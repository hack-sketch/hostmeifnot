from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from shapely.geometry import Point, Polygon
from sqlalchemy.sql import func
from fastapi.responses import StreamingResponse
from app.utils.auth import get_current_user, check_within_geofence
from app.database import get_mongo_db
from app.models import Attendance, Campus, User

router = APIRouter()

# ------------------------------------------
# ✅ PUNCH-IN API (With Geofencing)
# ------------------------------------------
@router.post("/attendance/punch-in")
async def punch_in(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_mongo_db)
):
    today = datetime.now(pytz.UTC).date()

    # Check for existing punch-in
    existing_attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()

    if existing_attendance and existing_attendance.punch_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already punched in today"
        )

    # Identify the campus
    campuses = db.query(Campus).all()
    for campus in campuses:
        if check_within_geofence(latitude, longitude, campus.geo_boundary):
            attendance = Attendance(
                user_id=current_user.id,
                punch_in=datetime.now(pytz.UTC),
                punch_in_campus_id=campus.id,
                status="Present",
                total_out_of_bounds_time=0,  # Reset out-of-campus tracking
                exit_time=None
            )
            db.add(attendance)
            db.commit()
            return {"message": f"Punched in at {campus.name}", "status": "success"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Punch-in location outside campus geofence"
    )

# ------------------------------------------
# ✅ PUNCH-OUT API (With Geofencing)
# ------------------------------------------
@router.post("/attendance/punch-out")
async def punch_out(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_mongo_db)
):
    today = datetime.now(pytz.UTC).date()

    # Find the user's punch-in record for today
    attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()

    if not attendance or not attendance.punch_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No punch-in record found for today"
        )

    if attendance.punch_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already punched out today"
        )

    # Identify the campus
    campuses = db.query(Campus).all()
    for campus in campuses:
        if check_within_geofence(latitude, longitude, campus.geo_boundary):
            attendance.punch_out = datetime.now(pytz.UTC)
            attendance.punch_out_campus_id = campus.id
            attendance.total_hours = (attendance.punch_out - attendance.punch_in).total_seconds() / 3600
            db.commit()
            return {
                "message": f"Punched out at {campus.name}",
                "total_hours": attendance.total_hours,
                "total_out_of_bounds_time": attendance.total_out_of_bounds_time,
                "status": "success"
            }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Punch-out location outside campus geofence"
    )

# ------------------------------------------
# ✅ GEOLOCATION CHECK API (Runs Every 5 Min)
# ✅ Tracks Faculty If They Leave The Campus
# ------------------------------------------
@router.post("/attendance/check-location")
async def track_user_location(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_mongo_db)
):
    today = datetime.now(pytz.UTC).date()

    # Check for active attendance record
    attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today,
        Attendance.punch_out == None
    ).first()

    if not attendance:
        raise HTTPException(status_code=400, detail="No active punch-in session found.")

    # Identify faculty's campus
    campus = db.query(Campus).filter(Campus.id == attendance.punch_in_campus_id).first()

    if not check_within_geofence(latitude, longitude, campus.geo_boundary):
        if attendance.exit_time is None:
            attendance.exit_time = datetime.utcnow()  # Mark initial exit time

        # Calculate total time outside campus
        time_outside = (datetime.utcnow() - attendance.exit_time).total_seconds() / 60  # Convert to minutes
        # if time_outside >= 30:
        #     attendance.total_out_of_bounds_time += time_outside
        #     attendance.exit_time = datetime.utcnow()  # Reset exit time
        # For testing, add time immediately (without waiting 30 min)
        attendance.total_out_of_bounds_time += 1  # Add 1 minute per out-of-bound ping
        attendance.exit_time = datetime.utcnow()  # Reset exit time


    else:
        attendance.exit_time = None  # Reset if user returns inside

    db.commit()

    # 🚨 Notify If Faculty Is Out for More Than 30 Min
    # if attendance.total_out_of_bounds_time > 30:
    if attendance.total_out_of_bounds_time > 0:
        return {"warning": f"You have been outside the campus for {attendance.total_out_of_bounds_time} minutes today."}

    return {"status": "Tracking active"}

# ------------------------------------------
# ✅ ADMIN/SUPERADMIN: GET DAILY GEO TRACKING DATA
# ------------------------------------------
@router.get("/attendance/daily-geofencing")
async def daily_geofencing_data(
    db: Session = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches a list of employees who violated geofencing today."""
    today = datetime.now(pytz.UTC).date()
    query = db.query(Attendance).filter(
        func.date(Attendance.date) == today,
        Attendance.total_out_of_bounds_time > 30  # Employees who went out for more than 30 mins
    )

    if current_user.role == "admin":
        query = query.filter(Attendance.punch_in_campus_id == current_user.campus_id)

    offenders = query.all()
    
    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ ADMIN/SUPERADMIN: WEEKLY GEO TRACKING REPORT
# ------------------------------------------
@router.get("/attendance/weekly-geofencing")
async def weekly_geofencing_report(
    db: Session = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches a weekly report of geofencing violations."""
    today = datetime.now(pytz.UTC).date()
    start_of_week = today - timedelta(days=today.weekday())

    query = db.query(Attendance).filter(
        Attendance.date >= start_of_week,
        Attendance.date <= today,
        Attendance.total_out_of_bounds_time > 30
    )

    if current_user.role == "admin":
        query = query.filter(Attendance.punch_in_campus_id == current_user.campus_id)

    offenders = query.all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ SUPERADMIN: ISSUE RED NOTICE FOR REPEATED VIOLATIONS
# ------------------------------------------
@router.post("/attendance/red-notice/{user_id}")
async def issue_red_notice(
    user_id: int,
    reason: str,
    db: Session = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user)
):
    """Issues a red notice if a user repeatedly violates geofencing rules."""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized action.")

    user_attendance = db.query(Attendance).filter(
        Attendance.user_id == user_id,
        Attendance.total_out_of_bounds_time > 30
    ).count()

    if user_attendance >= 5:  # If violations occurred for 5+ days
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.red_notice_issued = True
            user.red_notice_reason = reason
            db.commit()
            return {"message": f"Red notice issued to {user.full_name} for repeated geofencing violations."}

    return {"message": "User does not meet red notice criteria yet."}
