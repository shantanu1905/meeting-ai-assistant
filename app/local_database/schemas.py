from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# -------------------- User --------------------
class UserBase(BaseModel):
    name: str
    email: str

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    date_created: datetime


# -------------------- Auth --------------------
class GenerateUserToken(BaseModel):
    username: str
    password: str

class GenerateOtp(BaseModel):
    email: str

class VerifyOtp(BaseModel):
    email: str
    otp: int


# -------------------- Participant --------------------

class ParticipantCreate(BaseModel):
    name: str
    email: str

class ParticipantResponse(BaseModel):
    id: int
    name: str
    email: str


# -------------------- AgendaItem --------------------
class AgendaItemBase(BaseModel):
    topic: str

class AgendaItemCreate(AgendaItemBase):
    pass

class AgendaItem(AgendaItemBase):
    id: int
    meeting_id: int


# -------------------- MeetingLibrary --------------------
class MeetingLibraryBase(BaseModel):
    transcript_path: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None

class MeetingLibraryCreate(MeetingLibraryBase):
    pass

class MeetingLibrary(MeetingLibraryBase):
    id: int
    meeting_id: int

    class Config:
        orm_mode = True

class MeetingLibraryResponse(BaseModel):
    id: int
    transcript_path: Optional[str]
    audio_path: Optional[str]
    video_path: Optional[str]
    meeting_id: int

    class Config:
        orm_mode = True

# -------------------- MeetingInsights --------------------
class MeetingInsightsBase(BaseModel):
    summary: Optional[str]
    action_points: Optional[str]
    minutes_of_meeting: Optional[str]

class MeetingInsightsCreate(MeetingInsightsBase):
    pass

class MeetingInsights(MeetingInsightsBase):
    id: int
    meeting_id: int


# -------------------- SentimentLine --------------------
class SentimentLineBase(BaseModel):
    sentence: str
    sentiment: str  # 'Positive', 'Negative', 'Neutral'

class SentimentLineCreate(SentimentLineBase):
    pass

class SentimentLine(SentimentLineBase):
    id: int
    meeting_id: int


# -------------------- Translation --------------------
class TranslationBase(BaseModel):
    language: str
    translated_text: str

class TranslationCreate(TranslationBase):
    pass

class Translation(TranslationBase):
    id: int
    meeting_id: int


# -------------------- Meeting --------------------
class MeetingBase(BaseModel):
    meeting_name: str
    meeting_date: datetime
    meeting_description : Optional[str] = None

class MeetingCreate(MeetingBase):
    participants: Optional[List[ParticipantCreate]] = []
   
class MeetingResponse(BaseModel):
    id: int
    user_id: int
    meeting_name: str
    meeting_date: datetime
    meeting_description: str
    participants: List[ParticipantResponse] = []
    library: Optional[MeetingLibrary]

    class Config:
        orm_mode = True


# -------------------- Q&A and Minutes Input --------------------
class MeetingQandA(BaseModel):
    meeting_id: str
    question: str

class MeetingMinutes(BaseModel):
    meeting_id: str
    language: str

# -------------------- Summarize Meeting --------------------

# class MeetingSummary(BaseModel):
#     meeting_id: Optional[List[int]] = []