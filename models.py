import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    Numeric, JSON, ForeignKey, Enum as SQLEnum, func
)
from sqlalchemy.orm import relationship
from db import Base, init_db    

# Define Python Enums
class UserRole(str, enum.Enum):
    customer = "customer"
    business_owner = "business_owner"

class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

class NotificationType(str, enum.Enum):
    order_confirmation = "order_confirmation"
    pickup_reminder = "pickup_reminder"
    new_bag = "new_bag"
    order_update = "order_update"

class RelatedEntityType(str, enum.Enum):
    order = "order"
    bag = "bag"

# --- SQLAlchemy Models ---
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role_enum", create_type=False), nullable=False)

    # Relationships
    business_owner = relationship("BusinessOwner", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", foreign_keys="[Order.customer_id]")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class BusinessOwner(Base):
    __tablename__ = 'business_owners'

    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    business_name = Column(String, nullable=False)
    business_description = Column(Text, nullable=True)
    address = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    registration_date = Column(DateTime, server_default=func.now(), nullable=False)
    business_hours = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="business_owner")
    surprise_bags = relationship("SurpriseBag", back_populates="business", cascade="all, delete-orphan")

class SurpriseBag(Base):
    __tablename__ = 'surprise_bags'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey('business_owners.owner_id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    contents = Column(JSON, nullable=True)
    original_price = Column(Numeric(10, 2), nullable=False)
    discount_price = Column(Numeric(10, 2), nullable=False)
    quantity_available = Column(Integer, nullable=False)
    quantity_sold = Column(Integer, default=0, nullable=False)
    pickup_start = Column(DateTime, nullable=False)
    pickup_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    image_urls = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    business = relationship("BusinessOwner", back_populates="surprise_bags")
    orders = relationship("Order", back_populates="bag")

class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    bag_id = Column(Integer, ForeignKey('surprise_bags.id', ondelete='RESTRICT'), nullable=False, index=True)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(OrderStatus, name="order_status_enum", create_type=False), default=OrderStatus.pending, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    pickup_code = Column(String, unique=True, index=True, nullable=False)
    rating = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # Relationships
    customer = relationship("User", back_populates="orders", foreign_keys=[customer_id])
    bag = relationship("SurpriseBag", back_populates="orders")
    notifications = relationship(
        "Notification",
        primaryjoin="and_(Order.order_id==foreign(Notification.related_entity_id), Notification.related_entity_type=='order')",
        back_populates="order",
        cascade="all, delete-orphan"
    )

class Notification(Base):
    __tablename__ = 'notifications'

    notification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType, name="notification_type_enum", create_type=False), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    related_entity_type = Column(SQLEnum(RelatedEntityType, name="related_entity_type_enum", create_type=False), nullable=False)
    related_entity_id = Column(String, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    order = relationship(
        "Order",
        primaryjoin="and_(foreign(Notification.related_entity_id)==Order.order_id, Notification.related_entity_type=='order')",
        back_populates="notifications",
        uselist=False
    )

init_db()