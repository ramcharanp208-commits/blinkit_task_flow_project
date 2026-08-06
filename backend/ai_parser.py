import re
from typing import Dict, Any, Optional


def parse_quick_add(description: str) -> Dict[str, Any]:
    """
    Deterministic rule-based mock parser following Section 3 Task 3 requirements:
    a. Lower-cased copy for keyword matching; original string kept for title derivation.
    b. Priority: 'urgent'/'asap' -> 'high', 'whenever'/'low priority' -> 'low', default -> 'medium'.
    c. Due-date hint: strict priority sequence check (today, tomorrow, next week, next <weekday>, bare weekdays).
    d. Title derivation: strips all matched priority & date spans from original-cased description.
    """
    if not description or not description.strip():
        return {
            "title": "Untitled task",
            "priority": "medium",
            "due_date_hint": None
        }

    lower_text = description.lower()

    # ---------------------------------------------------------
    # STEP B: PRIORITY DETECTION & KEYWORD SPAN TRACKING
    # ---------------------------------------------------------
    priority_high_keywords = ["urgent", "asap"]
    priority_low_keywords = ["whenever", "low priority"]

    has_high = any(kw in lower_text for kw in priority_high_keywords)
    has_low = any(kw in lower_text for kw in priority_low_keywords)

    if has_high:
        priority = "high"
    elif has_low:
        priority = "low"
    else:
        priority = "medium"

    # Collect ALL priority spans for stripping (Title-stripping note in step b)
    all_priority_keywords = priority_high_keywords + priority_low_keywords
    matched_priority_spans = []
    for kw in all_priority_keywords:
        for match in re.finditer(re.escape(kw), lower_text):
            matched_priority_spans.append((match.start(), match.end()))

    # ---------------------------------------------------------
    # STEP C: DUE-DATE HINT DETECTION
    # ---------------------------------------------------------
    due_date_hint: Optional[str] = None
    matched_date_spans = []

    # Sequence 1-3: Fixed date phrases
    fixed_date_phrases = ["today", "tomorrow", "next week"]
    
    # Sequence 4: Two-word 'next <weekday>' phrases (Monday to Sunday order)
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    next_weekday_phrases = [f"next {day}" for day in weekdays]
    
    # Sequence 5: Bare day names (Monday to Sunday order)
    bare_weekday_phrases = weekdays

    all_date_checks = fixed_date_phrases + next_weekday_phrases + bare_weekday_phrases

    for date_kw in all_date_checks:
        if date_kw in lower_text:
            due_date_hint = date_kw
            # Collect all occurrences of the matched phrase
            for match in re.finditer(re.escape(date_kw), lower_text):
                matched_date_spans.append((match.start(), match.end()))
            break  # Stop at first matching keyword/phrase

    # ---------------------------------------------------------
    # STEP D: TITLE DERIVATION & STRIPPING
    # ---------------------------------------------------------
    all_spans_to_remove = matched_priority_spans + matched_date_spans

    if not all_spans_to_remove:
        derived_title = description.strip()
    else:
        # Merge overlapping or contiguous spans
        all_spans_to_remove.sort(key=lambda x: x[0])
        merged_spans = []
        for span in all_spans_to_remove:
            if not merged_spans:
                merged_spans.append(span)
            else:
                prev_start, prev_end = merged_spans[-1]
                if span[0] <= prev_end:
                    merged_spans[-1] = (prev_start, max(prev_end, span[1]))
                else:
                    merged_spans.append(span)

        # Build clean title from original-cased description by omitting matched spans
        title_chars = []
        last_idx = 0
        for start, end in merged_spans:
            title_chars.append(description[last_idx:start])
            last_idx = end
        title_chars.append(description[last_idx:])

        derived_title = "".join(title_chars).strip()

    # Fallback to literal placeholder if derived title is empty or whitespace-only
    if not derived_title:
        derived_title = "Untitled task"

    return {
        "title": derived_title,
        "priority": priority,
        "due_date_hint": due_date_hint
    }