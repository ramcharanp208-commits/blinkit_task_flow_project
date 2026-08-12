"""
main.py — TaskFlow API v3
New in v3: Forgot-password/OTP, Admin panel, Notifications, Pagination, Groq AI
"""
import time, logging, random, string
from datetime import datetime, timedelta
from typing import List, Optional
from math import ceil

from fastapi import FastAPI, Depends, HTTPException, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from backend.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.ai_parser import parse_task_description, parse_quick_add
from backend.database import Base, engine
from backend.dependencies import get_db
from backend.models import User, Project, Task, OtpToken, Notification
from backend.algorithms import insertion_sort, binary_search, linear_search
from backend.schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    UserCreate, UserResponse, UserAdminUpdate,
    ProjectCreate, ProjectResponse, ProjectStatResponse,
    TaskCreate, TaskUpdate, TaskResponse, PaginatedTaskResponse,
    NotificationResponse,
    QuickAddRequest,
    AdminStatsResponse,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow API", version="3.0.0",
              description="Blinkit Ops TaskFlow — JWT auth, Admin, Notifications, Groq AI")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", "http://localhost:5500",
        "http://127.0.0.1:5501", "http://localhost:5501",
        "http://127.0.0.1:5502", "http://localhost:5502",
        "http://127.0.0.1:5503", "http://localhost:5503",
        "http://127.0.0.1:8080", "http://localhost:8080",
        "http://127.0.0.1:3000", "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Request logging middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    logger.info("%s %s %.2fms %s", request.method, request.url.path,
                (time.time()-t0)*1000, response.status_code)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _now_str() -> str:
    return datetime.utcnow().isoformat()

def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

def _push_notification(db: Session, user_id: int, message: str, ntype: str = "info"):
    n = Notification(
        user_id=user_id,
        message=message,
        type=ntype,
        is_read=0,
        created_at=_now_str(),
    )
    db.add(n)
    db.commit()

def _require_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=payload.email, name=payload.name,
                hashed_password=hash_password(payload.password), is_admin=0)
    db.add(user); db.commit(); db.refresh(user)
    _push_notification(db, user.id, f"Welcome to TaskFlow, {user.name or user.email}! 🎉", "success")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id,
                         user_name=user.name, email=user.email, is_admin=user.is_admin)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or \
       not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id,
                         user_name=user.name, email=user.email, is_admin=user.is_admin)


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Forgot Password ────────────────────────────────────────────────────────────
@app.post("/auth/forgot-password", status_code=200)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generates a 6-digit OTP valid for 15 min.
    In production, send via email. Here it is printed to the server console
    so you can test without an SMTP server.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return 200 to avoid email enumeration
    if not user:
        return {"message": "If that email exists, an OTP has been sent."}

    # Invalidate old OTPs for this email
    db.query(OtpToken).filter(OtpToken.email == payload.email).delete()
    db.commit()

    otp = _generate_otp()
    expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    db.add(OtpToken(email=payload.email, otp=otp, expires_at=expires, used=0))
    db.commit()

    # Console print — replace with SMTP / SendGrid in production
    print(f"\n{'='*50}")
    print(f"  PASSWORD RESET OTP for {payload.email}")
    print(f"  OTP: {otp}  (valid 15 min)")
    print(f"{'='*50}\n")

    logger.info("OTP generated for %s: %s", payload.email, otp)
    return {"message": "If that email exists, an OTP has been sent."}


