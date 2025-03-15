from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from datetime import datetime, timedelta
from app.utils.auth import get_current_user
from app.database import get_mongo_db
from pymongo import MongoClient
import csv
import io
import os
import shutil
from fpdf import FPDF
from fastapi.responses import StreamingResponse
from bson import ObjectId

router = APIRouter()

# ✅ Directory to store profile pictures
PROFILE_PICTURE_DIR = "media/profile_pictures"
os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)


# ------------------------------------------
# ✅ USER ATTENDANCE API
# ------------------------------------------
@router.get("/user/attendance")
async def get_user_attendance(
    period: str = Query("monthly", description="Filter by: daily, weekly, or monthly"),
    status: str = Query(None, description="Filter by status: Present, Absent, Late, etc."),
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch user attendance records for selected period and status"""

    today = datetime.utcnow().date()
    
    # Set date range based on the period
    if period == "daily":
        start_date = today
        end_date = today
    elif period == "weekly":
        start_date = today - timedelta(days=today.weekday())  # Monday of this week
        end_date = today
    else:  # Monthly
        start_date = today.replace(day=1)
        end_date = today

    attendance_collection = db["attendance"]

    query = {
        "employee_id": current_user["employee_id"],
        "date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }

    if status:
        query["status"] = status  
        
    attendance_records = list(attendance_collection.find(query))

    return {
        "employee_id": current_user["employee_id"],
        "period": period,
        "attendance": attendance_records
    }

# ------------------------------------------
# ✅ DOWNLOAD ATTENDANCE REPORT (CSV & PDF)
# ------------------------------------------
@router.get("/user/attendance/report")
async def download_attendance_report(
    period: str = Query("monthly", description="Filter by: daily, weekly, or monthly"),
    format: str = Query("csv", description="Format: csv or pdf"),
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Download user attendance report in CSV or PDF format"""

    today = datetime.utcnow().date()

    # Set date range based on the period
    if period == "daily":
        start_date = today
        end_date = today
    elif period == "weekly":
        start_date = today - timedelta(days=today.weekday())  # Monday of this week
        end_date = today
    else:  # Monthly
        start_date = today.replace(day=1)
        end_date = today

    attendance_collection = db["attendance"]
    
    query = {
        "employee_id": current_user["employee_id"],
        "date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }

    attendance_records = list(attendance_collection.find(query))

    # CSV Report Generation
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Punch In", "Punch Out", "Total Hours", "Status"])
        
        for record in attendance_records:
            writer.writerow([
                record.get("date"),
                record.get("punch_in"),
                record.get("punch_out"),
                record.get("total_hours"),
                record.get("status")
            ])

        output.seek(0)
        return StreamingResponse(output, media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})

    # PDF Report Generation
    elif format == "pdf":
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, "Attendance Report", ln=True, align='C')
        pdf.ln(10)

        pdf.set_font("Arial", size=10)
        for record in attendance_records:
            pdf.cell(200, 10, f"Date: {record.get('date')}", ln=True)
            pdf.cell(200, 10, f"Punch In: {record.get('punch_in')}, Punch Out: {record.get('punch_out')}", ln=True)
            pdf.cell(200, 10, f"Total Hours: {record.get('total_hours')}, Status: {record.get('status')}", ln=True)
            pdf.ln(5)

        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return StreamingResponse(output, media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=attendance_report.pdf"})

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Choose 'csv' or 'pdf'.")

# ------------------------------------------
# ✅ USER LEAVE TRACKING API
# ------------------------------------------
@router.get("/user/leaves")
async def get_user_leaves(
    status: str = Query(None, description="Filter by status: Pending, Approved, Rejected"),
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch user's leave requests based on status"""

    leave_collection = db["leave_requests"]

    query = {"employee_id": current_user["employee_id"]}

    if status:
        query["status"] = status  # Apply status filter if provided

    leave_records = list(leave_collection.find(query))

    return {
        "employee_id": current_user["employee_id"],
        "leaves": leave_records
    }

# ------------------------------------------
# ✅ USER LEAVE APPLY API
# ------------------------------------------

@router.post("/user/apply-leave")
async def apply_leave(
    start_date: str,
    end_date: str,
    leave_type: str,
    reason: str,
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """User applies for leave"""

    leave_collection = db["leave_requests"]

    new_leave = {
        "employee_id": current_user["employee_id"],
        "name": current_user["full_name"],
        "start_date": start_date,
        "end_date": end_date,
        "leave_type": leave_type,
        "reason": reason,
        "status": "Pending",  # Initially Pending
        "requested_at": datetime.utcnow()
    }

    leave_collection.insert_one(new_leave)

    return {"message": "Leave request submitted successfully"}

# ------------------------------------------
# ✅ USER LEAVE BALANCE API
# ------------------------------------------

@router.get("/user/leave-balance")
async def get_leave_balance(
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch user's remaining leave balance"""

    user = db["users"].find_one({"employee_id": current_user["employee_id"]})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "employee_id": user["employee_id"],
        "casual_leaves_remaining": user.get("casual_leaves_remaining", 0),
        "sick_leaves_remaining": user.get("sick_leaves_remaining", 0),
        "special_leaves_remaining": user.get("special_leaves_remaining", 0),
        "total_leaves_remaining": user.get("total_leaves_remaining", 0)
    }


# ------------------------------------------
# ✅ HOLIDAY CALENDAR API
# ------------------------------------------
@router.get("/user/holiday-calendar")
async def get_holiday_calendar(
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch all Gazetted Holidays, Restricted Holidays & User's Leave Calendar"""

    # 📅 Get Holidays from DB
    holidays_collection = db["holidays"]
    holidays = list(holidays_collection.find())

    # 🏝️ Get User's Leaves
    leave_collection = db["leave_requests"]
    user_leaves = list(leave_collection.find({"employee_id": current_user["employee_id"]}))

    # 🗓️ Create Calendar Data
    calendar = []

    # ✅ Add Holidays (GH & RH)
    for holiday in holidays:
        calendar.append({
            "date": holiday["date"],
            "name": holiday["name"],
            "type": holiday["type"],  # GH or RH
            "color": "blue" if holiday["type"] == "GH" else "purple"
        })

    # ✅ Add User's Leaves
    for leave in user_leaves:
        calendar.append({
            "date": leave["start_date"],  # Assuming start_date is the key
            "end_date": leave["end_date"],  # Leave end date
            "name": f"{leave['leave_type']} Leave",
            "status": leave["status"],
            "color": "green" if leave["status"] == "Approved" else "yellow" if leave["status"] == "Pending" else "red"
        })

    return {"calendar": calendar}


# ------------------------------------------
# ✅ GET UNIVERSITY-LEVEL ANNOUNCEMENTS
# ------------------------------------------
@router.get("/announcements/university")
async def get_university_announcements(
    date: str = None,  # Optional date filter
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch University-Level Announcements"""
    
    query = {"level": "university"}

    # If date filter is provided
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            query["created_at"] = {"$gte": date_obj, "$lt": date_obj.replace(hour=23, minute=59, second=59)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    announcements = list(db["announcements"].find(query))

    return [
        {
            "title": ann["title"],
            "description": ann["description"],
            "created_by": ann["created_by"],
            "created_at": ann["created_at"]
        }
        for ann in announcements
    ]

# ------------------------------------------
# ✅ GET CAMPUS-LEVEL ANNOUNCEMENTS
# ------------------------------------------
@router.get("/announcements/campus")
async def get_campus_announcements(
    date: str = None,  # Optional date filter
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch Campus-Level Announcements"""

    query = {"level": "campus", "campus_id": current_user["campus_id"]}

    # If date filter is provided
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            query["created_at"] = {"$gte": date_obj, "$lt": date_obj.replace(hour=23, minute=59, second=59)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    announcements = list(db["announcements"].find(query))

    return [
        {
            "title": ann["title"],
            "description": ann["description"],
            "created_by": ann["created_by"],
            "created_at": ann["created_at"]
        }
        for ann in announcements
    ]

# ------------------------------------------
# ✅ GET PROFILE DETAILS
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
        "bank_details": {
            "bank_name": user.get("bank_name"),
            "account_number": user.get("account_number"),
            "ifsc_code": user.get("ifsc_code"),
            "pan_number": user.get("pan_number")
        }
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
    """Update profile picture for the logged-in user"""

    file_location = f"{PROFILE_PICTURE_DIR}/{current_user['employee_id']}.jpg"

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(profile_picture.file, file_object)

    db["users"].update_one({"_id": ObjectId(current_user["_id"])}, {"$set": {"profile_picture": file_location}})

    return {"message": "Profile picture updated successfully", "profile_picture_url": file_location}
