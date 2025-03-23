from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ------------------------------------------
# ✅ User Schema for API Requests
# ------------------------------------------
class UserSchema(BaseModel):
    employee_id: str
    email: EmailStr
    full_name: str
    role: str
    campus_id: Optional[str] = None  
    designation: Optional[str] = None 
    department: Optional[str] = None  
    is_active: Optional[bool] = True
    profile_picture: Optional[str] = None
    bank_details: Optional[dict] = {  
        "bank_name": None,
        "account_number": None,
        "ifsc_code": None,
        "pan_number": None
    }

    class Config:
        from_attributes = True  

# ------------------------------------------
# ✅ Attendance Schema for API Requests
# ------------------------------------------
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
        from_attributes = True 
        
# ------------------------------------------
# ✅ Campus Schema for API Requests
# ------------------------------------------
class CampusSchema(BaseModel):
    name: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    zone: Optional[str] = None  
    geo_boundary: Optional[str] = None  # ✅ Add this line

    class Config:
        from_attributes = True


# ------------------------------------------
# ✅ Leave Schema for API Requests
# ------------------------------------------
class LeaveRequestSchema(BaseModel):
    employee_id: str
    start_date: datetime
    end_date: datetime
    leave_type: str
    reason: str
    status: Optional[str] = "Pending"

    class Config:
        from_attributes = True

# ------------------------------------------
# ✅ Inventory Schema
# ------------------------------------------
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

# ------------------------------------------
# ✅ Announcements Schema for API Requests
# ------------------------------------------
class AnnouncementSchema(BaseModel):
    title: str
    message: str
    level: str  
    campus_id: Optional[str] = None
    created_at: Optional[datetime] = datetime.utcnow()

    class Config:
        from_attributes = True
