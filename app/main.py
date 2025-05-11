from fastapi import Depends, FastAPI
from app.routers import auth , meeting , user_metadata
from app.local_database.database import Base , engine

app = FastAPI()


Base.metadata.create_all(engine)
app.include_router(auth.router)
app.include_router(meeting.router)
app.include_router(user_metadata.router)


DATAPREP_URL = "http://localhost:6007/v1/dataprep/ingest"
UPLOADS_DIR = "uploaded_files"  # or your file save directory




@app.get("/")
async def root():
    return {"message": "Backend Service for Intel  AI Hackathon"}