"""
seed.py — TaskFlow Section 2 benchmark seeder
==============================================
Seeds the database with realistic task data at three sizes (10, 500, 3000 rows),
then runs the comparison-counting benchmark wrappers and prints the results.

Usage (from project root, with venv active):
    python seed.py

The script is safe to re-run: it creates one seed user + one seed project if
they don't already exist, then appends tasks up to each target size.
"""

import sys
import os
import random
import copy

# Make sure the project root is on sys.path so `backend.*` imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, engine, Base
from backend.models import User, Project, Task
from backend.algorithms import (
    insertion_sort_count,
    binary_search_count,
    linear_search_count,
)

# ---------------------------------------------------------------------------
# Realistic synthetic data pools
# ---------------------------------------------------------------------------
TITLE_PREFIXES = [
    "Review", "Update", "Fix", "Deploy", "Audit", "Test", "Document",
    "Refactor", "Monitor", "Schedule", "Verify", "Approve", "Escalate",
    "Coordinate", "Sync", "Analyse", "Migrate", "Configure", "Archive",
    "Optimise",
]
TITLE_SUBJECTS = [
    "shelf inventory", "cold-chain log", "delivery manifest", "picker assignment",
    "QC report", "fleet tracker", "store dashboard", "ops runbook", "SKU mapping",
    "vendor invoice", "route plan", "dark-store layout", "stock alert",
    "return request", "SLA breach ticket", "onboarding checklist", "API gateway",
    "CI pipeline", "DB migration script", "customer feedback form",
]
PRIORITIES = ["low", "medium", "high"]
DUE_DATES = [
    "2026-08-10", "2026-08-15", "2026-08-20", "2026-08-25",
    "2026-09-01", "next friday", "next monday", "tomorrow", "today", None,
]


def make_title(index: int) -> str:
    prefix = TITLE_PREFIXES[index % len(TITLE_PREFIXES)]
    subject = TITLE_SUBJECTS[index % len(TITLE_SUBJECTS)]
    return f"{prefix} {subject} #{index + 1}"


def seed_to_size(db, project_id: int, target: int):
    """Insert tasks until at least `target` rows exist for this project."""
    current = db.query(Task).filter(Task.project_id == project_id).count()
    if current >= target:
        print(f"  Already have {current} tasks — skipping insert to {target}.")
        return
    to_add = target - current
    print(f"  Inserting {to_add} tasks (current={current}, target={target}) …", end=" ")
    batch = []
    for i in range(to_add):
        batch.append(Task(
            title=make_title(current + i),
            priority=random.choice(PRIORITIES),
            due_date=random.choice(DUE_DATES),
            project_id=project_id,
        ))
        if len(batch) == 500:
            db.bulk_save_objects(batch)
            db.commit()
            batch = []
    if batch:
        db.bulk_save_objects(batch)
        db.commit()
    print("done.")


def build_task_dicts(db, project_id: int):
    """Fetch all tasks for a project as plain dicts (same shape as endpoints use)."""
    rows = db.query(Task).filter(Task.project_id == project_id).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "due_date": t.due_date,
            "project_id": t.project_id,
        }
        for t in rows
    ]


def run_benchmark(label: str, records: list):
    """
    Run all three counting wrappers against a copy of `records` and print results.
    Uses copies so the original list order is preserved between runs.
    """
    print(f"\n  [{label}]  n = {len(records)}")

    # --- insertion_sort_count ---
    sort_copy = copy.deepcopy(records)
    sort_comps = insertion_sort_count(sort_copy, key="title")
    print(f"    insertion_sort_count   comparisons = {sort_comps:,}")

    # After sorting by title, pick a target from middle for binary search
    mid_idx = len(sort_copy) // 2
    target_title = sort_copy[mid_idx]["title"]

    # --- binary_search_count (list is already sorted by title from above) ---
    bs_result = binary_search_count(sort_copy, target_value=target_title, key="title")
    print(f"    binary_search_count    comparisons = {bs_result['comparison_count']:,}  "
          f"(found at index {bs_result['index']})")

    # --- linear_search_count on original (unsorted) list ---
    ls_copy = copy.deepcopy(records)
    ls_result = linear_search_count(ls_copy, target_value=target_title, key="title")
    print(f"    linear_search_count    comparisons = {ls_result['comparison_count']:,}  "
          f"(found at index {ls_result['index']})")

    # --- worst-case linear (absent value) ---
    ls_absent = linear_search_count(ls_copy, target_value="__absent__", key="title")
    print(f"    linear_search_count    comparisons = {ls_absent['comparison_count']:,}  "
          f"(absent value — scanned full list)")


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Ensure seed user exists
        seed_user = db.query(User).filter(User.email == "seed@taskflow.internal").first()
        if not seed_user:
            seed_user = User(email="seed@taskflow.internal", name="Seed User")
            db.add(seed_user)
            db.commit()
            db.refresh(seed_user)
            print(f"Created seed user  id={seed_user.id}")
        else:
            print(f"Reusing seed user  id={seed_user.id}")

        # Ensure seed project exists
        seed_project = db.query(Project).filter(
            Project.title == "Benchmark Project",
            Project.owner_id == seed_user.id,
        ).first()
        if not seed_project:
            seed_project = Project(title="Benchmark Project", owner_id=seed_user.id)
            db.add(seed_project)
            db.commit()
            db.refresh(seed_project)
            print(f"Created seed project  id={seed_project.id}")
        else:
            print(f"Reusing seed project  id={seed_project.id}")

        pid = seed_project.id

        # ---------------------------------------------------------------
        # Seed + benchmark at three sizes
        # ---------------------------------------------------------------
        SIZES = [10, 500, 3000]
        print("\n=== SEEDING ===")
        for size in SIZES:
            print(f"\nTarget size: {size}")
            seed_to_size(db, pid, size)
            records = build_task_dicts(db, pid)
            actual = len(records)
            print(f"  Rows in DB for project {pid}: {actual}")

        print("\n=== BENCHMARK RESULTS ===")
        for size in SIZES:
            # Pull exactly `size` records for a clean comparison
            rows = (
                db.query(Task)
                .filter(Task.project_id == pid)
                .limit(size)
                .all()
            )
            records = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "due_date": t.due_date,
                    "project_id": t.project_id,
                }
                for t in rows
            ]
            run_benchmark(f"n={size}", records)

        print("\n=== BENCHMARK COMPLETE ===")
        print("Copy the numbers above into README.md Section 2 complexity table.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
