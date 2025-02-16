from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import MongoClient
from bson import ObjectId
from app.utils.auth import role_required, get_current_user
from app.database import get_mongo_db

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ALL INVENTORY ITEMS (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.get("/inventory/items", dependencies=[Depends(role_required(["inventory_admin"]))])
async def get_inventory_items(
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Fetch all inventory items for the logged-in inventory admin's campus"""
    inventory = list(db["inventory"].find({"campus_id": current_user["campus_id"]}))

    return [
        {
            "item_id": str(item["_id"]),
            "name": item["name"],
            "quantity": item["quantity"],
            "category": item["category"],
            "campus_id": item["campus_id"]
        }
        for item in inventory
    ]

# ------------------------------------------
# ✅ ADD NEW INVENTORY ITEM (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.post("/inventory/items", dependencies=[Depends(role_required(["inventory_admin"]))])
async def add_inventory_item(
    name: str, 
    quantity: int, 
    category: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Add a new inventory item (Only inventory admins can add items)"""

    new_item = {
        "name": name,
        "quantity": quantity,
        "category": category,
        "campus_id": current_user["campus_id"]
    }

    result = db["inventory"].insert_one(new_item)

    return {"message": f"Item {name} added successfully!", "item_id": str(result.inserted_id)}

# ------------------------------------------
# ✅ UPDATE INVENTORY ITEM (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.put("/inventory/items/{item_id}", dependencies=[Depends(role_required(["inventory_admin"]))])
async def update_inventory_item(
    item_id: str, 
    quantity: int, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Update inventory item quantity (Only for inventory admin)"""

    item = db["inventory"].find_one({"_id": ObjectId(item_id), "campus_id": current_user["campus_id"]})

    if not item:
        raise HTTPException(status_code=404, detail="Item not found or not in your campus inventory")

    db["inventory"].update_one({"_id": ObjectId(item_id)}, {"$set": {"quantity": quantity}})

    return {"message": f"Item {item['name']} updated successfully!", "new_quantity": quantity}

# ------------------------------------------
# ✅ DELETE INVENTORY ITEM (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.delete("/inventory/items/{item_id}", dependencies=[Depends(role_required(["inventory_admin"]))])
async def delete_inventory_item(
    item_id: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Delete an inventory item (Only for inventory admin)"""

    item = db["inventory"].find_one({"_id": ObjectId(item_id), "campus_id": current_user["campus_id"]})

    if not item:
        raise HTTPException(status_code=404, detail="Item not found or not in your campus inventory")

    db["inventory"].delete_one({"_id": ObjectId(item_id)})

    return {"message": f"Item {item['name']} deleted successfully!"}

# ------------------------------------------
# ✅ REQUEST NEW INVENTORY ITEM (FOR EMPLOYEES)
# ------------------------------------------
@router.post("/inventory/request", dependencies=[Depends(role_required(["employee"]))])
async def request_inventory_item(
    item_id: str, 
    requested_quantity: int, 
    reason: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Employees can request inventory items for official use"""

    item = db["inventory"].find_one({"_id": ObjectId(item_id)})

    if not item or item["quantity"] < requested_quantity:
        raise HTTPException(status_code=400, detail="Requested quantity not available")

    request = {
        "user_id": str(current_user["_id"]),
        "item_id": item_id,
        "requested_quantity": requested_quantity,
        "reason": reason,
        "status": "Pending"
    }

    db["inventory_requests"].insert_one(request)

    return {"message": "Inventory request submitted successfully!"}

# ------------------------------------------
# ✅ VIEW ALL INVENTORY REQUESTS (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.get("/inventory/requests", dependencies=[Depends(role_required(["inventory_admin"]))])
async def get_inventory_requests(
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Inventory admins can view all requests for their campus"""

    requests = list(db["inventory_requests"].aggregate([
        {
            "$lookup": {
                "from": "inventory",
                "localField": "item_id",
                "foreignField": "_id",
                "as": "item"
            }
        },
        {"$unwind": "$item"},
        {"$match": {"item.campus_id": current_user["campus_id"]}}
    ]))

    return [
        {
            "request_id": str(req["_id"]),
            "item_name": req["item"]["name"],
            "requested_by": req["user_id"],  # Could use another lookup to get user name
            "requested_quantity": req["requested_quantity"],
            "status": req["status"]
        }
        for req in requests
    ]

# ------------------------------------------
# ✅ APPROVE OR REJECT INVENTORY REQUESTS (FOR INVENTORY ADMIN)
# ------------------------------------------
@router.put("/inventory/requests/{request_id}", dependencies=[Depends(role_required(["inventory_admin"]))])
async def process_inventory_request(
    request_id: str, 
    status: str, 
    db: MongoClient = Depends(get_mongo_db), 
    current_user: dict = Depends(get_current_user)
):
    """Approve or Reject an inventory request (Only for inventory admin)"""

    inventory_request = db["inventory_requests"].find_one({"_id": ObjectId(request_id)})

    if not inventory_request:
        raise HTTPException(status_code=404, detail="Request not found")

    if status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status update")

    if status == "Approved":
        item = db["inventory"].find_one({"_id": ObjectId(inventory_request["item_id"])})

        if item["quantity"] < inventory_request["requested_quantity"]:
            raise HTTPException(status_code=400, detail="Not enough inventory available")

        db["inventory"].update_one(
            {"_id": ObjectId(inventory_request["item_id"])},
            {"$inc": {"quantity": -inventory_request["requested_quantity"]}}
        )

    db["inventory_requests"].update_one({"_id": ObjectId(request_id)}, {"$set": {"status": status}})

    return {"message": f"Request {request_id} updated to {status}"}