@app.post("/auth/reset-password", status_code=200)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify OTP and update password."""
    record = db.query(OtpToken).filter(
        OtpToken.email == payload.email,
        OtpToken.otp   == payload.otp,
        OtpToken.used  == 0,
    ).first()

    if not record:
        raise HTTPException(400, "Invalid or expired OTP")

    if datetime.utcnow() > datetime.fromisoformat(record.expires_at):
        raise HTTPException(400, "OTP has expired. Please request a new one.")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = hash_password(payload.new_password)
    record.used = 1
    db.commit()
    _push_notification(db, user.id, "Your password was reset successfully. 🔐", "success")
    return {"message": "Password reset successful. Please log in."}


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == 0)
    return q.order_by(Notification.id.desc()).limit(50).all()


@app.get("/notifications/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == 0,
    ).count()
    return {"count": count}


@app.patch("/notifications/{notif_id}/read", status_code=200)
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read = 1
    db.commit()
    return {"message": "Marked as read"}


@app.patch("/notifications/read-all", status_code=200)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == 0,
    ).update({"is_read": 1})
    db.commit()
    return {"message": "All notifications marked as read"}


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/admin/stats", response_model=AdminStatsResponse)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    total_users    = db.query(User).count()
    total_projects = db.query(Project).count()
    total_tasks    = db.query(Task).count()
    todo           = db.query(Task).filter(Task.status == "todo").count()
    in_prog        = db.query(Task).filter(Task.status == "in_progress").count()
    done           = db.query(Task).filter(Task.status == "done").count()
    high           = db.query(Task).filter(Task.priority == "high").count()
    return AdminStatsResponse(
        total_users=total_users, total_projects=total_projects,
        total_tasks=total_tasks, todo_count=todo,
        in_progress_count=in_prog, done_count=done,
        high_priority_count=high,
    )


@app.get("/admin/users", response_model=List[UserResponse])
def admin_list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    return db.query(User).all()


@app.patch("/admin/users/{user_id}", response_model=UserResponse)
def admin_update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if payload.name     is not None: user.name     = payload.name
    if payload.is_admin is not None: user.is_admin = payload.is_admin
    db.commit(); db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}", status_code=200)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(400, "Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user); db.commit()
    return {"message": f"User {user_id} deleted"}


@app.get("/admin/tasks", response_model=List[TaskResponse])
def admin_all_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    return db.query(Task).all()


@app.post("/admin/make-admin/{user_id}", status_code=200)
def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_admin = 1
    db.commit()
    _push_notification(db, user.id, "You have been granted Admin access. 🛡️", "success")
    return {"message": f"{user.email} is now an admin"}


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, "Email already registered")
    u = User(email=user.email, name=user.name)
    db.add(u); db.commit(); db.refresh(u)
    return u


@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(User).all()


# ══════════════════════════════════════════════════════════════════════════════
# PROJECTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(User).filter(User.id == project.owner_id).first():
        raise HTTPException(404, "User not found")
    p = Project(title=project.title, owner_id=project.owner_id)
    db.add(p); db.commit(); db.refresh(p)
    _push_notification(db, project.owner_id,
                       f"New project '{project.title}' created.", "info")
    return p


@app.get("/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Project).all()


@app.get("/projects/stats", response_model=List[ProjectStatResponse])
def get_project_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (
        db.query(
            Project.id.label("project_id"),
            Project.title.label("project_title"),
            func.count(Task.id).label("total_tasks"),
            func.count(case((Task.priority == "low",         1))).label("low_priority_count"),
            func.count(case((Task.priority == "medium",      1))).label("medium_priority_count"),
            func.count(case((Task.priority == "high",        1))).label("high_priority_count"),
            func.count(case((Task.status   == "todo",        1))).label("todo_count"),
            func.count(case((Task.status   == "in_progress", 1))).label("in_progress_count"),
            func.count(case((Task.status   == "done",        1))).label("done_count"),
        )
        .outerjoin(Task, Project.id == Task.project_id)
        .group_by(Project.id, Project.title)
        .all()
    )
    return [ProjectStatResponse(**r._asdict()) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# TASKS  (with pagination)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Project).filter(Project.id == task.project_id).first():
        raise HTTPException(404, "Project not found")
    t = Task(title=task.title, priority=task.priority, status=task.status,
             due_date=task.due_date, project_id=task.project_id)
    db.add(t); db.commit(); db.refresh(t)
    _push_notification(db, current_user.id, f"Task '{t.title}' created ✅", "success")
    return t


@app.get("/tasks", response_model=PaginatedTaskResponse)
def get_tasks(
    sort:        Optional[str] = Query(None,  description="'priority'"),
    project_id:  Optional[int] = Query(None),
    priority:    Optional[str] = Query(None,  pattern="^(low|medium|high)$"),
    task_status: Optional[str] = Query(None,  alias="status",
                                       pattern="^(todo|in_progress|done)$"),
    page:        int           = Query(1,     ge=1,  description="Page number"),
    limit:       int           = Query(20,    ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Paginated task list.
    Returns: { tasks, total, page, limit, total_pages }
    """
    q = db.query(Task)
    if project_id:  q = q.filter(Task.project_id == project_id)
    if priority:    q = q.filter(Task.priority    == priority)
    if task_status: q = q.filter(Task.status      == task_status)

    total = q.count()

    db_tasks = q.all()

    # Custom insertion_sort if requested (never SQL ORDER BY)
    if sort == "priority":
        pmap = {"low": 1, "medium": 2, "high": 3}
        dicts = [{"id":t.id,"title":t.title,"priority":t.priority,
                  "status":t.status,"due_date":t.due_date,
                  "project_id":t.project_id,
                  "_r": pmap.get(t.priority, 2)} for t in db_tasks]
        insertion_sort(dicts, key="_r")
        for d in dicts: d.pop("_r")
        # Paginate after sorting
        offset = (page - 1) * limit
        page_data = dicts[offset: offset + limit]
    else:
        offset = (page - 1) * limit
        page_data_orm = db_tasks[offset: offset + limit]
        page_data = [{"id":t.id,"title":t.title,"priority":t.priority,
                      "status":t.status,"due_date":t.due_date,
                      "project_id":t.project_id} for t in page_data_orm]

    return PaginatedTaskResponse(
        tasks=[TaskResponse(**d) for d in page_data],
        total=total,
        page=page,
        limit=limit,
        total_pages=max(1, ceil(total / limit)),
    )


