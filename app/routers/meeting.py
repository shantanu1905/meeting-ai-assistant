from fastapi import APIRouter ,  HTTPException , BackgroundTasks
import fastapi as _fastapi
from fastapi.responses import JSONResponse
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import sqlalchemy.orm as _orm
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.logger import Logger
from typing import List, Optional
import os
from app.helpers.utils import  MeetingCleanup

from fastapi import status

# Create an instance of the Logger class
logger_instance = Logger()
# Get a logger for your module
logger = logger_instance.get_logger("meeting_router")
router = APIRouter(
    tags=["meeting_router"])


def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/meetings/create")
async def create_meeting_with_participants(
    meeting_data: _schemas.MeetingCreate,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    try:
        # Create the meeting
        new_meeting = _models.Meeting(
            meeting_name=meeting_data.meeting_name,
            meeting_date=meeting_data.meeting_date,
            meeting_description=meeting_data.meeting_description,
            user_id=user.id
        )
        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)

        # Add participants if provided
        participant_objs = []
        if meeting_data.participants:
            for p in meeting_data.participants:
                participant_obj = _models.Participant(
                    name=p.name,
                    email=p.email,
                    meeting_id=new_meeting.id
                )
                db.add(participant_obj)
                participant_objs.append(participant_obj)

            db.commit()
            for p in participant_objs:
                db.refresh(p)

        logger.info(f"Meeting '{new_meeting.meeting_name}' created by user {user.email} with {len(participant_objs)} participants.")
        
        return JSONResponse(
            status_code=201,
            content={
                "message": f"Successfully created meeting: '{new_meeting.meeting_name}'",
                "meeting": {
                    "id": new_meeting.id,
                    "meeting_name": new_meeting.meeting_name,
                    "meeting_date": new_meeting.meeting_date.isoformat() if new_meeting.meeting_date else None,
                    "meeting_description": new_meeting.meeting_description,
                    "participants": [{"name": p.name, "email": p.email} for p in participant_objs],
                }
            }
        )

    except Exception as e:
        logger.error(f"Failed to create meeting: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while creating the meeting.")




@router.get("/meetings/list", response_model=list[_schemas.MeetingResponse])
async def get_meeting_details(
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    meetings = (
        db.query(_models.Meeting)
        .filter(_models.Meeting.user_id == user.id)
        .all()
    )

    if not meetings:
        logger.warning(f"No meetings found for user {user.email}")
        raise HTTPException(status_code=404, detail="No meetings found")

    logger.info(f"Retrieved {len(meetings)} meetings for user {user.email}")
    return meetings



@router.get("/meetings/details/{meeting_id}", response_model=_schemas.MeetingResponse)
async def get_meeting_by_id(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    meeting = (
        db.query(_models.Meeting)
        .filter(_models.Meeting.id == meeting_id, _models.Meeting.user_id == user.id)
        .first()
    )

    if not meeting:
        logger.error(f"Meeting ID {meeting_id} not found for user {user.email}")
        raise HTTPException(status_code=404, detail="Meeting not found")

    logger.info(f"Retrieved meeting '{meeting.meeting_name}' (ID: {meeting.id}) for user {user.email}")
    return meeting



@router.delete("/meetings/delete/{meeting_id}", response_model=dict)
async def delete_meeting(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting not found for meeting_id {meeting_id}")

    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()

    cleanup = MeetingCleanup()

    # Delete Redis vectors
    redis_deleted_count = cleanup.delete_rag_redis_vectors(str(meeting_id))

    # Delete local files
    deleted_file_paths = cleanup.delete_all_meeting_files(library_entry)

    # Delete DB records
    if library_entry:
        db.delete(library_entry)
    db.delete(meeting)
    db.commit()

    return {
        "detail": f"Meeting {meeting_id} deleted successfully",
        "redis_vectors_deleted": redis_deleted_count,
        "files_deleted": deleted_file_paths
    }




@router.delete("/delete_participant/{participant_id}", status_code=status.HTTP_200_OK)
async def delete_participant(
    participant_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # Fetch the participant
    participant = db.query(_models.Participant).filter(_models.Participant.id == participant_id).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Confirm the current user owns the meeting this participant belongs to
    meeting = db.query(_models.Meeting).filter(
        _models.Meeting.id == participant.meeting_id,
        _models.Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=403, detail="Not authorized to delete this participant")

    db.delete(participant)
    db.commit()

    return {"message": f"Participant with ID {participant_id} deleted successfully."}



@router.get("/meetings/media/{meeting_id}", response_model=dict)
async def get_meeting_media_files(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Ensure user owns the meeting
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found ")

    # 📦 Get associated file paths from MeetingLibrary
    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library_entry:
        raise HTTPException(status_code=404, detail="MeetingLibrary entry not found")

    # 📂 Collect available file paths
    media_files = {}
    for column in library_entry.__table__.columns:
        if "path" in column.name:
            file_path = getattr(library_entry, column.name)
            if file_path and os.path.exists(file_path):
                media_files[column.name] = file_path
            elif file_path:
                media_files[column.name] = "File not found on disk"

    return {
        "meeting_id": meeting_id,
        "media_files": media_files
    }


@router.get("/meetings/chathistory/{meeting_id}", response_model=List[dict])
async def get_chat_history(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Ensure meeting belongs to user
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found ")

    # 📜 Get chat messages ordered by timestamp
    messages = (
        db.query(_models.ChatMessage)
        .filter_by(meeting_id=meeting_id)
        .order_by(_models.ChatMessage.timestamp.asc())
        .all()
    )

    if not messages:
        raise HTTPException(status_code=404, detail="No chat history found for this meeting")

    chat_history = [
        {
            "message": msg.message,
            "sender_type": msg.sender_type,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

    return chat_history