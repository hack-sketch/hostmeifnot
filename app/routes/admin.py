from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from app.utils.auth import role_required, get_current_user
from app.database import get_mongo_db

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ATTENDANCE FOR ASSIGNED CAMPUS
# ------------------------------------------
@router.get("/attendance", dependencies=[Depends(role_required(["admin"]))])
async def get_attendance_for_campus(
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_mongo_db)
):
    """Fetch all attendance records for the admin's assigned campus."""
    attendance_collection = db["attendance"]

    attendance = await attendance_collection.find(
        {"punch_in_campus_id": current_user["campus_id"]}
    ).to_list(length=None)

    return [
        {
            "employee_id": record["user_id"],
            "name": record["user_full_name"],
            "punch_in": record["punch_in"],
            "punch_out": record.get("punch_out"),
            "total_hours": record.get("total_hours"),
            "status": record["status"]
        }
        for record in attendance
    ]


# ------------------------------------------
# ✅ VIEW USERS (EMPLOYEES) FOR ASSIGNED CAMPUS
# ------------------------------------------
@router.get("/users", dependencies=[Depends(role_required(["admin"]))])
async def get_users_for_campus(
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_mongo_db)
):
    """Fetch all employees assigned to the admin's campus."""
    users_collection = db["users"]

    users = await users_collection.find(
        {"campus_id": current_user["campus_id"]}
    ).to_list(length=None)

    return [
        {
            "employee_id": user["employee_id"],
            "name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"]
        }
        for user in users
    ]


# ------------------------------------------
# ✅ DOWNLOAD CAMPUS ATTENDANCE REPORT
# ------------------------------------------
@router.get("/attendance/report", dependencies=[Depends(role_required(["admin"]))])
async def download_attendance_report_for_campus(
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_mongo_db)
):
    """Download a CSV report of attendance for the assigned campus."""
    attendance_collection = db["attendance"]

    attendance = await attendance_collection.find(
        {"punch_in_campus_id": current_user["campus_id"]}
    ).to_list(length=None)

    def generate_csv():
        yield "Employee ID,Name,Punch In,Punch Out,Total Hours,Status\n"
        for record in attendance:
            yield f"{record['user_id']},{record['user_full_name']},{record['punch_in']},{record.get('punch_out')},{record.get('total_hours')},{record['status']}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=campus_attendance_report.csv"}
    )


# ------------------------------------------
# ✅ DAILY GEO TRACKING VIOLATION REPORT
# ------------------------------------------
@router.get("/attendance/daily-geofencing")
async def daily_geofencing_data(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """Fetch a list of employees who violated geofencing today in admin's assigned campus."""
    attendance_collection = db["attendance"]
    today = datetime.now().date().isoformat()

    offenders = await attendance_collection.find(
        {
            "punch_in_campus_id": current_user["campus_id"],
            "date": today,
            "total_out_of_bounds_time": {"$gt": 30}
        }
    ).to_list(length=None)

    return [
        {
            "employee_id": record["user_id"],
            "name": record["user_full_name"],
            "total_out_of_bounds_time": record["total_out_of_bounds_time"]
        } for record in offenders
    ]


# ------------------------------------------
# ✅ WEEKLY GEO TRACKING VIOLATION REPORT
# ------------------------------------------
@router.get("/attendance/weekly-geofencing")
async def weekly_geofencing_report(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_mongo_db)
):
    """Fetch a weekly report of geofencing violations in admin's assigned campus."""
    attendance_collection = db["attendance"]
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    offenders = await attendance_collection.find(
        {
            "punch_in_campus_id": current_user["campus_id"],
            "date": {"$gte": start_of_week.isoformat(), "$lte": today.isoformat()},
            "total_out_of_bounds_time": {"$gt": 30}
        }
    ).to_list(length=None)

    return [
        {
            "employee_id": record["user_id"],
            "name": record["user_full_name"],
            "total_out_of_bounds_time": record["total_out_of_bounds_time"]
        } for record in offenders
    ]


# ------------------------------------------
# ✅ MANAGE LEAVE REQUESTS (Approve/Reject)
# ------------------------------------------
@router.get("/leave-requests", dependencies=[Depends(role_required(["admin"]))])
async def get_leave_requests(
    current_user: dict = Depends(get_current_user), 
    db=Depends(get_mongo_db)
):
    """Fetch all pending leave requests for employees in the assigned campus."""
    leave_collection = db["leave_requests"]

    leave_requests = await leave_collection.find(
        {"campus_id": current_user["campus_id"], "status": "Pending"}
    ).to_list(length=None)

    return leave_requests


@router.post("/leave-requests/{leave_id}/approve")
async def approve_leave_request(
    leave_id: str, 
    db=Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Approve a leave request."""
    leave_collection = db["leave_requests"]
    
    leave = await leave_collection.find_one({"_id": leave_id})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave["campus_id"] != current_user["campus_id"]:
        raise HTTPException(status_code=403, detail="You can only approve leave requests for your campus.")

    await leave_collection.update_one({"_id": leave_id}, {"$set": {"status": "Approved"}})
    
    return {"message": "Leave request approved successfully"}


@router.post("/leave-requests/{leave_id}/reject")
async def reject_leave_request(
    leave_id: str, 
    reason: str, 
    db=Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Reject a leave request with a reason."""
    leave_collection = db["leave_requests"]

    leave = await leave_collection.find_one({"_id": leave_id})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave["campus_id"] != current_user["campus_id"]:
        raise HTTPException(status_code=403, detail="You can only reject leave requests for your campus.")

    await leave_collection.update_one({"_id": leave_id}, {"$set": {"status": "Rejected", "rejection_reason": reason}})
    
    return {"message": f"Leave request rejected. Reason: {reason}"}


# ------------------------------------------
# ✅ ADMIN: ISSUE RED NOTICE FOR REPEATED GEOFENCE VIOLATIONS
# ------------------------------------------
@router.post("/attendance/red-notice/{user_id}")
async def issue_red_notice(
    user_id: str, 
    reason: str, 
    db=Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Issues a red notice if an employee repeatedly violates geofencing rules."""
    attendance_collection = db["attendance"]

    user_attendance = await attendance_collection.count_documents(
        {"user_id": user_id, "punch_in_campus_id": current_user["campus_id"], "total_out_of_bounds_time": {"$gt": 30}}
    )

    if user_attendance >= 5:
        return {"message": f"Red notice issued for {user_id} due to repeated geofencing violations."}

    return {"message": "User does not meet red notice criteria yet."}
