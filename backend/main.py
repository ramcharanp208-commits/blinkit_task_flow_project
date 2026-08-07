import time
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from backend.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from backend.ai_parser import parse_quick_add
from backend.database import Base, engine
from backend.dependencies import get_db
from backend.models import User, Project, Task
from backend.algorithms import insertion_sort, binary_search, linear_search
from backend.schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserCreate, UserResponse,
    ProjectCreate, ProjectResponse, ProjectStatResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    QuickAddRequest,
)

# ── Init DB ───────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow API", version="2.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", "http://localhost:5500",
        "http://127.0.0.1:5501", "http://localhost:5501",
        "http://127.0.0.1:8080", "http://localhost:8080",
        "http://127.0.0.1:3000", "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Logging middleware ────────────────────────────────────────────────────────
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = (time.time() - start) * 1000
    logger.info("%s %s  %.2fms  %s", request.method, request.url.path, ms, response.status_code)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT token immediately."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        user_name=user.name,
        email=user.email,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with email + password, receive a JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        user_name=user.name,
        email=user.email,
    )


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(User).all()


# ══════════════════════════════════════════════════════════════════════════════
# PROJECT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(User).filter(User.id == project.owner_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    new_project = Project(title=project.title, owner_id=project.owner_id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@app.get("/projects", response_model=List[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Project).filter(Project.owner_id == current_user.id).all()


@app.get("/projects/stats", response_model=List[ProjectStatResponse])
def get_project_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (
        db.query(
            Project.id.label("project_id"),
            Project.title.label("project_title"),
            func.count(Task.id).label("total_tasks"),
            func.count(case((Task.priority == "low",    1))).label("low_priority_count"),
            func.count(case((Task.priority == "medium", 1))).label("medium_priority_count"),
            func.count(case((Task.priority == "high",   1))).label("high_priority_count"),
            func.count(case((Task.status == "todo",        1))).label("todo_count"),
            func.count(case((Task.status == "in_progress", 1))).label("in_progress_count"),
            func.count(case((Task.status == "done",        1))).label("done_count"),
        )
        .outerjoin(Task, Project.id == Task.project_id)
        .filter(Project.owner_id == current_user.id)
        .group_by(Project.id, Project.title)
        .all()
    )
    return [
        ProjectStatResponse(
            project_id=r.project_id,
            project_title=r.project_title,
            total_tasks=r.total_tasks,
            low_priority_count=r.low_priority_count,
            medium_priority_count=r.medium_priority_count,
            high_priority_count=r.high_priority_count,
            todo_count=r.todo_count,
            in_progress_count=r.in_progress_count,
            done_count=r.done_count,
        )
        for r in results
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TASK ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == task.project_id,
        Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_task = Task(
        title=task.title,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        project_id=task.project_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    sort:       Optional[str] = Query(None, description="'priority' to sort by priority"),
    project_id: Optional[int] = Query(None, description="Filter by project id"),
    priority:   Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    task_status: Optional[str] = Query(None, alias="status", pattern="^(todo|in_progress|done)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List tasks with optional filters (project_id, priority, status) and
    optional insertion_sort by priority.
    """
    query = db.query(Task).join(Project).filter(Project.owner_id == current_user.id)

    if project_id:
        query = query.filter(Task.project_id == project_id)
    if priority:
        query = query.filter(Task.priority == priority)
    if task_status:
        query = query.filter(Task.status == task_status)

    db_tasks = query.all()

    if sort == "priority":
        priority_map = {"low": 1, "medium": 2, "high": 3}
        task_dicts = [
            {
                "id": t.id, "title": t.title, "priority": t.priority,
                "status": t.status, "due_date": t.due_date,
                "project_id": t.project_id,
                "_rank": priority_map.get(str(t.priority), 2),
            }
            for t in db_tasks
        ]
        insertion_sort(task_dicts, key="_rank")
        for d in task_dicts:
            d.pop("_rank", None)
        return task_dicts

    return db_tasks


# /tasks/search MUST come before /tasks/{task_id}
@app.get("/tasks/search", response_model=TaskResponse)
def search_task_by_title(
    title: str = Query(...),
    algo:  str = Query("binary", pattern="^(binary|linear)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_tasks = db.query(Task).join(Project).filter(Project.owner_id == current_user.id).all()
    if not db_tasks:
        raise HTTPException(status_code=404, detail="No tasks found")

    task_index = [
        {"id": t.id, "title": t.title, "priority": t.priority,
         "status": t.status, "due_date": t.due_date, "project_id": t.project_id}
        for t in db_tasks
    ]

    if algo == "binary":
        insertion_sort(task_index, key="title")
        found = binary_search(task_index, target_value=title, key="title")
    else:
        found = linear_search(task_index, target_value=title, key="title")

    if found == -1:
        raise HTTPException(status_code=404, detail=f"Task '{title}' not found")
    return task_index[found]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_by_id(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, Project.owner_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, Project.owner_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def toggle_task_complete(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle task status: todo → in_progress → done → todo (cycle).
    Interview talking point: PATCH semantics for partial update.
    """
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, Project.owner_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cycle = {"todo": "in_progress", "in_progress": "done", "done": "todo"}
    task.status = cycle.get(task.status, "todo")
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id, Project.owner_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# AI QUICK-ADD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def quick_add_task(
    payload: QuickAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == payload.project_id,
        Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Project {payload.project_id} not found",
        )

    parsed = parse_quick_add(payload.description)
    task_in = TaskCreate(
        title=parsed["title"],
        priority=parsed["priority"],
        due_date=parsed["due_date_hint"],
        project_id=payload.project_id,
    )
    new_task = Task(
        title=task_in.title,
        priority=task_in.priority,
        status="todo",
        due_date=task_in.due_date,
        project_id=task_in.project_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
