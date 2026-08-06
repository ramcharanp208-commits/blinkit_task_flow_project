from typing import List, Dict, Any, Union, Optional


# ==========================================
# CORE ALGORITHMS (REQUIREMENT COMPLIANT)
# ==========================================

def insertion_sort(records: List[Dict[str, Any]], key: str) -> None:
    """
    Sorts a list of dictionaries in-place by record[key].
    Mutates the list directly with O(1) auxiliary space.
    """
    for i in range(1, len(records)):
        current_item = records[i]
        j = i - 1
        while j >= 0 and records[j][key] > current_item[key]:
            records[j + 1] = records[j]
            j -= 1
        records[j + 1] = current_item


def binary_search(sorted_records: List[Dict[str, Any]], target_value: Any, key: str) -> int:
    """
    Performs binary search on a list sorted by key using low/high/mid pointers.
    Returns index of target match, or -1 if absent.
    """
    low = 0
    high = len(sorted_records) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid][key]

        if mid_val == target_value:
            return mid
        elif mid_val < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return -1


def linear_search(records: List[Dict[str, Any]], target_value: Any, key: str) -> int:
    """
    Scans every record sequentially.
    Returns index of first match, or -1 if absent.
    """
    for index, record in enumerate(records):
        if record[key] == target_value:
            return index
    return -1


# ==========================================
# BENCHMARK WRAPPERS (FOR DAY 6 / SECTION 2)
# ==========================================

def insertion_sort_count(records: List[Dict[str, Any]], key: str) -> int:
    """
    Sorts records in-place and returns ONLY the comparison count (int).
    """
    comparison_count = 0
    for i in range(1, len(records)):
        current_item = records[i]
        j = i - 1
        while j >= 0:
            comparison_count += 1
            if records[j][key] > current_item[key]:
                records[j + 1] = records[j]
                j -= 1
            else:
                break
        records[j + 1] = current_item
    return comparison_count


def binary_search_count(sorted_records: List[Dict[str, Any]], target_value: Any, key: str) -> Dict[str, Union[int, None]]:
    """
    Returns dict with exactly two keys: 'index' and 'comparison_count'.
    """
    low = 0
    high = len(sorted_records) - 1
    comparison_count = 0

    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid][key]
        comparison_count += 1

        if mid_val == target_value:
            return {"index": mid, "comparison_count": comparison_count}
        elif mid_val < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return {"index": -1, "comparison_count": comparison_count}


def linear_search_count(records: List[Dict[str, Any]], target_value: Any, key: str) -> Dict[str, Union[int, None]]:
    """
    Returns dict with exactly two keys: 'index' and 'comparison_count'.
    """
    comparison_count = 0
    for index, record in enumerate(records):
        comparison_count += 1
        if record[key] == target_value:
            return {"index": index, "comparison_count": comparison_count}

    return {"index": -1, "comparison_count": comparison_count}