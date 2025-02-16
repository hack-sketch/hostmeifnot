# from fastapi import APIRouter
# #from app.utils.sync_epush import fetch_epush_data  

# router = APIRouter()

# @router.get("/sync-epush")
# async def sync_epush():
#     """
#     🔄 Triggers EPUSH Data Sync to MongoDB
#     """
#     result = fetch_epush_data()
#     return result


from fastapi import APIRouter
from app.utils.sync_epush import fetch_mongo_data  # ✅ Updated to use MongoDB sync

router = APIRouter()

@router.get("/sync-mongo")
async def sync_mongo():
    """Trigger MongoDB Attendance Sync"""
    result = fetch_mongo_data()
    return result
