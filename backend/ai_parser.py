"""
ai_parser.py — TaskFlow AI Quick-Add parser
============================================
Two modes:
  1. MOCK (default, zero API calls) — deterministic rule-based parser.
  2. GROQ  (optional, set GROQ_API_KEY env var) — real LLM via Groq API.
     Model: llama3-8b-8192  (fast, free-tier friendly)

The endpoint falls back to MOCK automatically if:
  - GROQ_API_KEY is not set
  - Groq API call fails for any reason
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("taskflow.ai_parser")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — REQUIRED MOCK PARSER  (always used when Groq is unavailable)
# ══════════════════════════════════════════════════════════════════════════════

def parse_quick_add(description: str) -> Dict[str, Any]:
    """
    Deterministic rule-based mock parser.
    Returns: { title, priority, due_date_hint }
    """
    if not description or not description.strip():
        return {"title": "Untitled task", "priority": "medium", "due_date_hint": None}

    lower = description.lower()

    # ── STEP B: Priority ──────────────────────────────────────────────────────
    high_kws = ["urgent", "asap"]
    low_kws  = ["whenever", "low priority"]

    has_high = any(kw in lower for kw in high_kws)
    has_low  = any(kw in lower for kw in low_kws)
    priority = "high" if has_high else ("low" if has_low else "medium")

    # Collect spans to strip from title
    priority_spans = []
    for kw in (high_kws + low_kws):
        for m in re.finditer(re.escape(kw), lower):
            priority_spans.append((m.start(), m.end()))

    # ── STEP C: Due-date hint ─────────────────────────────────────────────────
    weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    date_checks = (
        ["today", "tomorrow", "next week"]
        + [f"next {d}" for d in weekdays]
        + weekdays
    )

    due_date_hint: Optional[str] = None
    date_spans: list = []

    for kw in date_checks:
        if kw in lower:
            due_date_hint = kw
            for m in re.finditer(re.escape(kw), lower):
                date_spans.append((m.start(), m.end()))
            break

    # ── STEP D: Title derivation ──────────────────────────────────────────────
    all_spans = sorted(priority_spans + date_spans, key=lambda x: x[0])
    # merge overlapping spans
    merged: list = []
    for span in all_spans:
        if merged and span[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], span[1]))
        else:
            merged.append(list(span))

    if not merged:
        title = description.strip()
    else:
        parts, last = [], 0
        for s, e in merged:
            parts.append(description[last:s])
            last = e
        parts.append(description[last:])
        title = "".join(parts).strip()

    if not title:
        title = "Untitled task"

    return {"title": title, "priority": priority, "due_date_hint": due_date_hint}


# ══════════════════════════════════════════════════════════════════════════════
# GROQ REAL-LLM PARSER  (optional — activated by GROQ_API_KEY env var)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_with_groq(description: str) -> Optional[Dict[str, Any]]:
    """
    Calls Groq API (llama3-8b-8192) to extract task fields.
    Returns parsed dict or None on any failure.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from groq import Groq  # imported lazily so missing package won't break mock mode
        client = Groq(api_key=api_key)

        system_msg = (
            "You are a task-extraction assistant. "
            "Given a plain-English task description, extract three fields and return ONLY valid JSON:\n"
            '  {"title": "<string>", "priority": "low"|"medium"|"high", "due_date_hint": "<string or null>"}\n'
            "Rules:\n"
            "- title: cleaned task title, no priority/date keywords.\n"
            "- priority: 'high' if urgent/asap, 'low' if whenever/low priority, else 'medium'.\n"
            "- due_date_hint: exact date phrase (today/tomorrow/next friday/etc.) or null.\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )

        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": description},
            ],
            temperature=0.1,
            max_tokens=120,
        )

        raw = chat.choices[0].message.content.strip()
        # Strip markdown code fences if model wraps response
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)

        title    = str(parsed.get("title", "") or "").strip() or "Untitled task"
        priority = parsed.get("priority", "medium")
        if priority not in ("low", "medium", "high"):
            priority = "medium"
        due_date_hint = parsed.get("due_date_hint") or None

        logger.info("Groq parsed: title=%r priority=%s due=%s", title, priority, due_date_hint)
        return {"title": title, "priority": priority, "due_date_hint": due_date_hint}

    except Exception as exc:
        logger.warning("Groq parse failed (%s), falling back to mock.", exc)
        return None


def parse_task_description(description: str) -> Dict[str, Any]:
    """
    Public entry point used by the /tasks/quick-add endpoint.
    Tries Groq first; falls back to mock parser automatically.
    Returns dict with keys: title, priority, due_date_hint, used_ai (bool)
    """
    groq_result = _parse_with_groq(description)
    if groq_result:
        groq_result["used_ai"] = True
        return groq_result

    mock_result = parse_quick_add(description)
    mock_result["used_ai"] = False
    return mock_result
