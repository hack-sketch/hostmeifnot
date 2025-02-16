from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ✅ User Schema for API Requests
class UserSchema(BaseModel):
    employee_id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: Optional[bool] = True
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True  # Allows conversion from MongoDB dict

# ✅ Attendance Schema for API Requests
class AttendanceSchema(BaseModel):
    employee_id: str
    punch_in: datetime
    punch_out: Optional[datetime] = None
    status: str
    punch_in_campus_id: Optional[str] = None
    punch_out_campus_id: Optional[str] = None
    total_hours: Optional[float] = None
    total_out_of_bounds_time: Optional[float] = 0.0

    class Config:
        from_attributes = True  # Allows conversion from MongoDB dict

# ✅ Inventory Schema
class InventoryItemSchema(BaseModel):
    name: str
    quantity: int
    category: str
    campus_id: str

    class Config:
        from_attributes = True

class InventoryRequestSchema(BaseModel):
    user_id: str
    item_id: str
    requested_quantity: int
    reason: str
    status: Optional[str] = "Pending"

    class Config:
        from_attributes = True
