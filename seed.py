"""
seed.py — TaskFlow Section 2 Benchmark Script
==============================================
Runs the comparison-counting benchmark wrappers on synthetic in-memory task
data at three sizes (10, 500, 3000 rows) that mirror the exact dict shape used
by the real endpoints.  This avoids slow DB inserts while still exercising the
same algorithm functions that power GET /tasks?sort=priority and
GET /tasks/search.

Usage (from project root, with venv active):
    python seed.py
"""

import sys
import os
import copy
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.algorithms import (
    insertion_sort_count,
    binary_search_count,
    linear_search_count,
)

# ---------------------------------------------------------------------------
# Realistic title/priority/due_date pools (same vocabulary as the real app)
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


def make_synthetic_records(n: int) -> list:
    """Generate n task dicts with the exact field set the endpoints use."""
    random.seed(42)          # fixed seed for reproducible counts
    records = []
    for i in range(n):
        prefix  = TITLE_PREFIXES[i % len(TITLE_PREFIXES)]
        subject = TITLE_SUBJECTS[i % len(TITLE_SUBJECTS)]
        records.append({
            "id":         i + 1,
            "title":      "{} {} #{}".format(prefix, subject, i + 1),
            "priority":   random.choice(PRIORITIES),
            "due_date":   random.choice(DUE_DATES),
            "project_id": 1,
        })
    return records


def run_benchmark(n: int) -> None:
    """Run all three counting wrappers and print exact comparison counts."""
    records = make_synthetic_records(n)
    print("\n[n = {}]".format(n))

    # ── insertion_sort_count ──────────────────────────────────────────────
    sort_copy   = copy.deepcopy(records)
    sort_comps  = insertion_sort_count(sort_copy, key="title")
    print("  insertion_sort_count   comparisons = {:,}".format(sort_comps))

    # After sorting, pick the middle element as the search target
    mid_idx    = n // 2
    mid_title  = sort_copy[mid_idx]["title"]

    # ── binary_search_count (operates on already-sorted copy) ────────────
    bs = binary_search_count(sort_copy, target_value=mid_title, key="title")
    print("  binary_search_count    comparisons = {:,}  (found at index {})".format(
        bs["comparison_count"], bs["index"]))

    # ── linear_search_count — hit case (unsorted original) ───────────────
    ls_copy = copy.deepcopy(records)
    ls_hit  = linear_search_count(ls_copy, target_value=mid_title, key="title")
    print("  linear_search_count    comparisons = {:,}  (hit  — index {})".format(
        ls_hit["comparison_count"], ls_hit["index"]))

    # ── linear_search_count — miss case (absent value) ───────────────────
    ls_miss = linear_search_count(ls_copy, target_value="__absent__", key="title")
    print("  linear_search_count    comparisons = {:,}  (miss — scanned full list)".format(
        ls_miss["comparison_count"]))


def main():
    print("=" * 60)
    print("TaskFlow — Algorithm Benchmark (Section 2)")
    print("Synthetic in-memory data, same dict shape as real endpoints")
    print("=" * 60)

    for n in [10, 500, 3000]:
        run_benchmark(n)

    print("\n" + "=" * 60)
    print("Copy the numbers above into README.md Section 2 table.")
    print("=" * 60)


if __name__ == "__main__":
    main()
