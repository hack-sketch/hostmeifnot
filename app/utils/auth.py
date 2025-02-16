import os
import logging
import re
import smtplib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from shapely.geometry import Point, Polygon
from app.database import get_mongo_db
from fastapi.security import OAuth2PasswordBearer

# ✅ Security & JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ✅ Email Configuration (Use Environment Variables)
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# ✅ OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ✅ Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ Logger Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Email Regex Patterns
EMPLOYEE_EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@dseu\.ac\.in$"
ADMIN_EMAIL_REGEX = r"^(director-[a-z]+|hroffice)@dseu\.ac\.in$"
SUPER_ADMIN_EMAIL_REGEX = r"^(vc|vcoffice)@dseu\.ac\.in$"

# ------------------------------------------
# ✅ FUNCTION: ASSIGN ROLE BASED ON EMAIL
# ------------------------------------------
def assign_role(email: str):
    """Determines user role based on email format."""
    if re.match(SUPER_ADMIN_EMAIL_REGEX, email):
        return "super_admin"
    elif re.match(ADMIN_EMAIL_REGEX, email):
        return "admin"
    elif re.match(EMPLOYEE_EMAIL_REGEX, email):
        return "employee"
    return None

# ------------------------------------------
# ✅ PASSWORD HASHING & VERIFICATION
# ------------------------------------------
def verify_password(plain_password, hashed_password):
    """Verify the entered password with stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password using bcrypt."""
    return pwd_context.hash(password)

# ------------------------------------------
# ✅ EMAIL OTP FUNCTION FOR SIGNUP & PASSWORD RESET
# ------------------------------------------
def send_otp_email(recipient_email: str, otp: str):
    """Send OTP via email."""
    try:
        message = MIMEMultipart()
        message["From"] = EMAIL_USERNAME
        message["To"] = recipient_email
        message["Subject"] = "Your OTP for Account Verification"

        body = (
            f"Hello,\n\n"
            f"Your OTP for verification is: {otp}.\n"
            f"It is valid for the next 15 minutes.\n\n"
            f"Regards,\nDSEU IT Team"
        )
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending email, please try again later."
        )

# ------------------------------------------
# ✅ JWT AUTHENTICATION: GENERATE ACCESS TOKEN
# ------------------------------------------
def create_access_token(data: dict):
    """Generate JWT token with user email & role."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ------------------------------------------
# ✅ AUTHENTICATION: GET CURRENT USER FROM JWT
# ------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme)):
    """Extract and validate user from JWT token (MongoDB version)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    mongo_db = get_mongo_db()
    user = mongo_db["users"].find_one({"email": email})

    if not user:
        raise credentials_exception

    return user

# ------------------------------------------
# ✅ ROLE-BASED ACCESS CONTROL
# ------------------------------------------
def role_required(required_roles: list):
    """Restrict access based on user roles (MongoDB version)."""
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.get("role") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions."
            )
        return current_user
    return role_checker

# ------------------------------------------
# ✅ CHECK IF USER IS WITHIN A CAMPUS GEOFENCE
# ------------------------------------------
def check_within_geofence(latitude: float, longitude: float, geo_boundary: str):
    """Check if user coordinates are inside the campus geofence."""
    if not geo_boundary:
        return False
    boundary_points = [tuple(map(float, coord.split(','))) for coord in geo_boundary.split(';')]
    polygon = Polygon(boundary_points)
    point = Point(latitude, longitude)
    return polygon.contains(point)
