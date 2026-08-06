import time
import logging
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from backend.ai_parser import parse_quick_add
from backend.schemas import QuickAddRequest
from backend.database import Base, engine
from backend.dependencies import get_db
from backend.models import User, Project, Task
from backend.algorithms import insertion_sort, binary_search, linear_search
from backend.schemas import (
    UserCreate, UserResponse,
    ProjectCreate, ProjectResponse, ProjectStatResponse,
    TaskCreate, TaskUpdate, TaskResponse,
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow API", version="1.0.0")

# Setup Console Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow_middleware")

# -----------------------------------------------------------------------
# CORS MIDDLEWARE  (Task 8 – explicit origins, never unconditional wildcard)
# Allows both the Python http.server origin AND VS Code Live Server origin.
# allow_credentials must be False when using wildcard; here we name origins
# explicitly so credentials can stay False without ambiguity.
# -----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# -----------------------------------------------------------------------
# CUSTOM LOGGING MIDDLEWARE  (Task 7)
# -----------------------------------------------------------------------
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        "Method: %s  Path: %s  Completed in: %.2fms  Status: %s",
        request.method,
        request.url.path,
        process_time,
        response.status_code,
    )
    return response


# ==========================================
# USER ENDPOINTS
# ==========================================

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


# ==========================================
# PROJECT ENDPOINTS & STATS
# ==========================================

@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == project.owner_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Project owner (User) not found")
    new_project = Project(title=project.title, owner_id=project.owner_id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@app.get("/projects", response_model=List[ProjectResponse], status_code=status.HTTP_200_OK)
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@app.get("/projects/stats", response_model=List[ProjectStatResponse], status_code=status.HTTP_200_OK)
def get_project_stats(db: Session = Depends(get_db)):
    """
    Per-project task statistics computed with SQL COUNT + GROUP BY through
    SQLAlchemy over an OUTER JOIN of projects and tasks (Task 5).
    """
    results = (
        db.query(
            Project.id.label("project_id"),
            Project.title.label("project_title"),
            func.count(Task.id).label("total_tasks"),
            func.count(case((Task.priority == "low", 1))).label("low_priority_count"),
            func.count(case((Task.priority == "medium", 1))).label("medium_priority_count"),
            func.count(case((Task.priority == "high", 1))).label("high_priority_count"),
        )
        .outerjoin(Task, Project.id == Task.project_id)
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
        )
        for r in results
    ]


# ==========================================
# TASK CRUD ENDPOINTS
# ==========================================

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_task = Task(
        title=task.title,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=List[TaskResponse], status_code=status.HTTP_200_OK)
def get_tasks(
    sort: Optional[str] = Query(None, description="Sort field: 'priority'"),
    db: Session = Depends(get_db),
):
    """
    Lists all tasks.  When sort=priority is provided the list is ordered by
    custom insertion_sort (low=1, medium=2, high=3) — never by SQL ORDER BY
    or Python built-in sort.  (Section 2 Task 4)
    """
    db_tasks = db.query(Task).all()

    if sort == "priority":
        priority_map = {"low": 1, "medium": 2, "high": 3}
        task_dicts = [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "due_date": t.due_date,
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


# NOTE: /tasks/search MUST be defined before /tasks/{task_id} so FastAPI
# does not interpret the literal string "search" as an integer task_id.
@app.get("/tasks/search", response_model=TaskResponse, status_code=status.HTTP_200_OK)
def search_task_by_title(
    title: str = Query(..., description="Exact title to match"),
    algo: str = Query("binary", pattern="^(binary|linear)$"),
    db: Session = Depends(get_db),
):
    """
    Builds an in-memory index from real tasks then finds the exact title match
    using binary_search (after insertion_sort) or linear_search.  (Section 2 Task 4)
    """
    db_tasks = db.query(Task).all()
    if not db_tasks:
        raise HTTPException(status_code=404, detail="No tasks in database")

    task_index = [
        {
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "due_date": t.due_date,
            "project_id": t.project_id,
        }
        for t in db_tasks
    ]

    if algo == "binary":
        insertion_sort(task_index, key="title")
        found = binary_search(task_index, target_value=title, key="title")
    else:
        found = linear_search(task_index, target_value=title, key="title")

    if found == -1:
        raise HTTPException(status_code=404, detail=f"Task with title '{title}' not found")

    return task_index[found]


@app.get("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
def get_task_by_id(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted successfully"}


# ==========================================
# AI QUICK-ADD ENDPOINT  (Section 3)
# ==========================================

@app.post("/tasks/quick-add", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def quick_add_task(payload: QuickAddRequest, db: Session = Depends(get_db)):
    """
    Accepts free-text description + project_id.  Uses the deterministic
    rule-based mock parser (Section 3 Task 3) to derive title, priority,
    and due_date, then persists a real row in the tasks table.
    """
    # Validate project exists before doing anything else
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Project with id {payload.project_id} does not exist",
        )

    # Role-based prompt structure (Section 3 Task 2) – kept even for the mock
    _messages = [
        {
            "role": "system",
            "content": (
                "You are an AI task assistant. Extract task 'title', "
                "'priority' ('low'|'medium'|'high'), and 'due_date_hint' "
                "from the user description."
            ),
        },
        {"role": "user", "content": payload.description},
    ]

    # Deterministic mock parser (always active; real LLM path is optional/off)
    parsed = parse_quick_add(payload.description)

    # Validate parsed output via Pydantic before writing to DB
    task_in = TaskCreate(
        title=parsed["title"],
        priority=parsed["priority"],
        due_date=parsed["due_date_hint"],
        project_id=payload.project_id,
    )

    new_task = Task(
        title=task_in.title,
        priority=task_in.priority,
        due_date=task_in.due_date,
        project_id=task_in.project_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
