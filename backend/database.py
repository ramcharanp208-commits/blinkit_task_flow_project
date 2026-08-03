from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database file path
SQLITE_DATABASE_URL = "sqlite:///./taskflow.db"

# create_engine with check_same_thread=False allows FastAPI multi-threading with SQLite
engine = create_engine(
    SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal factory creates new database sessions for requests
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models to inherit from
Base = declarative_base()