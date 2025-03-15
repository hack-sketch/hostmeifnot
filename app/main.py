from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, profile, attendance, admin, super_admin, inventory_admin, sync, user
from .database import get_mongo_db #EpushSessionLocal
import asyncio

app = FastAPI(title="DSEU Dashboard API")

# ✅ CORS Middleware (Security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with actual frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include API Routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(profile.router, tags=["profile"])
app.include_router(attendance.router, tags=["attendance"])
app.include_router(user.router, prefix="/employee", tags=["user"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(super_admin.router, prefix="/super-admin", tags=["super_admin"])
app.include_router(inventory_admin.router, prefix="/inventory-admin", tags=["inventory_admin"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])

# ------------------------------------------
# ✅ Startup Event: MongoDB + EPUSH Sync
# ------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Application...")

    # ✅ Ensure MongoDB connection
    try:
        mongo_db = get_mongo_db()
        print("✅ MongoDB Connected.")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")

    # ✅ Ensure MySQL (EPUSH) connection
    # try:
    #     session = EpushSessionLocal()
    #     session.execute("SELECT 1")  # Quick connection test
    #     print("✅ MySQL (EPUSH) Connected.")
    #     session.close()
    # except Exception as e:
    #     print(f"❌ MySQL (EPUSH) Connection Failed: {e}")

    print("🎯 All systems initialized.")

# ------------------------------------------
# ✅ Shutdown Event
# ------------------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    print("⚡ Application shutting down...")

# ------------------------------------------
# ✅ Root API Check
# ------------------------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the DSEU Employee Attendance Dashboard API!"}
