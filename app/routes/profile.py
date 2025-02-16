from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pymongo import MongoClient
from bson import ObjectId
from typing import Optional
import shutil
import os
from app.utils.auth import get_current_user
from app.database import get_mongo_db

router = APIRouter()

# Directory to store profile pictures
PROFILE_PICTURE_DIR = "media/profile_pictures"
os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)

# ------------------------------------------
# ✅ FETCH PROFILE DATA
# ------------------------------------------
@router.get("/profile/me")
async def get_profile(db: MongoClient = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """Fetch the logged-in user's profile details"""

    user = db["users"].find_one({"_id": ObjectId(current_user["_id"])})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "employee_id": user.get("employee_id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "profile_picture": user.get("profile_picture"),
        "role": user.get("role"),
        "campus": user.get("campus"),
        "designation": user.get("designation"),
        "department": user.get("department"),
        "date_of_joining": user.get("date_of_joining"),
        "shift": user.get("shift")
    }

# ------------------------------------------
# ✅ UPDATE PROFILE (Name & Profile Picture)
# ------------------------------------------
@router.put("/profile/update")
async def update_profile(
    full_name: Optional[str] = None,
    profile_picture: Optional[UploadFile] = File(None),
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Update profile details such as name and profile picture"""

    update_fields = {}

    # Update full name
    if full_name:
        update_fields["full_name"] = full_name

    # Update profile picture
    if profile_picture:
        file_location = f"{PROFILE_PICTURE_DIR}/{current_user['employee_id']}.jpg"
        
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(profile_picture.file, file_object)

        update_fields["profile_picture"] = file_location  # Store file path in MongoDB

    if update_fields:
        db["users"].update_one({"_id": ObjectId(current_user["_id"])}, {"$set": update_fields})
        return {"message": "Profile updated successfully"}

    return {"message": "No changes made"}
