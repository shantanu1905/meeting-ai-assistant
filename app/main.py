from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ✅ Import CORS
from app.routers import auth, meeting, user_metadata, generative_ai
from app.local_database.database import Base, engine

app = FastAPI()

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(engine)

app.include_router(auth.router)
app.include_router(meeting.router)
app.include_router(user_metadata.router)
app.include_router(generative_ai.router)

DATAPREP_URL = "http://localhost:6007/v1/dataprep/ingest"
UPLOADS_DIR = "uploaded_files"

@app.get("/")
async def root():
    return {"message": "Backend Service for Intel AI Hackathon"}
