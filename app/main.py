from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, text
from typing import Optional
from datetime import datetime
from decimal import Decimal
import logging

from app.config import settings
from app.database import get_db, init_db, close_db
from app.models import Product, CategoryStats
from app.schemas import (
    BrowseProductsResponse,
    ProductResponse,
    CategoriesResponse,
    CategoryInfo,
    HealthCheckResponse,
    BulkCreateProductsRequest,
    BulkCreateProductsResponse,
)
from app.pagination import PaginationCursor

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
    await close_db()


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return {
        "status": "healthy",
        "version": settings.api_version,
    }


@app.get("/products", response_model=BrowseProductsResponse)
async def browse_products(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;"))
        result = await db.execute(text("SELECT pg_current_xact_id()"))
        snapshot_version = result.scalar() or 0
        
        last_product_id = None
        last_updated_at = None
        
        if cursor:
            try:
                pagination_cursor = PaginationCursor.decode(cursor)
                last_product_id = pagination_cursor.last_product_id
                last_updated_at = pagination_cursor.last_updated_at
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid cursor: {str(e)}")
        
        query = select(Product).where(Product.is_active == True)
        
        if category:
            query = query.where(Product.category == category)
        
        if last_updated_at and last_product_id:
            query = query.where(
                (Product.updated_at, Product.id) < (last_updated_at, last_product_id)
            )
        
        query = query.order_by(desc(Product.updated_at), desc(Product.id))
        query = query.limit(limit + 1)
        
        result = await db.execute(query)
        products = result.scalars().all()
        
        has_more = len(products) > limit
        products = products[:limit]
        
        next_cursor = None
        if products:
            last_product = products[-1]
            next_cursor = PaginationCursor(
                last_product_id=last_product.id,
                last_updated_at=last_product.updated_at,
                snapshot_version=snapshot_version,
            ).encode()
        
        count_query = select(func.count(Product.id)).where(Product.is_active == True)
        if category:
            count_query = count_query.where(Product.category == category)
        
        count_result = await db.execute(count_query)
        total_in_category = count_result.scalar()
        
        product_responses = [
            ProductResponse(
                id=p.id,
                name=p.name,
                category=p.category,
                price=Decimal(str(p.price)),
                description=p.description,
                created_at=p.created_at.isoformat() if p.created_at.tzinfo else p.created_at.isoformat() + "Z",
                updated_at=p.updated_at.isoformat() if p.updated_at.tzinfo else p.updated_at.isoformat() + "Z",
            )
            for p in products
        ]
        
        return BrowseProductsResponse(
            products=product_responses,
            cursor=next_cursor,
            has_more=has_more,
            snapshot_version=snapshot_version,
            total_in_category=total_in_category,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing products: {e}")
        raise HTTPException(status_code=500, detail="Failed to browse products")


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return ProductResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=Decimal(str(product.price)),
            description=product.description,
            created_at=product.created_at.isoformat() if product.created_at.tzinfo else product.created_at.isoformat() + "Z",
            updated_at=product.updated_at.isoformat() if product.updated_at.tzinfo else product.updated_at.isoformat() + "Z",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(status_code=500, detail="Failed to get product")


@app.get("/categories", response_model=CategoriesResponse)
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(CategoryStats).order_by(CategoryStats.category)
        )
        categories = result.scalars().all()
        
        category_list = [
            CategoryInfo(name=c.category, product_count=c.product_count)
            for c in categories
        ]
        
        return CategoriesResponse(categories=category_list)
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")


@app.post("/products/bulk")
async def bulk_create_products(
    api_key: str = Query(...),
    request: BulkCreateProductsRequest = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        if api_key != settings.api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        if not request:
            raise HTTPException(status_code=400, detail="Request body required")
        
        created_count = 0
        errors = []
        valid_products = []
        
        for idx, product_input in enumerate(request.products):
            try:
                if any(p.id == product_input.id for p in valid_products):
                    errors.append({
                        "index": idx,
                        "id": product_input.id,
                        "error": "Duplicate ID in batch",
                    })
                    continue
                
                existing = await db.execute(
                    select(Product).where(Product.id == product_input.id)
                )
                if existing.scalar_one_or_none():
                    errors.append({
                        "index": idx,
                        "id": product_input.id,
                        "error": "Product ID already exists",
                    })
                    continue
                
                product = Product(
                    id=product_input.id,
                    name=product_input.name,
                    category=product_input.category,
                    price=product_input.price,
                    description=product_input.description,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )
                valid_products.append(product)
            
            except Exception as e:
                logger.error(f"Error validating product: {e}")
                errors.append({
                    "index": idx,
                    "error": str(e),
                })
        
        if valid_products:
            db.add_all(valid_products)
            await db.flush()
            created_count = len(valid_products)
        
        category_counts = {}
        for product in valid_products:
            category_counts[product.category] = category_counts.get(product.category, 0) + 1
        
        for category, count in category_counts.items():
            stats_result = await db.execute(
                select(CategoryStats).where(CategoryStats.category == category)
            )
            stats = stats_result.scalar_one_or_none()
            
            if stats:
                stats.product_count += count
                stats.last_updated = datetime.utcnow()
            else:
                stats = CategoryStats(
                    category=category,
                    product_count=count,
                    last_updated=datetime.utcnow(),
                )
                db.add(stats)
        
        await db.commit()
        
        logger.info(f"Bulk created {created_count} products")
        
        return BulkCreateProductsResponse(
            created_count=created_count,
            errors=errors,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk creating products: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk create products")
