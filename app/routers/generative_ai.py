from fastapi import APIRouter ,  HTTPException 
import fastapi as _fastapi
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL
from app.helpers.utils import get_embedding, retrieve_similar_documents, build_qa_prompt , generate_llm_answer , meeting_minutes_prompt , parse_meeting_minutes , summarize_text
from app.logger import Logger
import sqlalchemy.orm as _orm
import os 

# Create an instance of the Logger class
logger_instance = Logger()
# Get a logger for your module
logger = logger_instance.get_logger("generative_ai")
router = APIRouter(
    tags=["generative_ai"])


def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ai/meeting_qna")
async def meeting_qna(  
    meeting: _schemas.MeetingQandA,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    question = meeting.question
    meeting_id = meeting.meeting_id

    # 🔐 Validate ownership of meeting
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found or not authorized")

    index_name = str(meeting_id)

    # Step 1: Get embedding
    try:
        embedding = get_embedding(question)
    except Exception as e:
        logger.error(f"Embedding failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

    # Step 2: Retrieve similar chunks
    try:
        context_chunks = retrieve_similar_documents(text=question, embedding=embedding, index_name=index_name)
    except Exception as e:
        logger.error(f"Document retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve context")

    if not context_chunks:
        raise HTTPException(status_code=404, detail="No relevant context found")

    # Step 3: Build prompt
    prompt = build_qa_prompt(question, context_chunks)

    # Step 4: Generate LLM answer
    try:
        answer = generate_llm_answer(prompt)
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate answer")

    return {"question": question, "answer": answer}




@router.post("/ai/meeting_minutes/")
async def generate_meeting_minutes(
    meeting_input: _schemas.MeetingMinutes,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
   
    meeting_id = meeting_input.meeting_id
    language = meeting_input.language
    


    # 🔐 Validate meeting ownership
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise _fastapi.HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 🗂️ Fetch related MeetingLibrary record
    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library_entry or not library_entry.transcript_path:
        raise _fastapi.HTTPException(status_code=404, detail="Transcript path not found in MeetingLibrary")

    transcript_path = library_entry.transcript_path
    if not os.path.exists(transcript_path):
        raise _fastapi.HTTPException(status_code=404, detail="Transcript file not found on disk")

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()
    except Exception as e:
        logger.error(f"Failed to read transcript: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to read transcript")

    # 🧠 Build prompt for meeting minutes
    context_chunks = [{"text": transcript_text}]
    prompt = meeting_minutes_prompt(context_chunks)

    # ✨ Call LLM to generate minutes
    try:
        meeting_minutes = generate_llm_answer(prompt)
        structured = parse_meeting_minutes(meeting_minutes)

    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to generate meeting minutes")

    return {"meeting_id": meeting_id, "neeting_of_minutes": structured}


@router.get("/meeting_summary/{meeting_id}")
async def generate_meeting_summary(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):

    # 🔐 Validate meeting ownership
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise _fastapi.HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 🗂️ Fetch related transcript
    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library_entry or not library_entry.transcript_path:
        raise _fastapi.HTTPException(status_code=404, detail="Transcript path not found in MeetingLibrary")

    transcript_path = library_entry.transcript_path
    if not os.path.exists(transcript_path):
        raise _fastapi.HTTPException(status_code=404, detail="Transcript file not found on disk")

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()
    except Exception as e:
        logger.error(f"Failed to read transcript: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to read transcript")

    # ✨ Summarize transcript
    try:
        summary = summarize_text(transcript_text)
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to summarize transcript")

    return {
        "meeting_id": meeting_id,
        "summary": summary
    }