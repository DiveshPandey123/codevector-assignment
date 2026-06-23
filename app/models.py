from sqlalchemy import Column, String, Numeric, DateTime, Boolean, Integer, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    __table_args__ = (
        Index('idx_products_category_updated_id', 'category', 'updated_at', 'id'),
        Index('idx_products_updated_id', 'updated_at', 'id'),
        Index('idx_products_updated_at', 'updated_at'),
        Index('idx_products_created_at', 'created_at'),
    )


class CategoryStats(Base):
    __tablename__ = "category_stats"
    
    category = Column(String(100), primary_key=True, index=True)
    product_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_category_stats_updated', 'last_updated'),
    )


class ProductAuditLog(Base):
    __tablename__ = "product_audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(255), nullable=False, index=True)
    operation = Column(String(50), nullable=False)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    admin_user = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_audit_product_id', 'product_id'),
        Index('idx_audit_changed_at', 'changed_at'),
    )
