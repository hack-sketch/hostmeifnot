from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
from app.utils.auth import role_required, get_current_user
from app.database import get_mongo_db
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ATTENDANCE (CAMPUS-WISE) 
# ------------------------------------------
@router.get("/user/{user_id}")
async def view_user_profile_attendance(user_id: str, db: MongoClient = Depends(get_mongo_db)):
    """Fetch user profile and attendance records."""

    # Try fetching user by ObjectId first, fallback to employee_id
    try:
        user = db["users"].find_one({"_id": ObjectId(user_id)})
    except:
        user = db["users"].find_one({"employee_id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert ObjectId to string for JSON serialization
    user["_id"] = str(user["_id"])

    # Fetch attendance records for the user
    attendance = list(db["attendance"].find({"employee_id": user["employee_id"]}))

    # Convert ObjectId fields in attendance records to strings
    for record in attendance:
        record["_id"] = str(record["_id"])

    return {
        "profile": {
            "id": user["_id"],
            "employee_id": user["employee_id"],
            "name": user.get("full_name"),
            "email": user.get("email"),
            "profile_picture": user.get("profile_picture", ""),
            "designation": user.get("designation", ""),
            "campus": user.get("campus", ""),
        },
        "attendance": attendance
    }
    
# ------------------------------------------
# ✅ VIEW USERS (EMPLOYEES) (CAMPUS-WISE)
# ------------------------------------------
@router.get("/users/campus/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def view_campus_users(campus_id: str, db: MongoClient = Depends(get_mongo_db)):
    users = db["users"].find({"campus_id": campus_id})

    return [
        {
            "employee_id": user["employee_id"],
            "name": user.get("full_name"),
            "profile_picture": user.get("profile_picture"),
            "email": user.get("email"),
            "role": user.get("role"),
            "campus": user.get("campus"),
            "designation": user.get("designation")
        }
        for user in users
    ]

# ------------------------------------------
# ✅ VIEW SPECIFIC USER PROFILE & ATTENDANCE
# ------------------------------------------
@router.get("/user/{user_id}")
async def view_user_profile_attendance(user_id: str, db: MongoClient = Depends(get_mongo_db)):
    # Check if the user_id is a valid ObjectId
    try:
        object_id = ObjectId(user_id)  # Convert if it's an ObjectId
        user = db["users"].find_one({"_id": object_id})
    except:
        user = db["users"].find_one({"employee_id": user_id})  # Query by employee_id if not ObjectId

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    attendance = list(db["attendance"].find({"employee_id": user_id}))

    return {
        "profile": {
            "employee_id": user["employee_id"],
            "name": user.get("full_name"),
            "email": user.get("email"),
            "profile_picture": user.get("profile_picture"),
            "designation": user.get("designation"),
            "campus": user.get("campus")
        },
        "attendance": attendance
    }

# ------------------------------------------
# ✅ DOWNLOAD ATTENDANCE REPORT (CSV & PDF)
# ------------------------------------------
@router.get("/attendance/report")
async def download_attendance_report(
    campus_id: str,
    department: str,
    user_id: str = None,
    file_format: str = "csv",
    db: MongoClient = Depends(get_mongo_db)
):
    """Download attendance report in CSV or PDF format"""
    query = {"campus_id": campus_id, "department": department}
    if user_id:
        query["employee_id"] = user_id

    attendance = db["attendance"].find(query)

    if file_format.lower() == "csv":
        def generate_csv():
            yield "Employee ID,Name,Punch In,Punch Out,Total Hours,Status\n"
            for record in attendance:
                yield f"{record['employee_id']},{record.get('name')},{record.get('punch_in')},{record.get('punch_out')},{record.get('total_hours')},{record.get('status')}\n"

        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance_report.csv"}
        )

    elif file_format.lower() == "pdf":
        buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
        pdf_canvas.setTitle("Attendance Report")

        # PDF Header
        pdf_canvas.setFont("Helvetica-Bold", 14)
        pdf_canvas.drawString(100, 750, f"Attendance Report - {department} Campus ID: {campus_id}")

        pdf_canvas.setFont("Helvetica", 10)
        y_position = 720

        # Table Headers
        headers = ["Employee ID", "Name", "Punch In", "Punch Out", "Total Hours", "Status"]
        pdf_canvas.drawString(50, y_position, " | ".join(headers))
        y_position -= 20

        # Table Data
        for record in attendance:
            row = f"{record['employee_id']} | {record.get('name')} | {record.get('punch_in')} | {record.get('punch_out')} | {record.get('total_hours')} | {record.get('status')}"
            pdf_canvas.drawString(50, y_position, row)
            y_position -= 15
            if y_position < 50:  # Create new page if the space runs out
                pdf_canvas.showPage()
                y_position = 750

        pdf_canvas.save()
        buffer.seek(0)

        return Response(buffer.read(), media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=attendance_report.pdf"})

    else:
        raise HTTPException(status_code=400, detail="Invalid file format. Use 'csv' or 'pdf'.")

# ------------------------------------------
# ✅ MANAGE CAMPUS (ADD, EDIT, DELETE)
# ------------------------------------------
@router.post("/campus/add")
async def add_campus(name: str, description: str, latitude: float, longitude: float, db: MongoClient = Depends(get_mongo_db)):
    new_campus = {"name": name, "description": description, "latitude": latitude, "longitude": longitude}
    campus_id = db["campuses"].insert_one(new_campus).inserted_id
    return {"message": "Campus added successfully", "campus_id": str(campus_id)}

@router.put("/campus/edit/{campus_id}")
async def edit_campus(campus_id: str, name: str = None, description: str = None, latitude: float = None, longitude: float = None, db: MongoClient = Depends(get_mongo_db)):
    update_fields = {}
    if name: update_fields["name"] = name
    if description: update_fields["description"] = description
    if latitude: update_fields["latitude"] = latitude
    if longitude: update_fields["longitude"] = longitude
    
    db["campuses"].update_one({"_id": ObjectId(campus_id)}, {"$set": update_fields})
    return {"message": "Campus updated successfully"}

@router.delete("/campus/delete/{campus_id}")
async def delete_campus(campus_id: str, db: MongoClient = Depends(get_mongo_db)):
    db["campuses"].delete_one({"_id": ObjectId(campus_id)})
    return {"message": "Campus deleted successfully"}

# ------------------------------------------
# ✅ GET USER BANK DETAILS
# ------------------------------------------
@router.get("/user/{user_id}/bank-details")
async def get_user_bank_details(user_id: str, db: MongoClient = Depends(get_mongo_db)):
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "bank_name": user.get("bank_name"),
        "account_number": user.get("account_number"),
        "ifsc_code": user.get("ifsc_code"),
        "pan_number": user.get("pan_number")
    }

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


