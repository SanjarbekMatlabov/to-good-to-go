import uuid
from sqlalchemy.orm import Session
from models import User, BusinessOwner, SurpriseBag, Order, Notification
from schemas import UserCreate, BusinessOwnerCreate, SurpriseBagCreate, OrderCreate, UserRole, OrderStatus, NotificationType, RelatedEntityType
from auth import get_password_hash
from datetime import datetime
from fastapi import HTTPException

# User Services
def create_user(db: Session, user: UserCreate):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
        phone=user.phone,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def delete_user(db: Session, user_id: int):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Soft delete by setting is_active to False
    db_user.is_active = False
    db.commit()
    return {"message": "User deactivated"}

# Business Owner Services
def create_business_owner(db: Session, business_owner: BusinessOwnerCreate, user_id: int):
    db_user = get_user_by_id(db, user_id)
    if not db_user or db_user.role != UserRole.business_owner:
        raise HTTPException(status_code=403, detail="User must be a business owner")
    db_business = BusinessOwner(
        owner_id=user_id,
        **business_owner.dict()
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business

def get_business_owner(db: Session, user_id: int):
    return db.query(BusinessOwner).filter(BusinessOwner.owner_id == user_id).first()

def delete_business_owner(db: Session, user_id: int):
    db_business = get_business_owner(db, user_id)
    if not db_business:
        raise HTTPException(status_code=404, detail="Business owner not found")
    # Soft delete by setting is_verified to False and user's is_active to False
    db_business.is_verified = False
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db_user.is_active = False
    db.commit()
    return {"message": "Business owner and associated user deactivated"}

# Surprise Bag Services
def create_surprise_bag(db: Session, bag: SurpriseBagCreate, business_id: int):
    db_business = db.query(BusinessOwner).filter(BusinessOwner.owner_id == business_id).first()
    if not db_business:
        raise HTTPException(status_code=404, detail="Business not found")
    if bag.discount_price >= bag.original_price:
        raise HTTPException(status_code=400, detail="Discount price must be less than original price")
    if bag.pickup_end <= bag.pickup_start:
        raise HTTPException(status_code=400, detail="Pickup end time must be after pickup start time")
    db_bag = SurpriseBag(
        business_id=business_id,
        **bag.dict()
    )
    db.add(db_bag)
    db.commit()
    db.refresh(db_bag)

    # Notify customers about the new surprise bag
    customers = db.query(User).filter(User.role == UserRole.customer).all()
    for customer in customers:
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            user_id=customer.id,
            type=NotificationType.new_bag,
            title="New Surprise Bag Available!",
            message=f"A new surprise bag '{db_bag.title}' is available at {db_business.business_name}!",
            related_entity_type=RelatedEntityType.bag,
            related_entity_id=str(db_bag.id)
        )
        db.add(notification)
    db.commit()
    return db_bag

def get_surprise_bag(db: Session, bag_id: int):
    return db.query(SurpriseBag).filter(SurpriseBag.id == bag_id).first()

def get_surprise_bags(db: Session, skip: int = 0, limit: int = 10):
    return db.query(SurpriseBag).filter(SurpriseBag.is_active == True).offset(skip).limit(limit).all()

def update_surprise_bag(db: Session, bag_id: int, business_id: int, bag_update: SurpriseBagCreate):
    db_bag = db.query(SurpriseBag).filter(SurpriseBag.id == bag_id, SurpriseBag.business_id == business_id).first()
    if not db_bag:
        raise HTTPException(status_code=404, detail="Surprise bag not found or not authorized")
    for key, value in bag_update.dict(exclude_unset=True).items():
        setattr(db_bag, key, value)
    db.commit()
    db.refresh(db_bag)
    return db_bag

