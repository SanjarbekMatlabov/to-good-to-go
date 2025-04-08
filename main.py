from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from db import Base, engine, get_db, init_db
from schemas import (
    UserCreate, UserOut, BusinessOwnerCreate, BusinessOwnerOut,
    SurpriseBagCreate, SurpriseBagOut, OrderCreate, OrderOut,
    NotificationOut, Token, OrderStatus
)
from services import (
    create_user, delete_user, create_business_owner, delete_business_owner,
    create_surprise_bag, get_surprise_bags, update_surprise_bag, delete_surprise_bag,
    create_order, get_order, update_order_status, delete_order,
    get_notifications, mark_notification_as_read, delete_notification
)
from auth import authenticate_user, create_access_token, get_current_user
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Initialize the database
init_db()

# User Endpoints
@app.post("/users/", response_model=UserOut)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)
@app.get("/users/me")
def read_users_me(current_user: UserOut = Depends(get_current_user)):
    """
    Hozirgi foydalanuvchining ma'lumotlarini qaytaradi.
    """
    return current_user
@app.delete("/users/")
def delete_current_user(current_user: UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    return delete_user(db, current_user.id)

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Business Owner Endpoints
@app.post("/business-owners/", response_model=BusinessOwnerOut)
def create_new_business_owner(
    business_owner: BusinessOwnerCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_business_owner(db, business_owner, current_user.id)

@app.delete("/business-owners/")
def delete_current_business_owner(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "business_owner":
        raise HTTPException(status_code=403, detail="Only business owners can delete their business profile")
    return delete_business_owner(db, current_user.id)

# Surprise Bag Endpoints
@app.post("/surprise-bags/", response_model=SurpriseBagOut)
def create_new_surprise_bag(
    bag: SurpriseBagCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "business_owner":
        raise HTTPException(status_code=403, detail="Only business owners can create surprise bags")
    return create_surprise_bag(db, bag, current_user.id)

@app.get("/surprise-bags/", response_model=list[SurpriseBagOut])
def read_surprise_bags(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_surprise_bags(db, skip, limit)

@app.put("/surprise-bags/{bag_id}", response_model=SurpriseBagOut)
def update_existing_surprise_bag(
    bag_id: int,
    bag_update: SurpriseBagCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "business_owner":
        raise HTTPException(status_code=403, detail="Only business owners can update surprise bags")
    return update_surprise_bag(db, bag_id, current_user.id, bag_update)

@app.delete("/surprise-bags/{bag_id}")
def delete_existing_surprise_bag(
    bag_id: int,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "business_owner":
        raise HTTPException(status_code=403, detail="Only business owners can delete surprise bags")
    return delete_surprise_bag(db, bag_id, current_user.id)

# Order Endpoints
@app.post("/orders/", response_model=OrderOut)
def create_new_order(
    order: OrderCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can place orders")
    return create_order(db, order, current_user.id)

@app.get("/orders/{order_id}", response_model=OrderOut)
def read_order(order_id: str, current_user: UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    db_order = get_order(db, order_id)
    if not db_order or db_order.customer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found or not authorized")
    return db_order

@app.put("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status_endpoint(
    order_id: str,
    status: OrderStatus,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_order_status(db, order_id, current_user.id, status)

@app.delete("/orders/{order_id}")
def delete_existing_order(
    order_id: str,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can delete their orders")
    return delete_order(db, order_id, current_user.id)

# Notification Endpoints
@app.get("/notifications/", response_model=list[NotificationOut])
def read_notifications(
    skip: int = 0,
    limit: int = 10,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_notifications(db, current_user.id, skip, limit)

@app.put("/notifications/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return mark_notification_as_read(db, notification_id, current_user.id)

@app.delete("/notifications/{notification_id}")
def delete_existing_notification(
    notification_id: str,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_notification(db, notification_id, current_user.id)