from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─────────────────────────────────────────────
# AUTH SCHEMAS
# ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    password: str = Field(min_length=6, description="Minimum 6 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_name: Optional[str]
    email: str


# ─────────────────────────────────────────────
# USER SCHEMAS
# ─────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
# PROJECT SCHEMAS
# ─────────────────────────────────────────────

class ProjectBase(BaseModel):
    title: str


class ProjectCreate(ProjectBase):
    owner_id: int


class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    model_config = ConfigDict(from_attributes=True)


class ProjectStatResponse(BaseModel):
    project_id: int
    project_title: str
    total_tasks: int
    low_priority_count: int
    medium_priority_count: int
    high_priority_count: int
    todo_count: int
    in_progress_count: int
    done_count: int


# ─────────────────────────────────────────────
# TASK SCHEMAS
# ─────────────────────────────────────────────

class TaskBase(BaseModel):
    title: str
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Priority must be 'low', 'medium', or 'high'",
    )
    status: str = Field(
        default="todo",
        pattern="^(todo|in_progress|done)$",
        description="Status must be 'todo', 'in_progress', or 'done'",
    )
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_and_trim_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Task title cannot be empty or whitespace only.")
        return trimmed


class TaskCreate(TaskBase):
    project_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    status: Optional[str] = Field(default=None, pattern="^(todo|in_progress|done)$")
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_and_trim_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Task title cannot be empty or whitespace only.")
            return trimmed
        return value


class TaskResponse(TaskBase):
    id: int
    project_id: int
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
# AI QUICK-ADD
# ─────────────────────────────────────────────

class QuickAddRequest(BaseModel):
    description: str
    project_id: int
