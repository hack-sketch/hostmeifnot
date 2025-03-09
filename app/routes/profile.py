from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pymongo import MongoClient
from bson import ObjectId
import shutil
import os
from app.utils.auth import get_current_user
from app.database import get_mongo_db

router = APIRouter()

# Directory to store profile pictures
PROFILE_PICTURE_DIR = "media/profile_pictures"
os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)

# Base URL for profile picture access (Replace with actual domain/IP)
BASE_URL = "http://yourserver.com"

# ------------------------------------------
# ✅ FETCH PROFILE DATA (INCLUDES CAMPUS & PROFILE PICTURE)
# ------------------------------------------
@router.get("/profile/me")
async def get_profile(db: MongoClient = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """Fetch the logged-in user's profile details"""

    user = db["users"].find_one({"_id": ObjectId(current_user["_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch campus details
    campus = db["campuses"].find_one({"_id": ObjectId(user.get("campus_id"))})

    return {
        "employee_id": user.get("employee_id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "profile_picture": f"{BASE_URL}/{user.get('profile_picture')}" if user.get("profile_picture") else None,
        "role": user.get("role"),
        "campus": {
            "campus_id": user.get("campus_id"),
            "campus_name": campus.get("name") if campus else "Unknown",
            "geo_boundary": campus.get("geo_boundary") if campus else None
        },
        "designation": user.get("designation"),
        "department": user.get("department"),
        "date_of_joining": user.get("date_of_joining"),
        "bank_details": user.get("bank_details"),
    }

# ------------------------------------------
# ✅ UPDATE PROFILE PICTURE ONLY
# ------------------------------------------
@router.put("/profile/update-picture")
async def update_profile_picture(
    profile_picture: UploadFile = File(...),
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Update only the profile picture"""

    # File location to store the image
    file_location = f"{PROFILE_PICTURE_DIR}/{current_user['employee_id']}.jpg"
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(profile_picture.file, file_object)

    # Update profile picture path in MongoDB
    db["users"].update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"profile_picture": file_location}}
    )

    return {
        "message": "Profile picture updated successfully",
        "profile_picture_url": f"{BASE_URL}/{file_location}"
    }

# ------------------------------------------
# ✅ FETCH USER'S BANK DETAILS
# ------------------------------------------
@router.get("/profile/bank-details")
async def get_bank_details(db: MongoClient = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """Fetch the user's bank details"""

    user = db["users"].find_one({"_id": ObjectId(current_user["_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "bank_name": user.get("bank_details", {}).get("bank_name"),
        "account_number": user.get("bank_details", {}).get("account_number"),
        "ifsc_code": user.get("bank_details", {}).get("ifsc_code"),
        "account_holder_name": user.get("bank_details", {}).get("account_holder_name"),
    }
