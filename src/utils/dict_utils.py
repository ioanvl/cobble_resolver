from copy import deepcopy
from typing import Any, Dict, List


def combine(*values: Any) -> Any:
    """Smart combination of multiple values that handles dicts and lists intelligently.

    Args:
        *values: Variable number of values to combine

    Returns:
        Combined value maintaining the type of the first non-None input
    """
    if len(values) < 2:
        return values[0] if values else None

    # Filter out None values
    filtered_values = [v for v in values if v is not None]
    if not filtered_values:
        return None

    # Get the type of the first value
    first_type = type(filtered_values[0])

    # Check if all non-None values are of compatible types
    if not all(isinstance(v, first_type) for v in filtered_values):
        # If values are of different types, return the first value
        return filtered_values[0]

    # Route to appropriate combination function based on type
    if isinstance(filtered_values[0], dict):
        return dict_combine(*filtered_values)
    elif isinstance(filtered_values[0], list):
        return list_combine(*filtered_values)
    else:
        # For non-container types, return the first non-empty value
        return next((v for v in filtered_values if v), filtered_values[0])


def dict_combine(*dicts: Dict) -> Dict:
    """Combines multiple dictionaries with nested combining of values.

    When there are conflicts:
    - If one value is empty (None, empty dict, or empty list)
        and the other isn't, takes the non-empty value
    - If both values are containers (dict or list), combines them recursively
    - Otherwise takes the last non-None value
    """
    if len(dicts) < 2:
        return dicts[0] if dicts else {}

    # Type checking
    if not all(isinstance(d, dict) for d in dicts):
        return dicts[0]

    # Start with a deep copy of the first dict
    result = deepcopy(dicts[0])

    # Combine with each subsequent dict
    for next_dict in dicts[1:]:
        if not next_dict:  # Skip empty dicts
            continue

        for key, value in next_dict.items():
            if key not in result:
                result[key] = deepcopy(value)
                continue

            # Both dicts have this key - need to resolve
            if _is_empty(result[key]) and not _is_empty(value):
                # Take non-empty value
                result[key] = deepcopy(value)
            elif _is_empty(value) and not _is_empty(result[key]):
                # Keep existing non-empty value
                continue
            elif isinstance(result[key], (dict, list)) and isinstance(
                value, (dict, list)
            ):
                # Recursively combine containers
                result[key] = combine(result[key], value)
            elif value is not None:
                # Take the new value if it's not None
                result[key] = deepcopy(value)

    return result


def list_combine(*lists: List) -> List:
    """Combines multiple lists, maintaining uniqueness of elements.

    For nested elements:
    - Primitive values are combined using set-like behavior
    - Dicts and lists are deep compared and combined if matching elements are found
    """
    if len(lists) < 2:
        return lists[0] if lists else []

    # Type checking
    if not all(isinstance(lst, list) for lst in lists):
        return lists[0]

    result = []
    seen = []  # Track "equivalent" items for smarter deduplication

    for lst in lists:
        if not lst:  # Skip empty lists
            continue

        for item in lst:
            # Check if we've seen an equivalent item
            found_match = False
            for idx, seen_item in enumerate(seen):
                if _are_equivalent(item, seen_item):
                    # Combine with existing equivalent item
                    if isinstance(item, (dict, list)):
                        result[idx] = combine(result[idx], item)
                    found_match = True
                    break

            if not found_match:
                # New unique item
                result.append(deepcopy(item))
                seen.append(deepcopy(item))

    return result


def _is_empty(value: Any) -> bool:
    """Helper function to check if a value is effectively empty."""
    if value is None:
        return True
    if isinstance(value, (dict, list)) and not value:
        return True
    return False


def _are_equivalent(a: Any, b: Any) -> bool:
    """
    Helper function to check if two values should
    be considered equivalent for combining.
    """
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a.keys()) == set(b.keys()) and all(
            _are_equivalent(a[k], b[k]) for k in a.keys()
        )
    if isinstance(a, list):
        return len(a) == len(b) and all(any(_are_equivalent(x, y) for y in b) for x in a)
    return a == b
