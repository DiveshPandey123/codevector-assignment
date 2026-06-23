"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal


class ProductResponse(BaseModel):
    """Product response model."""
    
    id: str
    name: str
    category: str
    price: Decimal = Field(..., decimal_places=2)
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def format_datetime(cls, v):
        """Ensure datetime is in ISO 8601 format with timezone."""
        if isinstance(v, datetime):
            return v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        return v
    
    class Config:
        from_attributes = True


class PaginationCursor(BaseModel):
    """Pagination cursor model."""
    
    last_product_id: str
    last_updated_at: datetime
    snapshot_version: int


class BrowseProductsResponse(BaseModel):
    """Browse products response model."""
    
    products: List[ProductResponse]
    cursor: Optional[str] = None  # Base64 encoded cursor for next page
    has_more: bool
    snapshot_version: int
    total_in_category: Optional[int] = None


class CategoryInfo(BaseModel):
    """Category information model."""
    
    name: str
    product_count: int


class CategoriesResponse(BaseModel):
    """List categories response model."""
    
    categories: List[CategoryInfo]


class ProductInput(BaseModel):
    """Product input for bulk creation."""
    
    id: str
    name: str
    category: str
    price: Decimal = Field(..., decimal_places=2)
    description: Optional[str] = None
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Validate price is positive."""
        if v <= 0:
            raise ValueError('Price must be positive')
        return v


class BulkCreateProductsRequest(BaseModel):
    """Bulk create products request."""
    
    products: List[ProductInput]
    
    @field_validator('products')
    @classmethod
    def validate_products_count(cls, v):
        """Validate products count."""
        if len(v) == 0:
            raise ValueError('At least one product required')
        if len(v) > 10000:
            raise ValueError('Maximum 10000 products per request')
        return v


class BulkCreateProductsResponse(BaseModel):
    """Bulk create products response."""
    
    created_count: int
    errors: List[dict]


class ErrorResponse(BaseModel):
    """Error response model."""
    
    code: str
    message: str
    details: Optional[Any] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
