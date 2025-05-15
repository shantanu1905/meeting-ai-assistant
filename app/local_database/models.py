import datetime as _dt
import sqlalchemy as _sql
import sqlalchemy.orm as _orm
import passlib.hash as _hash
import app.local_database.database as _database

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
    # sentiments = _orm.relationship("SentimentLine", back_populates="meeting")
    # translations = _orm.relationship("Translation", back_populates="meeting")



# 2. MeetingLibrary Table
class MeetingLibrary(_database.Base):
    __tablename__ = "meeting_library"
    id = _sql.Column(_sql.Integer, primary_key=True)
    transcript_path = _sql.Column(_sql.String)
    audio_path = _sql.Column(_sql.String)
    video_path = _sql.Column(_sql.String)
    meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))

    meeting = _orm.relationship("Meeting", back_populates="library")

# 3. MeetingInsights Table
class MeetingInsights(_database.Base):
    __tablename__ = "meeting_insights"
    id = _sql.Column(_sql.Integer, primary_key=True)
    summary = _sql.Column(_sql.Text)
    action_points = _sql.Column(_sql.Text)
    minutes_of_meeting = _sql.Column(_sql.Text)
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



# # 6. SentimentLine Table
# class SentimentLine(_database.Base):
#     __tablename__ = "sentiment_lines"
#     id = _sql.Column(_sql.Integer, primary_key=True)
#     sentence = _sql.Column(_sql.Text)
#     sentiment = _sql.Column(_sql.String)  # Positive / Negative / Neutral
#     meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))

#     meeting = _orm.relationship("Meeting", back_populates="sentiments")




# # 7. Translation Table
# class Translation(_database.Base):
#     __tablename__ = "translations"
#     id = _sql.Column(_sql.Integer, primary_key=True)
#     language = _sql.Column(_sql.String)
#     translated_text = _sql.Column(_sql.Text)
#     meeting_id = _sql.Column(_sql.Integer, _sql.ForeignKey("meetings.id"))

#     meeting = _orm.relationship("Meeting", back_populates="translations")












# class Product(_database.Base):
#     __tablename__ = "products"

#     id = _sql.Column(_sql.Integer, primary_key=True, index=True)
#     name = _sql.Column(_sql.String, index=True)
#     image_url = _sql.Column(_sql.String, index=True)
#     ean = _sql.Column(_sql.String,index=True )
#     brand = _sql.Column(_sql.String, index=True)
#     category = _sql.Column(_sql.String, index=True)
#     price  = _sql.Column(_sql.Integer,index=True)
#     description = _sql.Column(_sql.String, index=True)
#     owner_id = _sql.Column(_sql.Integer, _sql.ForeignKey("users.id"))



#     owner = _orm.relationship("User", back_populates="products")

