from fastapi import APIRouter ,  HTTPException , BackgroundTasks
import fastapi as _fastapi
from fastapi.responses import JSONResponse
import app.local_database.schemas as _schemas
import app.local_database.models as _models
import sqlalchemy.orm as _orm
import app.helpers.auth_services as _services
from app.helpers.auth_services import send_otp
from fastapi.security import OAuth2PasswordBearer
import app.local_database.database as _database
from jwt.exceptions import DecodeError
from app.logger import Logger
import jwt
import os 

# Create an instance of the Logger class
logger_instance = Logger()
# Get a logger for your module
logger = logger_instance.get_logger("Authentication")
router = APIRouter(
    tags=["Authentication"],)


# Retrieve environment variables
JWT_SECRET = os.environ.get("JWT_SECRET")
AUTH_BASE_URL = os.environ.get("AUTH_BASE_URL")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT token validation
async def jwt_validation(token: str = _fastapi.Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except DecodeError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/auth/register" )
async def create_user(
    user: _schemas.UserCreate, 
    db: _orm.Session = _fastapi.Depends(_services.get_db)):
    db_user = await _services.get_user_by_email(email=user.email, db=db)

    if db_user:
        logger.info('User with that email already exists')
        response = {
            "is_verified": False,
            "msg":"User with that email already exists"
        }
        
        raise _fastapi.HTTPException(
            status_code=200,
            detail=response)
    

    user = await _services.create_user(user=user, db=db)
    response = {
            "is_verified": False,
            "msg":"User Registered, Please verify email to activate account !"
        }

    return _fastapi.HTTPException(
            status_code=201,
            detail=response)



# Endpoint to check if the API is live
@router.get("/auth/check_api")
async def check_api():
    return {"status": "Connected to API Successfully"}



@router.post("/auth/token" )
async def generate_token(
    #form_data: _security.OAuth2PasswordRequestForm = _fastapi.Depends(), 
    user_data: _schemas.GenerateUserToken,
    db: _orm.Session = _fastapi.Depends(_services.get_db)):
    user = await _services.authenticate_user(email=user_data.username, password=user_data.password, db=db)

    if user == "is_verified_false":
        logger.info('Email verification is pending. Please verify your email to proceed. ')
        response = {
            "is_verified": False,
            "msg":"Email verification is pending. Please verify your email to proceed."
        }
        raise _fastapi.HTTPException(
            status_code=403, detail=response)

    if not user:
        logger.info('Invalid Credentials')
        raise _fastapi.HTTPException(
            status_code=401, detail="Invalid Credentials")
    
    logger.info('JWT Token Generated')
    response  = {'detail':await _services.create_token(user=user)}
    return  response


@router.get("/auth/users/me", response_model=_schemas.User )
async def get_user(user: _schemas.User = _fastapi.Depends(_services.get_current_user)):
    return user


@router.get("/auth/users/profile")
async def get_user(email: str, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    return db.query(_models.User and _models.Address).filter_by(id=1).first()
  

@router.post("/auth/users/generate_otp", response_model=str)
async def send_otp_mail( background_tasks: BackgroundTasks, userdata: _schemas.GenerateOtp, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    user = await _services.get_user_by_email(email=userdata.email, db=db)

    if not user:
        raise _fastapi.HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        response = {
            "is_verified": True,
            "msg":"User is already verified"
        }
        raise _fastapi.HTTPException(status_code=400, detail=response)

    # Generate and send OTP
    otp = _services.generate_otp()
    background_tasks.add_task(send_otp,userdata.email, otp)

    # Store the OTP in the database
    user.otp = otp
    db.add(user)
    db.commit()
    response = {
            "is_verified": False,
            "msg":"OTP send to email"
        }
    return JSONResponse(content=response, status_code=200)


@router.post("/auth/users/verify_otp")
async def verify_otp(userdata: _schemas.VerifyOtp, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    user = await _services.get_user_by_email(email=userdata.email, db=db )

    if not user:
        raise _fastapi.HTTPException(status_code=404, detail="User not found")

    if not user.otp or user.otp != userdata.otp:
        response = {
            "is_verified": False,
            "msg":"Invalid OTP"
        }
        raise _fastapi.HTTPException(status_code=400, detail=response)

    # Update user's is_verified field
    user.is_verified = True
    user.otp = None  # Clear the OTP
    db.add(user)
    db.commit()
    response = {
            "detail":{
            "is_verified": False,
            "msg":"Account verified !"
            }
        }

    return JSONResponse(content=response, status_code=200)

