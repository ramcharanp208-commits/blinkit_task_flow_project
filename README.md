# ⚡ TaskFlow — Blinkit Operations & Engineering

A full-stack task-and-project management platform for Blinkit's dark-store engineering pods.

**Stack:** FastAPI · SQLAlchemy · SQLite · Vanilla JS · CSS Variables (dark/light) · JWT · Groq AI

---

## Features

| Category | Feature |
|----------|---------|
| Auth | Register, Login, JWT tokens, Forgot Password (OTP), Reset Password |
| Admin | Admin panel — user list, promote/delete users, system-wide stats |
| Tasks | Create, Read, Update, Delete, Status toggle (todo→in_progress→done) |
| AI | AI Quick-Add — Groq LLM (llama3-8b) if `GROQ_API_KEY` set, mock parser fallback |
| Search | Binary Search + Linear Search on task title (custom algorithms) |
| Sort | Insertion Sort by priority (custom algorithm, never SQL ORDER BY) |
| Filter | Filter by project, priority, status |
| Pagination | Server-side pagination with page/limit controls |
| Notifications | Real-time notification bell — mark read, mark all read |
| UI | Dark/Light mode, responsive (768px + 480px breakpoints), sticky navbar |

---

## Setup

```bash
# 1. Clone
git clone <your-repo-url>
cd blinkit_task_flow_project

# 2. Virtual environment
python -m venv backend/venv

# Windows
backend\venv\Scripts\activate

# macOS/Linux
source backend/venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Run DB migrations
python migrate.py
```

### Groq AI (optional)

Set your Groq API key before starting the server:

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_your_key_here"

# macOS/Linux
export GROQ_API_KEY=gsk_your_key_here
```

When the key is set, AI Quick-Add uses `llama3-8b-8192` via Groq.
Without the key, it falls back to the deterministic mock parser automatically.

---

## Running the App

**Terminal 1 — Backend (port 8000):**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend (port 5500):**

```bash
python -m http.server 5500 --directory frontend
```

Open **http://127.0.0.1:5500** in your browser.

Interactive API docs: **http://127.0.0.1:8000/docs**

### Making yourself an Admin

After registering, run this once in Python:

```python
# make_admin.py
from backend.database import SessionLocal
from backend.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == "your@email.com").first()
user.is_admin = 1
db.commit(); db.close()
print("Done")
```

```bash
python make_admin.py
```

---

## Full Endpoint List

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register + get JWT |
| POST | `/auth/login` | Login + get JWT |
| GET  | `/auth/me` | Current user profile |
| POST | `/auth/forgot-password` | Send OTP to console/email |
| POST | `/auth/reset-password` | Verify OTP + set new password |

**Register:**
```json
POST /auth/register
Body: { "email": "alice@blinkit.com", "name": "Alice", "password": "pass123" }
Response 201: { "access_token": "eyJ...", "user_id": 1, "user_name": "Alice", "email": "...", "is_admin": 0 }
```

**Forgot Password:**
```json
POST /auth/forgot-password
Body: { "email": "alice@blinkit.com" }
Response 200: { "message": "If that email exists, an OTP has been sent." }
// OTP printed to server console — check terminal
```

**Reset Password:**
```json
POST /auth/reset-password
Body: { "email": "alice@blinkit.com", "otp": "123456", "new_password": "newpass123" }
Response 200: { "message": "Password reset successful. Please log in." }
```

---

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications` | List notifications (newest first) |
| GET | `/notifications/unread-count` | Count of unread |
| PATCH | `/notifications/{id}/read` | Mark one as read |
| PATCH | `/notifications/read-all` | Mark all as read |

```json
GET /notifications
Response 200: [{ "id": 1, "message": "Welcome! 🎉", "type": "success", "is_read": 0, "created_at": "2026-08-12T..." }]

GET /notifications/unread-count
Response 200: { "count": 3 }
```

---

### Tasks (Paginated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tasks` | Create task |
| GET | `/tasks?page=1&limit=10` | Paginated task list |
| GET | `/tasks?sort=priority` | Insertion-sorted by priority |
| GET | `/tasks?status=todo&priority=high` | Filtered list |
| GET | `/tasks/search?title=...&algo=binary` | Binary or linear search |
| GET | `/tasks/{id}` | Get by ID |
| PUT | `/tasks/{id}` | Update task |
| PATCH | `/tasks/{id}/complete` | Cycle status todo→in_progress→done |
| DELETE | `/tasks/{id}` | Delete task |
| POST | `/tasks/quick-add` | AI Quick-Add |

