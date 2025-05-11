import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.logger import Logger

log = Logger()
logger = log.get_logger(__name__)
load_dotenv()

# # Define path to SQLite database file
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "sqlite_db.sqlite3")

# # SQLite connection string
# DATABASE_URL = f"sqlite:///{DB_PATH}"





"""Create a connection to the backend default database """
DATABASE_URL = (
    "postgresql://{username}:{password}@{host}:{port}/{database_name}".format(
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database_name=os.getenv("POSTGRES_DB"),
    )
)


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    return db