# /tasks/search MUST come before /tasks/{task_id}
@app.get("/tasks/search", response_model=TaskResponse)
def search_task(
    title: str = Query(...),
    algo:  str = Query("binary", pattern="^(binary|linear)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(Task).all()
    if not rows:
        raise HTTPException(404, "No tasks in database")
    idx = [{"id":t.id,"title":t.title,"priority":t.priority,
             "status":t.status,"due_date":t.due_date,"project_id":t.project_id}
           for t in rows]
    if algo == "binary":
        insertion_sort(idx, key="title")
        found = binary_search(idx, title, key="title")
    else:
        found = linear_search(idx, title, key="title")
    if found == -1:
        raise HTTPException(404, f"Task '{title}' not found")
    return idx[found]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db),
             _: User = Depends(get_current_user)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    return t


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int, task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    for k, v in task_update.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit(); db.refresh(t)
    _push_notification(db, current_user.id, f"Task '{t.title}' updated ✏️", "info")
    return t


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def toggle_complete(
    task_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    cycle = {"todo": "in_progress", "in_progress": "done", "done": "todo"}
    t.status = cycle.get(t.status, "todo")
    db.commit(); db.refresh(t)
    if t.status == "done":
        _push_notification(db, current_user.id,
                           f"Task '{t.title}' marked as Done 🎉", "success")
    return t


@app.delete("/tasks/{task_id}", status_code=200)
def delete_task(
    task_id: int, db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    db.delete(t); db.commit()
    return {"message": f"Task {task_id} deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# AI QUICK-ADD  (Groq if GROQ_API_KEY set, else mock)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=201)
def quick_add_task(
    payload: QuickAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Project).filter(Project.id == payload.project_id).first():
        raise HTTPException(422, f"Project {payload.project_id} not found")

    parsed   = parse_task_description(payload.description)
    used_ai  = parsed.pop("used_ai", False)

    task_in  = TaskCreate(
        title=parsed["title"], priority=parsed["priority"],
        due_date=parsed["due_date_hint"], project_id=payload.project_id,
    )
    t = Task(title=task_in.title, priority=task_in.priority, status="todo",
             due_date=task_in.due_date, project_id=task_in.project_id)
    db.add(t); db.commit(); db.refresh(t)

    engine_label = "Groq AI 🤖" if used_ai else "Rule-based AI"
    _push_notification(db, current_user.id,
                       f"{engine_label} created task: '{t.title}'", "success")
    return t
