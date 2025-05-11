from fastapi import Depends, FastAPI
from app.routers import auth , meeting , user_files
from app.local_database.database import Base , engine

app = FastAPI()


Base.metadata.create_all(engine)
app.include_router(auth.router)
app.include_router(meeting.router)
app.include_router(user_files.router)





@app.get("/")
async def root():
    return {"message": "Backend Service for Intel  AI Hackathon"}