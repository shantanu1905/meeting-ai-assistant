from fastapi import APIRouter ,  HTTPException 
import fastapi as _fastapi
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import app.helpers.auth_services as _services
import app.local_database.database as _database
from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL
from app.helpers.ai_operations import get_embedding, retrieve_similar_documents, build_qa_prompt , generate_llm_answer
from app.logger import Logger
import sqlalchemy.orm as _orm

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


@router.post("/meeting_qna")
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