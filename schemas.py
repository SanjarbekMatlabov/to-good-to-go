from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# Enums for Pydantic
class UserRole(str, Enum):
    customer = "customer"
    business_owner = "business_owner"

class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

class NotificationType(str, Enum):
    order_confirmation = "order_confirmation"
    pickup_reminder = "pickup_reminder"
    new_bag = "new_bag"
    order_update = "order_update"

class RelatedEntityType(str, Enum):
    order = "order"
    bag = "bag"

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    role: UserRole

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone: Optional[str]
    created_at: datetime
    is_active: bool
    role: UserRole

    class Config:
        orm_mode = True

# Business Owner Schemas
class BusinessOwnerCreate(BaseModel):
    business_name: str
    business_description: Optional[str] = None
    address: str
    logo_url: Optional[str] = None
    business_hours: Optional[str] = None

class BusinessOwnerOut(BaseModel):
    owner_id: int
    business_name: str
    business_description: Optional[str]
    address: str
    logo_url: Optional[str]
    registration_date: datetime
    business_hours: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        orm_mode = True

# Surprise Bag Schemas
class SurpriseBagCreate(BaseModel):
    title: str
    description: str
    contents: Optional[Dict[str, Any]] = None
    original_price: float = Field(..., gt=0)
    discount_price: float = Field(..., gt=0)
    quantity_available: int = Field(..., ge=0)
    pickup_start: datetime
    pickup_end: datetime
    image_urls: Optional[List[str]] = None

class SurpriseBagOut(BaseModel):
    id: int
    business_id: int
    title: str
    description: str
    contents: Optional[Dict[str, Any]]
    original_price: float
    discount_price: float
    quantity_available: int
    quantity_sold: int
    pickup_start: datetime
    pickup_end: datetime
    created_at: datetime
    image_urls: Optional[List[str]]
    is_active: bool

    class Config:
        orm_mode = True

# Order Schemas
class OrderCreate(BaseModel):
    bag_id: int
    total_price: float = Field(..., gt=0)

class OrderOut(BaseModel):
    order_id: str
    customer_id: Optional[int]
    bag_id: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    pickup_code: str
    rating: Optional[int]
    feedback: Optional[str]

    class Config:
        orm_mode = True

# Notification Schemas
class NotificationOut(BaseModel):
    notification_id: str
    user_id: int
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime
    related_entity_type: RelatedEntityType
    related_entity_id: str

    class Config:
        orm_mode = True

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str