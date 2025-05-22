import datetime as _dt
import sqlalchemy as _sql
import sqlalchemy.orm as _orm
import passlib.hash as _hash
import app.local_database.database as _database
from sqlalchemy.dialects.postgresql import JSON

_database.Base.metadata.create_all(_database.engine)

class User(_database.Base):
    __tablename__ = "users"
    id = _sql.Column(_sql.Integer, primary_key=True, index=True)
    name = _sql.Column(_sql.String)
    email = _sql.Column(_sql.String, unique=True, index=True)
    is_verified = _sql.Column(_sql.Boolean , default=False)
    otp = _sql.Column(_sql.Integer)
    hashed_password = _sql.Column(_sql.String)
    date_created = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)
    
    meetings = _orm.relationship("Meeting", back_populates="user")

    def verify_password(self, password: str):
        return _hash.bcrypt.verify(password, self.hashed_password)



# 1. Meeting Table
class Meeting(_database.Base):
    __tablename__ = "meetings"
    id = _sql.Column(_sql.Integer, primary_key=True, index=True)
    meeting_name = _sql.Column(_sql.String, nullable=False)
    meeting_description = _sql.Column(_sql.Text  , nullable=False)
    meeting_date = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)
    user_id = _sql.Column(_sql.Integer, _sql.ForeignKey("users.id"))

    user = _orm.relationship("User", back_populates="meetings")
    library = _orm.relationship("MeetingLibrary", back_populates="meeting", uselist=False)
    insights = _orm.relationship("MeetingInsights", back_populates="meeting", uselist=False)
    participants = _orm.relationship("Participant", back_populates="meeting")
    chat_messages = _orm.relationship("ChatMessage", back_populates="meeting", cascade="all, delete-orphan")
 

# 2. MeetingLibrary Table
class MeetingLibrary(_database.Base):
    __tablename__ = "meeting_library"
    id = _sql.Column(_sql.Integer, primary_key=True)
    transcript_path = _sql.Column(_sql.String)
    audio_path = _sql.Column(_sql.String)
    video_path = _sql.Column(_sql.String)
    meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))

    meeting = _orm.relationship("Meeting", back_populates="library")

class MeetingInsights(_database.Base):
    __tablename__ = "meeting_insights"
    id = _sql.Column(_sql.Integer, primary_key=True)
    # JSON fields for AI-generated content
    summary = _sql.Column(JSON, nullable=True)
    minutes_of_meeting = _sql.Column(JSON, nullable=True)
    sentiments = _sql.Column(JSON, nullable=True)

    # Individual flags for content presence
    is_summary_stored = _sql.Column(_sql.Boolean, default=False)
    is_minutes_stored = _sql.Column(_sql.Boolean, default=False)
    is_sentiment_stored = _sql.Column(_sql.Boolean, default=False)
    reset_requested = _sql.Column(_sql.Boolean, default=False)       # 🔄 Lets user trigger re-generation
    meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))
    meeting = _orm.relationship("Meeting", back_populates="insights")

# 5. Participant Table
class Participant(_database.Base):
    __tablename__ = "participants"
    id = _sql.Column(_sql.Integer, primary_key=True)
    name = _sql.Column(_sql.String)
    email = _sql.Column(_sql.String)
    meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))

    meeting = _orm.relationship("Meeting", back_populates="participants")

class ChatMessage(_database.Base):
    __tablename__ = "chat_messages"

    id = _sql.Column(_sql.Integer, primary_key=True, index=True)
    meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"), nullable=False)
    message = _sql.Column(_sql.Text, nullable=False)
    sender_type = _sql.Column(_sql.String(50), default="text")  # e.g. Bot, User
    timestamp = _sql.Column(_sql.DateTime, default=_sql.func.now())

    # Relationships (optional)
    meeting = _orm.relationship("Meeting", back_populates="chat_messages")
    