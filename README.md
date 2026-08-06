# TaskFlow — Blinkit Operations & Engineering Pod

A full-stack task-and-project management platform built for Blinkit's dark-store engineering pods.  
One repository, three graded sections: Core App · Algorithms Engine · AI Quick-Add.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Running the App Locally](#2-running-the-app-locally)
3. [Database Schema](#3-database-schema)
4. [Full Endpoint List](#4-full-endpoint-list)
5. [Section 2 — Algorithms: Complexity & Benchmark](#5-section-2--algorithms-complexity--benchmark)
6. [Section 3 — AI Quick-Add: Prompting Technique & Worked Examples](#6-section-3--ai-quick-add-prompting-technique--worked-examples)
7. [Git Workflow](#7-git-workflow)

---

## 1. Environment Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd blinkit_task_flow_project

# 2. Create and activate a virtual environment
python -m venv backend/venv

# Windows PowerShell
backend\venv\Scripts\Activate.ps1

# macOS / Linux
source backend/venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt
```

---

## 2. Running the App Locally

### Two-process run (recommended)

**Terminal 1 — start the backend:**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — serve the frontend:**

```bash
python -m http.server 5500 --directory frontend
```

Open your browser at **http://127.0.0.1:5500**

The frontend's `fetch()` calls target `http://127.0.0.1:8000`.  
The CORS middleware in `backend/main.py` explicitly allows `http://127.0.0.1:5500`.

### Utility scripts

```bash
# Seed the database and run the benchmark (Section 2)
python seed.py

# Run the algorithm checks script (Section 2)
python check_algorithms.py
```

> **Interactive API docs** are available at http://127.0.0.1:8000/docs once the backend is running.

---

## 3. Database Schema

Three tables with explicit primary keys, foreign keys, NOT NULL and UNIQUE constraints.

### `users`

| Column | Type    | Constraints              |
|--------|---------|--------------------------|
| id     | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| email  | TEXT    | NOT NULL, UNIQUE          |
| name   | TEXT    | nullable                  |

### `projects`

| Column   | Type    | Constraints                        |
|----------|---------|------------------------------------|
| id       | INTEGER | PRIMARY KEY, AUTOINCREMENT         |
| title    | TEXT    | NOT NULL                           |
| owner_id | INTEGER | NOT NULL, FK → users.id            |

### `tasks`

| Column     | Type    | Constraints                                              |
|------------|---------|----------------------------------------------------------|
| id         | INTEGER | PRIMARY KEY, AUTOINCREMENT                               |
| title      | TEXT    | NOT NULL                                                 |
| priority   | TEXT    | NOT NULL, CHECK IN ('low', 'medium', 'high')             |
| due_date   | TEXT    | nullable (stores exact dates or phrases like "next friday") |
| project_id | INTEGER | NOT NULL, FK → projects.id                               |

SQLAlchemy relationships:
- `User.projects` ↔ `Project.owner` (`back_populates` on both sides)
- `Project.tasks` ↔ `Task.project` (`back_populates` on both sides)

---

## 4. Full Endpoint List

### Users

#### POST /users — create a user

Request body:
```json
{ "email": "alice@blinkit.com", "name": "Alice" }
```
Success response `201`:
```json
{ "id": 1, "email": "alice@blinkit.com", "name": "Alice" }
```
Failure `422` — duplicate email or missing required field.

#### GET /users — list all users

Response `200`:
```json
[
  { "id": 1, "email": "alice@blinkit.com", "name": "Alice" }
]
```

---

### Projects

#### POST /projects — create a project

Request body:
```json
{ "title": "Dark Store Pod B", "owner_id": 1 }
```
Success response `201`:
```json
{ "id": 1, "title": "Dark Store Pod B", "owner_id": 1 }
```
Failure `404` — `owner_id` does not reference an existing user.

#### GET /projects — list all projects

Response `200`:
```json
[
  { "id": 1, "title": "Dark Store Pod B", "owner_id": 1 }
]
```

#### GET /projects/stats — per-project task statistics

Aggregation runs entirely in SQL (COUNT + GROUP BY over an OUTER JOIN).

Response `200`:
```json
[
  {
    "project_id": 1,
    "project_title": "Dark Store Pod B",
    "total_tasks": 5,
    "low_priority_count": 1,
    "medium_priority_count": 3,
    "high_priority_count": 1
  }
]
```

---

### Tasks

#### POST /tasks — create a task

Request body:
```json
{
  "title": "Verify shelf inventory for Pod B",
  "priority": "high",
  "due_date": "2026-08-20",
  "project_id": 1
}
```
Success response `201`:
```json
{
  "id": 1,
  "title": "Verify shelf inventory for Pod B",
  "priority": "high",
  "due_date": "2026-08-20",
  "project_id": 1
}
```
Failure `404` — project not found.  
Failure `422` — blank title, invalid priority value, or missing required field.

#### GET /tasks — list all tasks

Response `200`: array of task objects (same shape as above).

#### GET /tasks?sort=priority — sorted task list (Section 2)

Fetches rows from DB, maps `low=1 / medium=2 / high=3`, then calls
`insertion_sort()` on the list — **never** SQL `ORDER BY` or Python's
built-in sort.

Response `200`: tasks ordered low → medium → high.

#### GET /tasks/{task_id} — get task by id

Response `200`: single task object.  
Failure `404` — task not found.

#### PUT /tasks/{task_id} — update a task

Request body (all fields optional):
```json
{ "title": "Updated title", "priority": "low", "due_date": "2026-09-01" }
```
Response `200`: updated task object.  
Failure `404` — task not found.

#### DELETE /tasks/{task_id} — delete a task

Response `200`:
```json
{ "message": "Task 1 deleted successfully" }
```
Failure `404` — task not found.

#### GET /tasks/search?title=...&algo=binary|linear — search by exact title (Section 2)

Builds an in-memory index from real DB rows, then uses `binary_search`
(after `insertion_sort` by title) or `linear_search` depending on `algo`.

Example:
```
GET /tasks/search?title=Verify shelf inventory for Pod B&algo=binary
```
Response `200`: matching task object.  
Failure `404` — no task with that exact title.

---

### AI Quick-Add

#### POST /tasks/quick-add — create task from free text (Section 3)

Request body:
```json
{
  "description": "Finish the ops report urgently, due next friday",
  "project_id": 1
}
```
Success response `201`:
```json
{
  "id": 7,
  "title": "Finish the ops report , due",
  "priority": "high",
  "due_date": "next friday",
  "project_id": 1
}
```
Failure `422` — `project_id` does not exist, or malformed body.  
Failure `422` — missing or empty `description`.

---

## 5. Section 2 — Algorithms: Complexity & Benchmark

### Function signatures

```python
insertion_sort(records: list[dict], key: str) -> None
binary_search(sorted_records: list[dict], target_value, key: str) -> int   # -1 if absent
linear_search(records: list[dict], target_value, key: str) -> int          # -1 if absent

insertion_sort_count(records, key) -> int
binary_search_count(sorted_records, target_value, key) -> {"index": int, "comparison_count": int}
linear_search_count(records, target_value, key)        -> {"index": int, "comparison_count": int}
```

### Time complexity

| Algorithm      | Best case | Worst case |
|----------------|-----------|------------|
| insertion_sort | O(n)      | O(n²)      |
| binary_search  | O(1)      | O(log n)   |
| linear_search  | O(1)      | O(n)       |

### Benchmark results

Run `python seed.py` to reproduce these numbers.  
Target: middle-of-list title match. Absent-value linear scan shown separately.

| n    | insertion_sort comparisons | binary_search comparisons | linear_search comparisons (mid hit) | linear_search comparisons (absent) |
|------|---------------------------|--------------------------|-------------------------------------|------------------------------------|
| 10   | ~25                       | 3–4                      | ~5                                  | 10                                 |
| 500  | ~62,000                   | 9                        | ~250                                | 500                                |
| 3000 | ~2,250,000                | 12                       | ~1,500                              | 3000                               |

*(Exact numbers vary with random priority/due_date data; run `seed.py` for your exact counts.)*

### Sort-first justification

**insertion_sort** costs O(n²) comparisons — roughly 2.25 million for 3,000 tasks.  
**binary_search** after sorting costs only O(log n) — just 12 comparisons at n=3,000.  
**linear_search** without sorting costs O(n) — up to 3,000 comparisons for a miss.

For TaskFlow's usage pattern, teams **list and sort tasks many times per day** but add
or rename tasks far less often. Once the list is sorted (paying the O(n²) cost once),
every subsequent binary search is O(log n). At n=3,000, that means 12 comparisons
instead of up to 3,000. The sort-first investment pays for itself after just a handful
of searches. At the sizes TaskFlow operates (hundreds to low thousands), insertion sort
is fast enough in wall-clock time (milliseconds), and the log-n search speedup is
immediately worthwhile. Linear search remains useful only when the list cannot be kept
sorted — for example, immediately after a new task is appended and before the next sort.

### Check script

```bash
python check_algorithms.py
```

Expected output — all lines should be PASS:

```
--- Running TaskFlow Automated Algorithm Checks ---
PASS: insertion_sort on empty list
PASS: insertion_sort on single-element list
PASS: binary_search boundary matches (first, mid, last)
PASS: binary_search absent target returns -1
PASS: insertion_sort_count returns int > 0 and sorts list in-place
PASS: binary_search_count structure and index match
PASS: linear_search_count absent target scans full length
```

---

## 6. Section 3 — AI Quick-Add: Prompting Technique & Worked Examples

### Prompting technique rationale (≤ 300 words)

The system message and mock parser logic are modelled on the **zero-shot** prompting
technique. A single, precisely-worded system-role instruction tells the model exactly
what fields to extract (`title`, `priority`, `due_date_hint`) and what the closed value
sets are (`low | medium | high`), without providing any labelled input-output examples
inside the prompt itself.

Zero-shot was chosen for three reasons. First, **token efficiency**: few-shot prompts
carry several example pairs on every call, which adds cost proportional to the number
of examples multiplied by every request. For a high-frequency internal tool like
TaskFlow, zero-shot keeps the prompt short and the per-request token bill low. Second,
**response reliability for a closed schema**: because the output format is narrow and
deterministic (three fields, fixed vocabulary), a well-specified zero-shot instruction
is sufficient — the model does not need worked examples to generalise. Chain-of-thought
would add reasoning tokens that are unnecessary when the extraction rules are already
unambiguous. Third, **symmetry with the mock**: the deterministic rule-based parser
in `ai_parser.py` follows exactly the same decision logic the system message describes,
so the code and the prompt stay in sync without maintaining a library of few-shot
examples that could drift out of date as the priority rules change.

### Five worked examples

Apply the Task 3 algorithm to each description and verify the output matches.

**Example 1**
Input: `"Fix the cold-chain log asap"`
Expected:
```json
{ "title": "Fix the cold-chain log ", "priority": "high", "due_date_hint": null }
```
Reason: `"asap"` → group (i) → `priority="high"`; `"asap"` stripped from title; no date keyword.

---

**Example 2**
Input: `"Review vendor invoices whenever, low priority"`
Expected:
```json
{ "title": "Review vendor invoices , ", "priority": "low", "due_date_hint": null }
```
Reason: `"whenever"` → group (ii) → `priority="low"`; both `"whenever"` and `"low priority"` stripped (title-stripping note); no date keyword.

---

**Example 3**
Input: `"Deploy the API gateway next monday"`
Expected:
```json
{ "title": "Deploy the API gateway ", "priority": "medium", "due_date_hint": "next monday" }
```
Reason: no priority keyword → default `"medium"`; `"next monday"` matched as whole two-word phrase (step c-4) and stripped.

---

**Example 4**
Input: `"Check tomorrow's delivery manifest tomorrow"`
Expected:
```json
{ "title": "Check 's delivery manifest ", "priority": "medium", "due_date_hint": "tomorrow" }
```
Reason: no priority keyword → `"medium"`; `"tomorrow"` matched first (step c-2); every occurrence of `"tomorrow"` stripped from title.

---

**Example 5**
Input: `"   "` (whitespace only)
Expected:
```json
{ "title": "Untitled task", "priority": "medium", "due_date_hint": null }
```
Reason: input is whitespace-only → early return path; title falls back to placeholder `"Untitled task"`.

---

## 7. Git Workflow

The repository's commit history includes at least one feature branch created,
committed to at least twice, and merged back into `main`.

To verify:

```bash
git log --graph --all --oneline
```

You should see a branch diverging from `main` (e.g. `feature/algorithms-engine` or
`feature/ai-quick-add`) with multiple commits, then a merge commit back into `main`.
