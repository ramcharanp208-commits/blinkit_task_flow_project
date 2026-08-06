import sys
from backend.algorithms import (
    insertion_sort,
    binary_search,
    linear_search,
    insertion_sort_count,
    binary_search_count,
    linear_search_count,
)


def run_checks():
    print("--- Running TaskFlow Automated Algorithm Checks ---")

    # Case 1: insertion_sort on empty list
    empty_list = []
    insertion_sort(empty_list, key="priority")
    if empty_list == []:
        print("PASS: insertion_sort on empty list")
    else:
        print(f"FAIL: insertion_sort on empty list — expected [], got {empty_list}")

    # Case 2: insertion_sort on single element
    single_list = [{"title": "A", "val": 5}]
    insertion_sort(single_list, key="val")
    if single_list == [{"title": "A", "val": 5}]:
        print("PASS: insertion_sort on single-element list")
    else:
        print(f"FAIL: insertion_sort single element — got {single_list}")

    # Case 3: binary_search boundary matches (first, last, middle)
    sorted_items = [
        {"id": 1, "title": "Apple"},
        {"id": 2, "title": "Banana"},
        {"id": 3, "title": "Cherry"},
        {"id": 4, "title": "Date"},
        {"id": 5, "title": "Elderberry"},
    ]

    idx_first = binary_search(sorted_items, "Apple", key="title")
    idx_mid = binary_search(sorted_items, "Cherry", key="title")
    idx_last = binary_search(sorted_items, "Elderberry", key="title")

    if idx_first == 0 and idx_mid == 2 and idx_last == 4:
        print("PASS: binary_search boundary matches (first, mid, last)")
    else:
        print(f"FAIL: binary_search boundaries — got first:{idx_first}, mid:{idx_mid}, last:{idx_last}")

    # Case 4: binary_search missing target
    idx_missing = binary_search(sorted_items, "Fig", key="title")
    if idx_missing == -1:
        print("PASS: binary_search absent target returns -1")
    else:
        print(f"FAIL: binary_search missing target — expected -1, got {idx_missing}")

    # Case 5: insertion_sort_count validation
    unsorted_list = [
        {"val": 3},
        {"val": 1},
        {"val": 4},
        {"val": 2},
    ]
    comp_count = insertion_sort_count(unsorted_list, key="val")
    is_sorted = unsorted_list == [{"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}]
    if is_sorted and isinstance(comp_count, int) and comp_count > 0:
        print("PASS: insertion_sort_count returns int > 0 and sorts list in-place")
    else:
        print(f"FAIL: insertion_sort_count — sorted:{is_sorted}, count:{comp_count}")

    # Case 6: binary_search_count validation
    bs_res = binary_search_count(sorted_items, "Cherry", key="title")
    if (
        isinstance(bs_res, dict)
        and bs_res.get("index") == 2
        and isinstance(bs_res.get("comparison_count"), int)
        and bs_res["comparison_count"] > 0
    ):
        print("PASS: binary_search_count structure and index match")
    else:
        print(f"FAIL: binary_search_count — got {bs_res}")

    # Case 7: linear_search_count for absent value
    ls_res = linear_search_count(sorted_items, "Mango", key="title")
    if (
        isinstance(ls_res, dict)
        and ls_res.get("index") == -1
        and ls_res.get("comparison_count") == len(sorted_items)
    ):
        print("PASS: linear_search_count absent target scans full length")
    else:
        print(f"FAIL: linear_search_count absent — got {ls_res}")


if __name__ == "__main__":
    run_checks()