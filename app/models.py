from datetime import datetime
from bson import ObjectId
from pymongo import IndexModel, ASCENDING
from app.database import get_mongo_db

db = get_mongo_db()

# ------------------------------------------
# ✅ USERS COLLECTION (Includes Bank Details)
# ------------------------------------------
class User:
    collection = db["users"]

    @staticmethod
    def create_user(employee_id, email, hashed_password, full_name, role="user", campus_id=None, designation=None, department=None):
        """Create a new user in MongoDB"""
        new_user = {
            "employee_id": employee_id,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "profile_picture": None,
            "role": role,
            "campus_id": campus_id,  
            "designation": designation,
            "department": department,
            "bank_details": {  
                "bank_name": None,
                "account_number": None,
                "ifsc_code": None,
                "pan_number": None
            },
            "is_active": True,
            "first_login": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return User.collection.insert_one(new_user).inserted_id

    @staticmethod
    def find_user_by_email(email):
        """Find user by email"""
        return User.collection.find_one({"email": email})

    @staticmethod
    def find_user_by_id(user_id):
        """Find user by ObjectId"""
        return User.collection.find_one({"_id": ObjectId(user_id)})

# ------------------------------------------
# ✅ ATTENDANCE COLLECTION (Ensuring Consistency)
# ------------------------------------------
class Attendance:
    collection = db["attendance"]

    @staticmethod
    def log_attendance(employee_id, punch_in, punch_out=None, status="Present", campus_id=None):
        """Log attendance record"""
        attendance_record = {
            "employee_id": employee_id,
            "date": datetime.utcnow().date(),
            "punch_in": punch_in,
            "punch_out": punch_out,
            "status": status,
            "punch_in_campus_id": campus_id,  
            "punch_out_campus_id": None if not punch_out else campus_id,
            "total_hours": None if not punch_out else (punch_out - punch_in).total_seconds() / 3600,
            "total_out_of_bounds_time": 0,
        }
        return Attendance.collection.insert_one(attendance_record).inserted_id

    @staticmethod
    def get_attendance_by_employee(employee_id, date):
        """Retrieve attendance record for a user on a specific date"""
        return Attendance.collection.find_one({"employee_id": employee_id, "date": date})

# ------------------------------------------
# ✅ CAMPUS COLLECTION (Added Zone)
# ------------------------------------------
class Campus:
    collection = db["campuses"]

    @staticmethod
    def create_campus(name, description, latitude, longitude, zone, geo_boundary=None):
        """Create a new campus with geofence boundaries"""
        new_campus = {
            "name": name,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "zone": zone,
            "geo_boundary": geo_boundary  # ✅ Add this
        }
        return Campus.collection.insert_one(new_campus).inserted_id


    @staticmethod
    def get_campus_by_id(campus_id):
        """Fetch campus details by ID"""
        return Campus.collection.find_one({"_id": ObjectId(campus_id)})

# ------------------------------------------
# ✅ INVENTORY COLLECTION (Items + Requests)
# ------------------------------------------
class InventoryItem:
    collection = db["inventory_items"]

    @staticmethod
    def add_item(name, quantity, category, campus_id):
        """Add new inventory item"""
        item = {
            "name": name,
            "quantity": quantity,
            "category": category,
            "campus_id": campus_id,
        }
        return InventoryItem.collection.insert_one(item).inserted_id

    @staticmethod
    def update_item_quantity(item_id, quantity):
        """Update quantity of an inventory item"""
        return InventoryItem.collection.update_one(
            {"_id": ObjectId(item_id)}, {"$set": {"quantity": quantity}}
        )

class InventoryRequest:
    collection = db["inventory_requests"]

    @staticmethod
    def request_item(user_id, item_id, requested_quantity, reason):
        """Employee requests inventory item"""
        request = {
            "user_id": user_id,
            "item_id": item_id,
            "requested_quantity": requested_quantity,
            "reason": reason,
            "status": "Pending",
            "created_at": datetime.utcnow(),
        }
        return InventoryRequest.collection.insert_one(request).inserted_id

# ------------------------------------------
# ✅ LEAVE COLLECTION (For Leave Requests)
# ------------------------------------------
class LeaveRequest:
    collection = db["leave_requests"]

    @staticmethod
    def request_leave(employee_id, start_date, end_date, leave_type, reason, status="Pending"):
        """User applies for leave"""
        leave_request = {
            "employee_id": employee_id,
            "start_date": start_date,
            "end_date": end_date,
            "leave_type": leave_type,
            "reason": reason,
            "status": status,
            "created_at": datetime.utcnow(),
        }
        return LeaveRequest.collection.insert_one(leave_request).inserted_id

    @staticmethod
    def get_leave_requests_by_employee(employee_id):
        """Fetch all leave requests by an employee"""
        return list(LeaveRequest.collection.find({"employee_id": employee_id}))

# ------------------------------------------
# ✅ ANNOUNCEMENTS COLLECTION
# ------------------------------------------
class Announcement:
    collection = db["announcements"]

    @staticmethod
    def create_announcement(title, message, level, campus_id=None):
        """Create a new announcement (University-Level or Campus-Level)"""
        announcement = {
            "title": title,
            "message": message,
            "level": level,  # "university" or "campus"
            "campus_id": campus_id if level == "campus" else None,
            "created_at": datetime.utcnow(),
        }
        return Announcement.collection.insert_one(announcement).inserted_id

    @staticmethod
    def get_announcements(level, campus_id=None):
        """Fetch announcements"""
        query = {"level": level}
        if campus_id:
            query["campus_id"] = campus_id
        return list(Announcement.collection.find(query))