**Create task:**
```json
POST /tasks
Body: { "title": "Review shelf inventory", "priority": "high", "due_date": "2026-08-20", "project_id": 1 }
Response 201: { "id": 1, "title": "Review shelf inventory", "priority": "high", "status": "todo", "due_date": "2026-08-20", "project_id": 1 }
```

**Paginated list:**
```json
GET /tasks?page=1&limit=10
Response 200: {
  "tasks": [...],
  "total": 45,
  "page": 1,
  "limit": 10,
  "total_pages": 5
}
```

**AI Quick-Add:**
```json
POST /tasks/quick-add
Body: { "description": "Fix cold-chain log urgently next friday", "project_id": 1 }
Response 201: { "id": 7, "title": "Fix cold-chain log", "priority": "high", "due_date": "next friday", ... }
```

---

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create project |
| GET | `/projects` | List all projects |
| GET | `/projects/stats` | Per-project task counts by priority & status |

---

### Admin (requires is_admin=1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/stats` | System-wide stats |
| GET | `/admin/users` | All users |
| PATCH | `/admin/users/{id}` | Update user name/admin flag |
| DELETE | `/admin/users/{id}` | Delete user |
| GET | `/admin/tasks` | All tasks across all users |
| POST | `/admin/make-admin/{id}` | Promote user to admin |

```json
GET /admin/stats
Response 200: {
  "total_users": 4, "total_projects": 2, "total_tasks": 12,
  "todo_count": 5, "in_progress_count": 4, "done_count": 3, "high_priority_count": 3
}
```

---

## Section 2 — Algorithms

### Time Complexity

| Algorithm | Best case | Worst case |
|-----------|-----------|------------|
| insertion_sort | O(n) | O(n²) |
| binary_search  | O(1) | O(log n) |
| linear_search  | O(1) | O(n) |

### Benchmark Results (synthetic data, random.seed=42)

Run: `python seed.py`

| n | insertion_sort | binary_search | linear_search (hit) | linear_search (miss) |
|---|---------------|--------------|---------------------|----------------------|
| 10 | 29 | 3 | 8 | 10 |
| 500 | 61,931 | 8 | 117 | 500 |
| 3000 | 2,234,525 | 11 | 1,017 | 3,000 |

**Justification:** At n=3000 insertion_sort costs 2.2M comparisons (paid once), then every binary_search costs only 11. For teams that search/sort repeatedly but add tasks rarely, the sort-first strategy gives O(log n) repeated lookups vs O(n) linear scans.

Run checks: `python check_algorithms.py` — all 7 cases should print PASS.

---

## Section 3 — AI Quick-Add

### Prompting Technique: Zero-Shot

The system message describes the extraction task with exact output format and closed value sets. No examples are included in the prompt. This keeps each request short (low token usage) while the deterministic schema (3 fields, fixed vocabulary) makes zero-shot reliable enough without few-shot examples.

When `GROQ_API_KEY` is set, `llama3-8b-8192` is called with temperature=0.1. On any failure the mock parser runs automatically — no downtime, no extra cost.

### Five Worked Examples (mock parser)

| Input | title | priority | due_date_hint |
|-------|-------|----------|---------------|
| `"Fix the cold-chain log asap"` | `"Fix the cold-chain log"` | high | null |
| `"Review vendor invoices whenever, low priority"` | `"Review vendor invoices ,"` | low | null |
| `"Deploy the API gateway next monday"` | `"Deploy the API gateway"` | medium | next monday |
| `"Check tomorrow delivery manifest tomorrow"` | `"Check  delivery manifest"` | medium | tomorrow |
| `"   "` (whitespace only) | `"Untitled task"` | medium | null |

---

## Git Workflow

```bash
git log --graph --oneline --all
```

Repository has feature branch `feature/complete-taskflow` merged into `main` with multiple commits — satisfies the assignment Git workflow requirement.

---

## Project Structure

```
blinkit_task_flow_project/
├── backend/
│   ├── main.py          # FastAPI app — all endpoints
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic schemas
│   ├── auth.py          # JWT helpers, password hashing
│   ├── ai_parser.py     # Groq + mock parser
│   ├── algorithms.py    # insertion_sort, binary_search, linear_search
│   ├── database.py      # DB engine (absolute path)
│   ├── dependencies.py  # get_db dependency
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Full SPA — auth, dashboard, admin
│   ├── app.js           # All JS logic
│   └── styles.css       # Dark/light CSS variables
├── migrate.py           # DB migration script
├── seed.py              # Benchmark seeder
├── check_algorithms.py  # Algorithm PASS/FAIL tests
├── taskflow.db          # SQLite database (git-ignored)
└── README.md
```
