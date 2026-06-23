import asyncio
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, Product, CategoryStats
from app.config import settings


CATEGORIES = ["electronics", "clothing", "home", "sports", "books"]

PRODUCT_NAMES = {
    "electronics": ["Wireless Headphones", "USB-C Cable", "Phone Charger", "Laptop Stand", "Keyboard", "Mouse", "Monitor", "Webcam", "Speaker", "Power Bank"],
    "clothing": ["T-Shirt", "Jeans", "Hoodie", "Jacket", "Socks", "Hat", "Sweater", "Shorts", "Pants", "Dress"],
    "home": ["Desk Lamp", "Pillow", "Bedsheet", "Curtains", "Rug", "Wall Art", "Plant Pot", "Coffee Mug", "Towel", "Candle"],
    "sports": ["Yoga Mat", "Dumbbells", "Running Shoes", "Water Bottle", "Resistance Band", "Tennis Racket", "Soccer Ball", "Basketball"],
    "books": ["Python Programming", "Web Development", "Data Science", "Machine Learning", "Cloud Computing", "DevOps Guide"],
}

PRICE_RANGES = {
    "electronics": (10.00, 2000.00),
    "clothing": (5.00, 150.00),
    "home": (3.00, 500.00),
    "sports": (5.00, 300.00),
    "books": (8.00, 50.00),
}


def generate_product_id():
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"prod_{suffix}"


def generate_products(count: int = 200000):
    base_date = datetime.utcnow() - timedelta(days=365)
    products = []
    seen_ids = set()
    
    print(f"Generating {count:,} products...")
    
    for i in range(count):
        category = random.choice(CATEGORIES)
        
        while True:
            product_id = generate_product_id()
            if product_id not in seen_ids:
                seen_ids.add(product_id)
                break
        
        name = random.choice(PRODUCT_NAMES[category])
        variant = random.randint(1, 100)
        name = f"{name} v{variant}" if variant > 1 else name
        
        min_price, max_price = PRICE_RANGES[category]
        price = Decimal(str(round(random.uniform(min_price, max_price), 2)))
        
        days_ago = random.randint(0, 365)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        
        created_at = base_date + timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        updated_at = created_at + timedelta(days=random.randint(0, 30))
        
        product = Product(
            id=product_id,
            name=name,
            category=category,
            price=price,
            description=f"{name} - High quality product",
            created_at=created_at,
            updated_at=updated_at,
            is_active=True,
        )
        products.append(product)
        
        if (i + 1) % 10000 == 0:
            print(f"  Generated {i + 1:,} products...")
    
    return products


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    
    print(f"Connecting to database: {settings.database_url}")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created")
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Generating products...")
        products = generate_products(200000)
        
        batch_size = 5000
        total_batches = (len(products) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(products))
            batch = products[start_idx:end_idx]
            
            session.add_all(batch)
            await session.commit()
            print(f"  Inserted batch {batch_num + 1}/{total_batches} ({len(batch)} products)")
        
        print("Calculating category statistics...")
        for category in CATEGORIES:
            category_count = sum(1 for p in products if p.category == category)
            stats = CategoryStats(
                category=category,
                product_count=category_count,
                last_updated=datetime.utcnow(),
            )
            session.add(stats)
        
        await session.commit()
        print("Category statistics updated")
    
    await engine.dispose()
    
    print(f"Successfully generated and inserted {len(products):,} products!")


if __name__ == "__main__":
    asyncio.run(main())
