from datetime import datetime
from bson import ObjectId
from pymongo import IndexModel, ASCENDING
from app.database import get_mongo_db

# ✅ Get MongoDB Instance
db = get_mongo_db()

# ------------------------------------------
# ✅ USERS COLLECTION
# ------------------------------------------
class User:
    collection = db["users"]

    @staticmethod
    def create_user(employee_id, email, hashed_password, full_name, role="user"):
        """Create a new user in MongoDB"""
        new_user = {
            "employee_id": employee_id,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "profile_picture": None,
            "role": role,
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
# ✅ ATTENDANCE COLLECTION (EPUSH + MongoDB)
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
# ✅ CAMPUS COLLECTION (Geofencing)
# ------------------------------------------
class Campus:
    collection = db["campuses"]

    @staticmethod
    def create_campus(name, geo_boundary):
        """Create a new campus with geofence boundaries"""
        new_campus = {
            "name": name,
            "geo_boundary": geo_boundary,
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
