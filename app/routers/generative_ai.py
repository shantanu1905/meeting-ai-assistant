from fastapi import APIRouter ,  HTTPException 
import fastapi as _fastapi
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL
from app.helpers.utils import get_embedding, retrieve_similar_documents, build_qa_prompt , generate_llm_answer , meeting_minutes_prompt , parse_meeting_minutes , summarize_text , analyze_sentiment
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
    meeting_obj = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting_obj:
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

    # Step 5: Save chat messages
    user_message = _models.ChatMessage(
        meeting_id=meeting_id,
        message=question,
        sender_type="user"
    )

    bot_message = _models.ChatMessage(
        meeting_id=meeting_id,
        message=answer,
        sender_type="bot"
    )

    db.add_all([user_message, bot_message])
    db.commit()

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

    # 🧠 Check for existing AI insights
    insight = db.query(_models.MeetingInsights).filter_by(meeting_id=meeting_id).first()

    if insight and insight.is_minutes_stored and not insight.reset_requested:
        return {
            "meeting_id": meeting_id,
            "minutes_of_meeting": insight.minutes_of_meeting,
            "cached": True
        }

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

    # 🧠 Build prompt and call LLM
    context_chunks = [{"text": transcript_text}]
    prompt = meeting_minutes_prompt(context_chunks)

    try:
        meeting_minutes = generate_llm_answer(prompt)
        structured_minutes = parse_meeting_minutes(meeting_minutes)
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to generate meeting minutes")

    # 📝 Save or update MeetingInsights
    if insight:
        insight.minutes_of_meeting = structured_minutes
        insight.is_minutes_stored = True
        insight.reset_requested = False
    else:
        insight = _models.MeetingInsights(
            meeting_id=meeting_id,
            minutes_of_meeting=structured_minutes,
            is_minutes_stored=True,
            reset_requested=False
        )
        db.add(insight)

    db.commit()

    return {
        "meeting_id": meeting_id,
        "minutes_of_meeting": structured_minutes,
        "cached": False
    }

@router.get("/ai/summary/{meeting_id}")
async def generate_meeting_summary(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Validate meeting ownership
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise _fastapi.HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 🔍 Check existing insight
    insight = db.query(_models.MeetingInsights).filter_by(meeting_id=meeting_id).first()

    if insight and insight.is_summary_stored and not insight.reset_requested:
        return {
            "meeting_id": meeting_id,
            "summary": insight.summary,
            "cached": True
        }

    # 📄 Fetch transcript
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

    # ✨ Summarize
    try:
        summary = summarize_text(transcript_text)
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise _fastapi.HTTPException(status_code=500, detail="Failed to summarize transcript")

    # 💾 Save or update summary
    if insight:
        insight.summary = summary
        insight.is_summary_stored = True
        insight.reset_requested = False
    else:
        insight = _models.MeetingInsights(
            meeting_id=meeting_id,
            summary=summary,
            is_summary_stored=True,
            reset_requested=False
        )
        db.add(insight)

    db.commit()

    return {
        "meeting_id": meeting_id,
        "summary": summary,
        "cached": False
    }

@router.get("/ai/transcript/{meeting_id}")
async def get_transcript(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Check meeting ownership
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 📁 Get transcript path
    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library_entry or not library_entry.transcript_path:
        raise HTTPException(status_code=404, detail="Transcript path not found in MeetingLibrary")

    transcript_path = library_entry.transcript_path
    if not os.path.exists(transcript_path):
        raise HTTPException(status_code=404, detail="Transcript file not found on disk")

       # 📄 Read and format transcript
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            transcript_text = ''.join([line.strip() + '\n' for line in lines])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read transcript: {str(e)}")
    return {
        "meeting_id": meeting_id,
        "transcript": transcript_text
    }





@router.delete("/meeting/reset_ai_response/{meeting_id}")
async def reset_ai_generated_data(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Validate meeting ownership
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise _fastapi.HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 🧠 Fetch or create insight entry
    insight = db.query(_models.MeetingInsights).filter_by(meeting_id=meeting_id).first()
    if not insight:
        insight = _models.MeetingInsights(
            meeting_id=meeting_id,
            summary=None,
            minutes_of_meeting=None,
            sentiments=None,
            is_summary_stored=False,
            is_minutes_stored=False,
            is_sentiment_stored=False,
        )
        db.add(insight)
    else:
        insight.summary = None
        insight.minutes_of_meeting = None
        insight.sentiments = None

        insight.is_summary_stored = False
        insight.is_minutes_stored = False
        insight.is_sentiment_stored = False

    db.commit()

    return {
        "meeting_id": meeting_id,
        "message": "AI-generated content reset. You can now regenerate ai response."

    }






@router.get("/meetings/get_sentiment/{meeting_id}")
async def generate_meeting_sentiment(
    meeting_id: int,
    db: _orm.Session = _fastapi.Depends(get_db),
    user: _schemas.User = _fastapi.Depends(_services.get_current_user)
):
    # 🔐 Verify user and meeting
    meeting = db.query(_models.Meeting).filter_by(id=meeting_id, user_id=user.id).first()
    if not meeting:
        raise _fastapi.HTTPException(status_code=404, detail="Meeting not found or not authorized")

    # 🔍 Get or create insights record
    insight = db.query(_models.MeetingInsights).filter_by(meeting_id=meeting_id).first()

    if insight and insight.is_sentiment_stored and not insight.reset_requested:
        return {
            "meeting_id": meeting_id,
            "sentiments": insight.sentiments,
            "cached": True
        }

    # 📄 Get transcript
    library_entry = db.query(_models.MeetingLibrary).filter_by(meeting_id=meeting_id).first()
    if not library_entry or not library_entry.transcript_path:
        raise _fastapi.HTTPException(status_code=404, detail="Transcript not found")

    transcript_path = library_entry.transcript_path
    if not os.path.exists(transcript_path):
        raise _fastapi.HTTPException(status_code=404, detail="Transcript file missing on disk")

    # 📖 Read transcript
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        raise _fastapi.HTTPException(status_code=500, detail=f"Error reading transcript: {str(e)}")

    # ✨ Perform sentiment analysis
    try:
        
        sentiments = analyze_sentiment(transcript_lines)
    except Exception as e:
        raise _fastapi.HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")

    # 💾 Save or update insights
    if insight:
        insight.sentiments = sentiments
        insight.is_sentiment_stored = True
        insight.reset_requested = False
    else:
        insight = _models.MeetingInsights(
            meeting_id=meeting_id,
            sentiments=sentiments,
            is_sentiment_stored=True
        )
        db.add(insight)

    db.commit()

    return {
        "meeting_id": meeting_id,
        "sentiments": sentiments,
        "cached": False
    }
