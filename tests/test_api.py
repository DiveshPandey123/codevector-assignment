"""Integration tests for API endpoints."""
import pytest
from sqlalchemy import select
from app.models import Product, CategoryStats
from datetime import datetime
from decimal import Decimal


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_browse_products_empty(client):
    """Test browsing products when database is empty."""
    response = await client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert data["products"] == []
    assert data["has_more"] is False
    assert data["cursor"] is None


@pytest.mark.asyncio
async def test_browse_products_with_data(client, test_session):
    """Test browsing products with data."""
    # Insert test products
    products_data = [
        Product(
            id="prod_001",
            name="Laptop",
            category="electronics",
            price=Decimal("999.99"),
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        ),
        Product(
            id="prod_002",
            name="Mouse",
            category="electronics",
            price=Decimal("25.00"),
            created_at=datetime(2024, 1, 2),
            updated_at=datetime(2024, 1, 2),
        ),
        Product(
            id="prod_003",
            name="Keyboard",
            category="electronics",
            price=Decimal("75.00"),
            created_at=datetime(2024, 1, 3),
            updated_at=datetime(2024, 1, 3),
        ),
    ]
    
    test_session.add_all(products_data)
    await test_session.commit()
    
    # Insert category stats
    category_stats = CategoryStats(
        category="electronics",
        product_count=3,
    )
    test_session.add(category_stats)
    await test_session.commit()
    
    # Test browsing
    response = await client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 3
    assert data["has_more"] is False
    assert data["cursor"] is None
    
    # Verify sort order (newest first: updated_at DESC, id DESC)
    assert data["products"][0]["id"] == "prod_003"
    assert data["products"][1]["id"] == "prod_002"
    assert data["products"][2]["id"] == "prod_001"


@pytest.mark.asyncio
async def test_browse_products_pagination(client, test_session):
    """Test cursor-based pagination."""
    # Insert 10 test products
    for i in range(1, 11):
        product = Product(
            id=f"prod_{i:03d}",
            name=f"Product {i}",
            category="electronics",
            price=Decimal(f"{i * 10}.00"),
            created_at=datetime(2024, 1, i),
            updated_at=datetime(2024, 1, i),
        )
        test_session.add(product)
    
    test_session.add(CategoryStats(category="electronics", product_count=10))
    await test_session.commit()
    
    # Get first page (limit 3)
    response1 = await client.get("/products?limit=3")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["products"]) == 3
    assert data1["has_more"] is True
    assert data1["cursor"] is not None
    
    # Get second page with cursor
    cursor = data1["cursor"]
    response2 = await client.get(f"/products?limit=3&cursor={cursor}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["products"]) == 3
    
    # Verify no overlapping products
    ids1 = {p["id"] for p in data1["products"]}
    ids2 = {p["id"] for p in data2["products"]}
    assert ids1.isdisjoint(ids2), "Pagination returned duplicate products"


@pytest.mark.asyncio
async def test_browse_products_by_category(client, test_session):
    """Test filtering products by category."""
    # Insert products from different categories
    products_data = [
        Product(
            id="prod_001",
            name="Laptop",
            category="electronics",
            price=Decimal("999.99"),
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        ),
        Product(
            id="prod_002",
            name="Shirt",
            category="clothing",
            price=Decimal("25.00"),
            created_at=datetime(2024, 1, 2),
            updated_at=datetime(2024, 1, 2),
        ),
        Product(
            id="prod_003",
            name="Book",
            category="books",
            price=Decimal("15.00"),
            created_at=datetime(2024, 1, 3),
            updated_at=datetime(2024, 1, 3),
        ),
    ]
    
    test_session.add_all(products_data)
    test_session.add_all([
        CategoryStats(category="electronics", product_count=1),
        CategoryStats(category="clothing", product_count=1),
        CategoryStats(category="books", product_count=1),
    ])
    await test_session.commit()
    
    # Test category filter
    response = await client.get("/products?category=electronics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 1
    assert data["products"][0]["category"] == "electronics"
    assert data["total_in_category"] == 1


@pytest.mark.asyncio
async def test_get_product_by_id(client, test_session):
    """Test getting product by ID."""
    # Insert test product
    product = Product(
        id="prod_123",
        name="Test Product",
        category="electronics",
        price=Decimal("99.99"),
        description="A great product",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 5),
    )
    test_session.add(product)
    await test_session.commit()
    
    # Get product
    response = await client.get("/products/prod_123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "prod_123"
    assert data["name"] == "Test Product"
    assert data["category"] == "electronics"
    assert data["price"] == "99.99"
    assert data["description"] == "A great product"


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    """Test getting non-existent product."""
    response = await client.get("/products/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_categories(client, test_session):
    """Test listing categories."""
    # Insert category stats
    categories = [
        CategoryStats(category="books", product_count=100),
        CategoryStats(category="electronics", product_count=500),
        CategoryStats(category="clothing", product_count=300),
    ]
    test_session.add_all(categories)
    await test_session.commit()
    
    # Get categories
    response = await client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == 3
    
    # Verify alphabetical order
    names = [c["name"] for c in data["categories"]]
    assert names == sorted(names)
    
    # Verify counts
    for cat in data["categories"]:
        if cat["name"] == "electronics":
            assert cat["product_count"] == 500
        elif cat["name"] == "books":
            assert cat["product_count"] == 100


@pytest.mark.asyncio
async def test_invalid_limit_parameter(client):
    """Test invalid limit parameter."""
    # Limit too high
    response = await client.get("/products?limit=200")
    assert response.status_code == 422  # Validation error
    
    # Limit too low
    response = await client.get("/products?limit=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_cursor_parameter(client):
    """Test invalid cursor parameter."""
    response = await client.get("/products?cursor=not-valid-base64!!!")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_CURSOR"
