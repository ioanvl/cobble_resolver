from copy import deepcopy
from typing import Any


def compare(*values: Any, loose: bool = False) -> bool:
    """Smart comparison of multiple values that handles dicts and lists intelligently.

    Args:
        *values: Variable number of values to compare
        loose (bool): If True, allows comparison of empty containers of same type
            and ignores empty containers in dicts. Defaults to False.

    Returns:
        bool: True if all values are equal according to specified rules
    """
    if len(values) < 2:
        return True

    # Get the type of the first value
    first_type = type(values[0])

    # Check if all values are of the same type
    if not all(isinstance(v, first_type) for v in values):
        if loose:
            # In loose mode, allow empty containers of different types
            if all(isinstance(v, (list, dict)) for v in values):
                return all(not v for v in values)
        return False

    # Route to appropriate comparison function based on type
    if isinstance(values[0], dict):
        return dict_equality(*values, loose=loose)
    elif isinstance(values[0], list):
        return list_equality(*values, loose=loose)
    else:
        # For non-container types, use direct equality
        if isinstance(values[0], str) and loose:
            return all(v.lower() == values[0].lower() for v in values[1:])
        return all(v == values[0] for v in values[1:])


def dict_equality(*dicts: dict, loose: bool = False) -> bool:
    """Dictionary equality that supports multiple inputs.
    Performs n-1 comparisons using transitivity property."""
    if len(dicts) < 2:
        return True

    # Type checking
    if not all(isinstance(d, dict) for d in dicts):
        return False

    # Compare sequential pairs
    for i in range(len(dicts) - 1):
        if not _dict_equality_pair(dicts[i], dicts[i + 1], loose=loose):
            return False

    return True


def _dict_equality_pair(a_dict: dict, b_dict: dict, loose: bool = False) -> bool:
    """Helper function for comparing a single pair of dictionaries."""
    _proc_keys: set = set()
    _proc_keys.update(list(a_dict.keys()))
    _proc_keys.update(list(b_dict.keys()))

    for key in _proc_keys:
        if (key in a_dict) and (key in b_dict):
            # Use the smart compare function for all value comparisons
            if compare(a_dict[key], b_dict[key], loose=loose):
                continue

            # Loose comparison for empty containers
            elif (
                loose
                and isinstance(a_dict[key], (list, dict))
                and isinstance(b_dict[key], (list, dict))
                and not a_dict[key]
                and not b_dict[key]
            ):
                continue
            elif (
                loose
                and isinstance(a_dict[key], str)
                and isinstance(b_dict[key], str)
                and a_dict[key].lower() == b_dict[key].lower()
            ):
                continue

            return False

        # Key exists in only one dictionary
        else:
            if loose:
                _temp = a_dict[key] if key in a_dict else b_dict[key]
                if isinstance(_temp, (dict, list)) and not _temp:
                    continue
            return False

    return True


def list_equality(*lists: list, loose: bool = False) -> bool:
    """Deep comparison of multiple lists that may contain nested dictionaries and lists.
    Performs n-1 comparisons using transitivity property."""
    if len(lists) < 2:
        return True

    # Type checking
    if not all(isinstance(lst, list) for lst in lists):
        return False

    # Compare sequential pairs
    for i in range(len(lists) - 1):
        if not _list_equality_pair(lists[i], lists[i + 1], loose=loose):
            return False

    return True


def _list_equality_pair(a_list: list, b_list: list, loose: bool = False) -> bool:
    """Helper function for comparing a single pair of lists."""
    if len(a_list) != len(b_list):
        return False

    unmatched_b = deepcopy(b_list)

    for item_a in a_list:
        found_match = False

        for idx, item_b in enumerate(unmatched_b):
            # Use the smart compare function for all value comparisons
            if compare(item_a, item_b, loose=loose):
                unmatched_b.pop(idx)
                found_match = True
                break

        if not found_match:
            return False

    return True
