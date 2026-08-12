from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─────────────────────────────────────────────
# AUTH SCHEMAS
# ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    password: str = Field(min_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_name: Optional[str]
    email: str
    is_admin: int = 0

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(min_length=6)


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
    is_admin: int = 0
    model_config = ConfigDict(from_attributes=True)

class UserAdminUpdate(BaseModel):
    name:     Optional[str] = None
    is_admin: Optional[int] = None


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
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    status:   str = Field(default="todo",   pattern="^(todo|in_progress|done)$")
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty.")
        return v

class TaskCreate(TaskBase):
    project_id: int

class TaskUpdate(BaseModel):
    title:    Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    status:   Optional[str] = Field(default=None, pattern="^(todo|in_progress|done)$")
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty.")
        return v

class TaskResponse(TaskBase):
    id: int
    project_id: int
    model_config = ConfigDict(from_attributes=True)

class PaginatedTaskResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# ─────────────────────────────────────────────
# NOTIFICATION SCHEMAS
# ─────────────────────────────────────────────
class NotificationResponse(BaseModel):
    id: int
    message: str
    type: str
    is_read: int
    created_at: str
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
# AI QUICK-ADD
# ─────────────────────────────────────────────
class QuickAddRequest(BaseModel):
    description: str
    project_id: int


# ─────────────────────────────────────────────
# ADMIN SCHEMAS
# ─────────────────────────────────────────────
class AdminStatsResponse(BaseModel):
    total_users: int
    total_projects: int
    total_tasks: int
    todo_count: int
    in_progress_count: int
    done_count: int
    high_priority_count: int