def delete_surprise_bag(db: Session, bag_id: int, business_id: int):
    db_bag = db.query(SurpriseBag).filter(SurpriseBag.id == bag_id, SurpriseBag.business_id == business_id).first()
    if not db_bag:
        raise HTTPException(status_code=404, detail="Surprise bag not found or not authorized")
    # Check if there are any pending or confirmed orders for this bag
    active_orders = db.query(Order).filter(
        Order.bag_id == bag_id,
        Order.status.in_([OrderStatus.pending, OrderStatus.confirmed])
    ).count()
    if active_orders > 0:
        raise HTTPException(status_code=400, detail="Cannot delete surprise bag with active orders")
    db_bag.is_active = False
    db.commit()
    return {"message": "Surprise bag deactivated"}

# Order Services
def create_order(db: Session, order: OrderCreate, customer_id: int):
    db_bag = get_surprise_bag(db, order.bag_id)
    if not db_bag or not db_bag.is_active:
        raise HTTPException(status_code=404, detail="Surprise bag not found or not available")
    if db_bag.quantity_available <= db_bag.quantity_sold:
        raise HTTPException(status_code=400, detail="Surprise bag is sold out")
    
    # Generate a unique pickup code
    pickup_code = str(uuid.uuid4())[:8]
    while db.query(Order).filter(Order.pickup_code == pickup_code).first():
        pickup_code = str(uuid.uuid4())[:8]

    db_order = Order(
        order_id=str(uuid.uuid4()),
        customer_id=customer_id,
        bag_id=order.bag_id,
        total_price=order.total_price,
        pickup_code=pickup_code,
        status=OrderStatus.pending
    )
    db_bag.quantity_sold += 1
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Create a notification for the customer
    notification = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=customer_id,
        type=NotificationType.order_confirmation,
        title="Order Confirmed!",
        message=f"Your order for '{db_bag.title}' has been placed. Pickup code: {pickup_code}",
        related_entity_type=RelatedEntityType.order,
        related_entity_id=db_order.order_id
    )
    db.add(notification)
    db.commit()
    return db_order

def get_order(db: Session, order_id: str):
    return db.query(Order).filter(Order.order_id == order_id).first()

def update_order_status(db: Session, order_id: str, customer_id: int, status: OrderStatus):
    db_order = db.query(Order).filter(Order.order_id == order_id, Order.customer_id == customer_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found or not authorized")
    db_order.status = status
    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)

    # Notify the customer about the order update
    notification = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=customer_id,
        type=NotificationType.order_update,
        title="Order Status Updated",
        message=f"Your order status has been updated to '{status}'.",
        related_entity_type=RelatedEntityType.order,
        related_entity_id=order_id
    )
    db.add(notification)
    db.commit()
    return db_order

def delete_order(db: Session, order_id: str, customer_id: int):
    db_order = db.query(Order).filter(Order.order_id == order_id, Order.customer_id == customer_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found or not authorized")
    # Only allow deletion if the order is in pending status
    if db_order.status != OrderStatus.pending:
        raise HTTPException(status_code=400, detail="Can only delete pending orders")
    # Decrease the quantity_sold of the associated surprise bag
    db_bag = get_surprise_bag(db, db_order.bag_id)
    if db_bag:
        db_bag.quantity_sold -= 1
    # Update the order status to cancelled instead of hard delete
    db_order.status = OrderStatus.cancelled
    db_order.updated_at = datetime.utcnow()
    db.commit()

    # Notify the customer about the cancellation
    notification = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=customer_id,
        type=NotificationType.order_update,
        title="Order Cancelled",
        message="Your order has been cancelled.",
        related_entity_type=RelatedEntityType.order,
        related_entity_id=order_id
    )
    db.add(notification)
    db.commit()
    return {"message": "Order cancelled"}

# Notification Services
def get_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    return db.query(Notification).filter(Notification.user_id == user_id).offset(skip).limit(limit).all()

def mark_notification_as_read(db: Session, notification_id: str, user_id: int):
    db_notification = db.query(Notification).filter(Notification.notification_id == notification_id, Notification.user_id == user_id).first()
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found or not authorized")
    db_notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}

def delete_notification(db: Session, notification_id: str, user_id: int):
    db_notification = db.query(Notification).filter(Notification.notification_id == notification_id, Notification.user_id == user_id).first()
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found or not authorized")
    db.delete(db_notification)
    db.commit()
    return {"message": "Notification deleted"}