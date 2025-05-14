from datetime import datetime
import pydantic 
from typing import List, Optional


class UserBase(pydantic.BaseModel):
    name: str
    email: str
    class Config:
       from_attributes=True

class UserCreate(UserBase):
    password: str
    class Config:
       from_attributes=True

class User(UserBase):
    id: int
    date_created: datetime
    class Config:
       from_attributes=True


class GenerateUserToken(pydantic.BaseModel):
    username: str
    password: str
    class Config:
        from_attributes=True

class GenerateOtp(pydantic.BaseModel):
    email: str
    
class VerifyOtp(pydantic.BaseModel):
    email: str
    otp: int







# -------------------- Meeting --------------------
class MeetingBase(pydantic.BaseModel):
    meeting_name: str
    meeting_date: Optional[datetime] = None

class MeetingCreate(MeetingBase):
    pass

class Meeting(MeetingBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True


# -------------------- MeetingLibrary --------------------
class MeetingLibraryBase(pydantic.BaseModel):
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

class MeetingLibraryResponse(pydantic.BaseModel):
    id: int
    transcript_path: Optional[str]
    audio_path: Optional[str]
    video_path: Optional[str]
    meeting_id: int

    class Config:
        orm_mode = True

# -------------------- MeetingInsights --------------------
class MeetingInsightsBase(pydantic.BaseModel):
    summary: Optional[str] = None
    action_points: Optional[str] = None
    minutes_of_meeting: Optional[str] = None

class MeetingInsightsCreate(MeetingInsightsBase):
    pass

class MeetingInsights(MeetingInsightsBase):
    id: int
    meeting_id: int

    class Config:
        orm_mode = True


# -------------------- AgendaItem --------------------
class AgendaItemBase(pydantic.BaseModel):
    topic: str

class AgendaItemCreate(AgendaItemBase):
    pass

class AgendaItem(AgendaItemBase):
    id: int
    meeting_id: int

    class Config:
        orm_mode = True


# -------------------- Participant --------------------
class ParticipantBase(pydantic.BaseModel):
    name: str
    email: str

class ParticipantCreate(ParticipantBase):
    pass

class Participant(ParticipantBase):
    id: int

    class Config:
        orm_mode = True

# -------------------- SentimentLine --------------------
class SentimentLineBase(pydantic.BaseModel):
    sentence: str
    sentiment: str  # 'Positive', 'Negative', 'Neutral'

class SentimentLineCreate(SentimentLineBase):
    pass

class SentimentLine(SentimentLineBase):
    id: int
    meeting_id: int

    class Config:
        orm_mode = True


# -------------------- Translation --------------------
class TranslationBase(pydantic.BaseModel):
    language: str
    translated_text: str

class TranslationCreate(TranslationBase):
    pass

class Translation(TranslationBase):
    id: int
    meeting_id: int

    class Config:
        orm_mode = True


# -------------------- Meeting Question and Answer  --------------------
class MeetingQandA(pydantic.BaseModel):
    meeting_id: str
    question: str
    class Config:
        orm_mode = True
  
# -------------------- Meeting of Minutes   --------------------
class MeetingMinutes(pydantic.BaseModel):
    meeting_id: str
    language: str
    class Config:
        orm_mode = True
  






class Meeting(MeetingBase):
    id: int
    user_id: int
    library: Optional[MeetingLibrary]
    insights: Optional[MeetingInsights]
    agenda: List[AgendaItem] = []
    participants: List[Participant] = []
    sentiments: List[SentimentLine] = []
    translations: List[Translation] = []

    class Config:
        orm_mode = True