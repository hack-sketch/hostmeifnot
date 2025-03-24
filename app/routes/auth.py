from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import MongoClient
from datetime import datetime, timedelta
import pyotp
import re
from bson import ObjectId
from app.utils.auth import (
    verify_password,
    get_password_hash,
    send_otp_email,
    create_access_token,
    assign_role
)
from app.database import get_mongo_db
from app.schemas import UserSchema  
from app.models import User  
from pydantic import BaseModel, EmailStr

router = APIRouter()

PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$%^&+=]).{6,}$"

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

# ------------------------------------------
# ✅ SIGNUP API (Step 1: Send OTP)
# ------------------------------------------
@router.post("/signup")
async def signup(request: SignupRequest, db: MongoClient = Depends(get_mongo_db)):
    role = assign_role(request.email)
    if role is None:
        raise HTTPException(status_code=400, detail="Invalid email. Use a valid @dseu.ac.in email.")

    if not re.match(PASSWORD_REGEX, request.password):
        raise HTTPException(status_code=400, detail="Password must meet security requirements.")

    existing_user = db["users"].find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    secret = pyotp.random_base32()
    otp = pyotp.TOTP(secret, interval=900).now()
    send_otp_email(request.email, otp)

    new_user = {
        "email": request.email,
        "hashed_password": get_password_hash(request.password),
        "otp_secret": secret,
        "otp_expires": datetime.utcnow() + timedelta(minutes=15),
        "role": role,
        "is_active": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    db["users"].insert_one(new_user)
    return {"message": "OTP sent to email. Please verify."}

# ------------------------------------------
# ✅ VERIFY OTP (Step 2)
# ------------------------------------------
@router.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest, db: MongoClient = Depends(get_mongo_db)):
    user = db["users"].find_one({"email": request.email})

    if not user or "otp_secret" not in user:
        raise HTTPException(status_code=400, detail="Invalid request.")

    if user["otp_expires"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired. Request again.")

    totp = pyotp.TOTP(user["otp_secret"], interval=900)
    if not totp.verify(request.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    db["users"].update_one({"email": request.email}, {"$set": {"is_active": True, "otp_secret": None, "otp_expires": None, "updated_at": datetime.utcnow()}})

    return {"message": "Signup successful. You can now log in."}

# ------------------------------------------
# ✅ LOGIN API
# ------------------------------------------
@router.post("/login")
async def login(request: LoginRequest, db: MongoClient = Depends(get_mongo_db)):
    user = db["users"].find_one({"email": request.email})

    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    access_token = create_access_token({"sub": user["email"], "role": user["role"], "campus_id": user.get("campus_id")})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

# ------------------------------------------
# ✅ FORGOT PASSWORD (Step 1: Send OTP)
# ------------------------------------------
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: MongoClient = Depends(get_mongo_db)):
    if not assign_role(request.email):
        raise HTTPException(status_code=400, detail="Invalid email. Use an @dseu.ac.in email.")

    user = db["users"].find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    secret = pyotp.random_base32()
    otp = pyotp.TOTP(secret, interval=900).now()

    db["users"].update_one({"email": request.email}, {"$set": {"otp_secret": secret, "otp_expires": datetime.utcnow() + timedelta(minutes=15)}})

    send_otp_email(request.email, otp)
    return {"message": "OTP sent to email for password reset."}

# ------------------------------------------
# ✅ VERIFY OTP FOR PASSWORD RESET (Step 2)
# ------------------------------------------
@router.post("/verify-forgot-otp")
async def verify_forgot_otp(request: OTPVerifyRequest, db: MongoClient = Depends(get_mongo_db)):
    user = db["users"].find_one({"email": request.email})
    if not user or "otp_secret" not in user:
        raise HTTPException(status_code=400, detail="Invalid request.")

    if user["otp_expires"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired. Request again.")

    totp = pyotp.TOTP(user["otp_secret"], interval=900)
    if not totp.verify(request.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    db["users"].update_one({"email": request.email}, {"$set": {"otp_secret": None, "otp_expires": None, "updated_at": datetime.utcnow()}})

    return {"message": "OTP verified. You can now reset your password."}

# ------------------------------------------
# ✅ RESET PASSWORD (Step 3)
# ------------------------------------------
@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: MongoClient = Depends(get_mongo_db)):
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if not re.match(PASSWORD_REGEX, request.new_password):
        raise HTTPException(status_code=400, detail="Password must meet security requirements.")

    user = db["users"].find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request.")

    db["users"].update_one({"email": request.email}, {"$set": {"hashed_password": get_password_hash(request.new_password), "updated_at": datetime.utcnow()}})

    return {"message": "Password reset successful. You can now log in."}
