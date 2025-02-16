from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
from app.utils.auth import role_required, get_current_user
from app.database import get_mongo_db

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ATTENDANCE (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/campus/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def view_campus_attendance(
    campus_id: str,
    db: MongoClient = Depends(get_mongo_db)
):
    """Fetch attendance records for a specific campus"""
    attendance_records = db["attendance"].find({"campus_id": campus_id})

    return [
        {
            "employee_id": record["user_id"],
            "name": record.get("name"),
            "punch_in": record.get("punch_in"),
            "punch_out": record.get("punch_out"),
            "total_hours": record.get("total_hours"),
            "status": record.get("status")
        }
        for record in attendance_records
    ]

# ------------------------------------------
# ✅ DAILY GEOFENCING VIOLATION REPORT (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/daily-geofencing/campus/{campus_id}")
async def daily_geofencing_report(
    campus_id: str,
    db: MongoClient = Depends(get_mongo_db)
):
    """Fetch geofencing violations for today for a specific campus"""
    today = datetime.utcnow().date()

    offenders = db["attendance"].find({
        "date": today,
        "total_out_of_bounds_time": {"$gt": 30},
        "campus_id": campus_id
    })

    return [
        {
            "employee_id": record["user_id"],
            "name": record.get("name"),
            "total_out_of_bounds_time": record.get("total_out_of_bounds_time")
        }
        for record in offenders
    ]

# ------------------------------------------
# ✅ WEEKLY GEOFENCING VIOLATION REPORT (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/weekly-geofencing/campus/{campus_id}")
async def weekly_geofencing_report(
    campus_id: str,
    db: MongoClient = Depends(get_mongo_db)
):
    """Fetch weekly geofencing violations for a specific campus"""
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())

    offenders = db["attendance"].find({
        "date": {"$gte": start_of_week, "$lte": today},
        "total_out_of_bounds_time": {"$gt": 30},
        "campus_id": campus_id
    })

    return [
        {
            "employee_id": record["user_id"],
            "name": record.get("name"),
            "total_out_of_bounds_time": record.get("total_out_of_bounds_time")
        }
        for record in offenders
    ]

# ------------------------------------------
# ✅ VIEW & MANAGE LEAVE REQUESTS (ADMIN-LEVEL ONLY)
# ------------------------------------------
@router.get("/leave-requests", dependencies=[Depends(role_required(["super_admin"]))])
async def get_leave_requests(
    db: MongoClient = Depends(get_mongo_db)
):
    """Fetch all pending leave requests for Admins (HR or Directors)."""
    leave_requests = db["leave_requests"].find({"status": "Pending", "role": "admin"})

    return [
        {
            "id": str(leave["_id"]),
            "employee_id": leave["user_id"],
            "name": leave.get("name"),
            "leave_type": leave.get("leave_type"),
            "start_date": leave.get("start_date"),
            "end_date": leave.get("end_date"),
            "reason": leave.get("reason"),
            "status": leave.get("status")
        }
        for leave in leave_requests
    ]

@router.post("/leave-requests/{leave_id}/approve")
async def approve_leave_request(
    leave_id: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Approve an Admin-level leave request."""
    result = db["leave_requests"].update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "Approved"}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    return {"message": "Leave request approved successfully"}

@router.post("/leave-requests/{leave_id}/reject")
async def reject_leave_request(
    leave_id: str, 
    reason: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Reject an Admin-level leave request with a reason."""
    result = db["leave_requests"].update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "Rejected", "rejection_reason": reason}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    return {"message": f"Leave request rejected. Reason: {reason}"}

# ------------------------------------------
# ✅ CCTV CAMERA STREAMING (Super Admin)
# ------------------------------------------
@router.get("/cctv/live/{campus_id}")
async def stream_cctv(
    campus_id: str, 
    db: MongoClient = Depends(get_mongo_db),
    current_user: dict = Depends(get_current_user)
):
    """Stream live CCTV footage for a specific campus (Super Admin Only)"""

    campus = db["campuses"].find_one({"_id": ObjectId(campus_id)})

    if not campus:
        raise HTTPException(status_code=404, detail="Campus not found.")

    # Placeholder logic: Replace with actual CCTV streaming URL
    cctv_stream_url = f"http://cctv.dseu.ac.in/live/{campus_id}"
    
    return {"campus": campus["name"], "stream_url": cctv_stream_url}

# ------------------------------------------
# ✅ VIEW CAMPUS INVENTORY (Super Admin)
# ------------------------------------------
@router.get("/inventory/campus/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def get_inventory_for_campus(
    campus_id: str, db: MongoClient = Depends(get_mongo_db)
):
    """View all inventory items for a specific campus"""
    inventory = db["inventory"].find({"campus_id": campus_id})

    return [
        {
            "id": str(item["_id"]),
            "name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"]
        }
        for item in inventory
    ]

# ------------------------------------------
# ✅ VIEW INVENTORY REQUESTS (Super Admin)
# ------------------------------------------
@router.get("/inventory/requests", dependencies=[Depends(role_required(["super_admin"]))])
async def get_inventory_requests(
    db: MongoClient = Depends(get_mongo_db)
):
    """Super Admin can view all inventory requests across campuses"""
    requests = db["inventory_requests"].find()

    return [
        {
            "id": str(req["_id"]),
            "item_name": req["item_name"],
            "requested_by": req["requested_by"],
            "requested_quantity": req["requested_quantity"],
            "status": req["status"]
        }
        for req in requests
    ]
