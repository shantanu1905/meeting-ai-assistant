import jwt
from fastapi import APIRouter
import sqlalchemy.orm as _orm
import passlib.hash as _hash
import email_validator as _email_check
import fastapi as _fastapi
import fastapi.security as _security
import app.local_database.database as _database
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import app.helpers.email_notification as email_notification
import random
import os
from app.logger import Logger

# Load environment variables
JWT_SECRET = os.getenv("JWT_SECRET")
oauth2schema = _security.OAuth2PasswordBearer("/api/token")


# Create an instance of the Logger class
logger_instance = Logger()
# Get a logger for your module
logger = logger_instance.get_logger("ondc api")
router = APIRouter(
    tags=["ondc"],)



def create_database():
    # Create database tables
    return _database.Base.metadata.create_all(bind=_database.engine)

def get_db():
    # Dependency to get a database session
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user_by_email(email: str, db: _orm.Session):
     # Retrieve a user by email from the database
    return db.query(_models.User).filter(_models.User.email == email and _models.User.is_verified==True).first()

async def create_user(user: _schemas.UserCreate, db: _orm.Session):
    # Create a new user in the database
    try:
        valid = _email_check.validate_email(user.email)
        name = user.name
        email = valid.email
    except _email_check.EmailNotValidError:
        raise _fastapi.HTTPException(status_code=404, detail="Please enter a valid email")

    user_obj = _models.User(email=email, name=name, hashed_password=_hash.bcrypt.hash(user.password))
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

async def authenticate_user(email: str, password: str, db: _orm.Session):
    # Authenticate a user
    user = await get_user_by_email(email=email, db=db)

    if not user:
        return False
    
    if not user.is_verified:
        return 'is_verified_false'
    
    if not user.verify_password(password):
        return False

    return user

async def create_token(user: _models.User):
    # Create a JWT token for authentication
    user_obj = _schemas.User.from_orm(user)
    user_dict = user_obj.model_dump()
    del user_dict["date_created"]
    token = jwt.encode(user_dict, JWT_SECRET, algorithm="HS256")
    return dict(access_token=token, token_type="bearer" ,  is_verified=True , success=True , username=user_dict['email'] , name=user_dict['name'] , id =user_dict['id'] )

async def get_current_user(db: _orm.Session = _fastapi.Depends(get_db), token: str = _fastapi.Depends(oauth2schema)):
    # Get the current authenticated user from the JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = db.query(_models.User).get(payload["id"])
    except:
        raise _fastapi.HTTPException(status_code=401, detail="Invalid Email or Password")
    return _schemas.User.from_orm(user)

def generate_otp():
    # Generate a random OTP
    return str(random.randint(100000, 999999))

def send_otp(email, otp):
    # Send an OTP email notification using RabbitMQ
    try:
        message = {'email': email,
                'subject': 'Account Verification OTP Notification',
                'other': 'null',
                'body': f'Your OTP for account verification is: {otp} \n Please enter this OTP on the verification page to complete your account setup. \n If you did not request this OTP, please ignore this message.\n Thank you '
                    }
        otp_auth =email_notification.notification(message)
        if otp_auth :
            logger.info(f"OTP send to {email}")
    except Exception as err:
        print(f"Failed to publish message: {err}")
   