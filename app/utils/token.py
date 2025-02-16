import os
from datetime import datetime, timedelta
from jose import JWTError, jwt

# ✅ Load secret key & algorithm from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ------------------------------------------
# ✅ FUNCTION: CREATE ACCESS TOKEN (JWT)
# ------------------------------------------
def create_access_token(data: dict):
    """Generate JWT access token with expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ------------------------------------------
# ✅ FUNCTION: VERIFY ACCESS TOKEN
# ------------------------------------------
def verify_access_token(token: str):
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
