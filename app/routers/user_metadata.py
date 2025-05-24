
from fastapi import APIRouter ,  HTTPException , BackgroundTasks
from fastapi.responses import StreamingResponse
import fastapi as _fastapi
from fastapi import UploadFile, File, Form
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import sqlalchemy.orm as _orm
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.helpers.constants import DATAPREP_URL, UPLOAD_DIR 
from app.helpers.utils import transcribe_audio
from app.logger import Logger
import requests
import os 
import shutil
import moviepy as mp

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
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    ext = file.filename.split('.')[-1].lower()
    if ext not in ["txt", "mp3", "wav", "mp4"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Must be .txt, .mp3, .wav, or .mp4")

    meeting = db.query(_models.Meeting).filter(
        _models.Meeting.id == meeting_id,
        _models.Meeting.user_id == user.id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{meeting_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Prepare meeting library record
    library = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library:
        library = _models.MeetingLibrary(meeting_id=meeting_id)
        db.add(library)

    transcript_text = None
    if ext == "txt":
        library.transcript_path = file_path
    elif ext in ["mp3", "wav"]:
        library.audio_path = file_path
        transcript_text = transcribe_audio(file_path)
    elif ext == "mp4":
        library.video_path = file_path
        audio_temp_path = file_path.replace(".mp4", ".mp3")
        try:
            mp.VideoFileClip(file_path).audio.write_audiofile(audio_temp_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract audio: {str(e)}")

        transcript_text = transcribe_audio(audio_temp_path)

    # If transcription done, save to .txt
    if transcript_text:
        transcript_path = file_path.rsplit('.', 1)[0] + "_transcript.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        library.transcript_path = transcript_path

    db.commit()
    db.refresh(library)

    # Vector embedding call
    try:
        with open(library.transcript_path, 'rb') as f:
            files = {'files': (os.path.basename(library.transcript_path), f)}
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


@router.get("/meetings/media_stream/{meeting_id}")
async def stream_meeting_file(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    meeting = db.query(_models.Meeting).filter(
        _models.Meeting.id == meeting_id,
        _models.Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    library = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="No media available for this meeting or you have uploaded transcript only")

    # Prefer video if available, otherwise audio
    file_path = library.video_path or library.audio_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    # Determine MIME type
    ext = os.path.splitext(file_path)[-1].lower()
    media_type = {
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav"
    }.get(ext, "application/octet-stream")

    def file_stream():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(file_stream(), media_type=media_type)