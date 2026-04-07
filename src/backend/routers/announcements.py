"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson.objectid import ObjectId
import uuid

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("")
def get_announcements() -> List[Dict[str, Any]]:
    """Get all announcements (public endpoint)"""
    announcements = list(announcements_collection.find())
    
    # Convert ObjectId to string for JSON serialization and filter expired ones
    result = []
    now = datetime.now()
    
    for announcement in announcements:
        # Skip expired announcements
        if announcement.get("expiration_date") and announcement["expiration_date"] < now:
            continue
            
        # Check if announcement has started (if start_date is provided)
        if announcement.get("start_date") and announcement["start_date"] > now:
            continue
            
        announcement["_id"] = str(announcement["_id"])
        result.append(announcement)
    
    return result


@router.get("/all")
def get_all_announcements() -> List[Dict[str, Any]]:
    """Get all announcements including expired ones (for admin management)"""
    announcements = list(announcements_collection.find())
    
    # Convert ObjectId to string for JSON serialization
    result = []
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
        result.append(announcement)
    
    return result


@router.post("")
def create_announcement(
    title: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    username: str = Query(...)
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    
    # Check if user is logged in
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Parse dates
    try:
        exp_date = datetime.fromisoformat(expiration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    
    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    
    # Validate expiration date is in the future
    if exp_date < datetime.now():
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")
    
    # Create announcement
    announcement = {
        "_id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "start_date": start_dt,
        "expiration_date": exp_date,
        "created_by": username,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    expiration_date: Optional[str] = None,
    start_date: Optional[str] = None,
    username: str = Query(...)
) -> Dict[str, Any]:
    """Update an announcement (requires authentication)"""
    
    # Check if user is logged in
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Find the announcement
    announcement = announcements_collection.find_one({"_id": announcement_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Prepare update data
    update_data = {"updated_at": datetime.now()}
    
    if title is not None:
        update_data["title"] = title
    
    if message is not None:
        update_data["message"] = message
    
    if expiration_date is not None:
        try:
            exp_date = datetime.fromisoformat(expiration_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
        if exp_date < datetime.now():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        update_data["expiration_date"] = exp_date
    
    if start_date is not None:
        try:
            start_dt = datetime.fromisoformat(start_date)
            update_data["start_date"] = start_dt
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    
    # If start_date is empty string, set it to None
    if start_date == "":
        update_data["start_date"] = None
    
    # Update the announcement
    announcements_collection.update_one(
        {"_id": announcement_id},
        {"$set": update_data}
    )
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": announcement_id})
    updated["_id"] = str(updated["_id"])
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    username: str = Query(...)
) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    
    # Check if user is logged in
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Find and delete the announcement
    result = announcements_collection.delete_one({"_id": announcement_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
