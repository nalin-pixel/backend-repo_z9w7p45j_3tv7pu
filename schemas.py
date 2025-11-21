"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (kept for reference):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# GST App Schemas

class GSTCategory(BaseModel):
    """
    GST categories with dynamic rates and keywords for AI-like matching
    Collection name: "gstcategory"
    """
    name: str = Field(..., description="Category name, e.g., Electronics, Restaurant")
    rate: float = Field(..., ge=0, le=100, description="GST rate percentage, e.g., 18 for 18%")
    keywords: List[str] = Field(default_factory=list, description="Keywords to help classify descriptions")
    active: bool = Field(True, description="Whether this category is active")

class GSTCalculation(BaseModel):
    """
    Calculation log for auditing
    Collection name: "gstcalculation"
    """
    amount: float = Field(..., ge=0, description="Base amount entered by user")
    mode: str = Field(..., description="exclusive or inclusive")
    applied_rate: float = Field(..., ge=0, le=100, description="Rate actually used")
    computed_tax: float = Field(..., ge=0, description="Tax amount computed")
    net_amount: float = Field(..., ge=0, description="Amount before tax")
    gross_amount: float = Field(..., ge=0, description="Amount after tax")
    detected_category: Optional[str] = Field(None, description="Category name used")
    source: Optional[str] = Field(None, description="How rate was chosen: provided|detected|default")
