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



@router.post("/meetings/add", response_model=_schemas.Meeting)
async def create_meeting(
    meeting: _schemas.MeetingCreate,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # Create and persist a meeting for the authenticated user
    new_meeting = _models.Meeting(
        meeting_name=meeting.meeting_name,
        meeting_date=meeting.meeting_date,
        user_id=user.id
    )
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)

    logger.info(f"Meeting '{meeting.meeting_name}' created by user {user.email}")
    return new_meeting


@router.get("/list_meetings", response_model=list[_schemas.Meeting])
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


@router.post("/add_participants/{meeting_id}", response_model=List[_schemas.Participant])
async def add_multiple_participants(
    meeting_id: int,
    participants: List[_schemas.ParticipantCreate],
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    meeting = db.query(_models.Meeting).filter(
        _models.Meeting.id == meeting_id,
        _models.Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_objs = []
    for p in participants:
        participant_obj = _models.Participant(
            name=p.name,
            email=p.email,
            meeting_id=meeting.id
        )
        db.add(participant_obj)
        participant_objs.append(participant_obj)

    db.commit()
    for p in participant_objs:
        db.refresh(p)
        

    return participant_objs


from fastapi import status

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
