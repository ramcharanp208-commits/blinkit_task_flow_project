from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, nullable=False, index=True)
    name            = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_admin        = Column(Integer, nullable=False, default=0)  # 0=user, 1=admin

    projects      = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id       = Column(Integer, primary_key=True, index=True)
    title    = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String, nullable=False)
    priority   = Column(String, nullable=False, default="medium")
    status     = Column(String, nullable=False, default="todo")
    due_date   = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="tasks")

    __table_args__ = (
        CheckConstraint("priority IN ('low','medium','high')", name="check_valid_priority"),
        CheckConstraint("status IN ('todo','in_progress','done')",  name="check_valid_status"),
    )


class OtpToken(Base):
    __tablename__ = "otp_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, nullable=False, index=True)
    otp        = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)   # ISO datetime string
    used       = Column(Integer, nullable=False, default=0)


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    message    = Column(String, nullable=False)
    type       = Column(String, nullable=False, default="info")  # info|success|warning|error
    is_read    = Column(Integer, nullable=False, default=0)
    created_at = Column(String, nullable=False)

    user = relationship("User", back_populates="notifications")
