import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Always resolve to the project root's taskflow.db regardless of where uvicorn is launched from
_HERE = os.path.dirname(os.path.abspath(__file__))          # backend/
_ROOT = os.path.dirname(_HERE)                               # project root
_DB_PATH = os.path.join(_ROOT, "taskflow.db")

SQLITE_DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()