
from fastapi import APIRouter ,  HTTPException , BackgroundTasks
import fastapi as _fastapi
from fastapi import UploadFile, File, Form
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import sqlalchemy.orm as _orm
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.helpers.constants import DATAPREP_URL, UPLOAD_DIR
from app.logger import Logger
import requests
import os 
import shutil

# Create an instance of the Logger class
logger_instance = Logger()
# Get a logger for your module
logger = logger_instance.get_logger("user_metadata")
router = APIRouter(
    tags=["user_metadata"])


def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload_meeting_file/{meeting_id}", response_model=_schemas.MeetingLibraryResponse)
async def upload_single_meeting_file(
    meeting_id: int,
    file: UploadFile = File(...),
    filetype: str = Form(...),  # Accepts 'transcript', 'audio', or 'video'
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    valid_types = ["transcript", "audio", "video"]
    if filetype not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid filetype. Must be 'transcript', 'audio', or 'video'")

    meeting = db.query(_models.Meeting).filter(
        _models.Meeting.id == meeting_id,
        _models.Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found or not authorized")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{filetype}_{meeting_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save path to DB
    library = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library:
        library = _models.MeetingLibrary(meeting_id=meeting_id)
        db.add(library)

    setattr(library, f"{filetype}_path", file_path)
    db.commit()
    db.refresh(library)

    # 🔄 In-place File Processing (send to DataPrep)
    try:
        with open(file_path, 'rb') as f:
            files = {'files': (filename, f)}
            data = {
                "index_name": str(meeting_id),
                "chunk_size": "500",
                "chunk_overlap": "200"
            }
            r = requests.post(DATAPREP_URL, files=files, data=data)
            r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"File uploaded but embedding failed: {str(e)}")

    return library
    


