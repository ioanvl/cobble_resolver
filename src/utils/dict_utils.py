import copy


def dict_equality(a_dict: dict, b_dict: dict, loose: bool = False):
    """Dictionary equality that supports unordered lists, and empty keys.

    Args:
        a_dict (dict): _description_
        b_dict (dict): _description_
        loose (bool, optional): If a key is present in either
        but its an empty list or dict, ignore it.
    """
    for inp in [a_dict, b_dict]:
        if not isinstance(inp, dict):
            return False

    _proc_keys: set = set()
    _proc_keys.update(list(a_dict.keys()))
    _proc_keys.update(list(b_dict.keys()))

    for key in _proc_keys:
        if (key in a_dict) and (key in b_dict):
            if a_dict[key] == b_dict[key]:
                continue
            elif isinstance(a_dict[key], list) and isinstance(b_dict[key], list):
                if list_equality(a_list=a_dict[key], b_list=b_dict[key]):
                    continue
            elif isinstance(a_dict[key], dict) and isinstance(b_dict[key], dict):
                if dict_equality(a_dict=a_dict[key], b_dict=b_dict[key], loose=loose):
                    continue
            else:
                _temp = [a_dict[key], b_dict[key]]
                if (
                    loose
                    and all([isinstance(inp(list, dict)) for inp in _temp])
                    and all([(not inp) for inp in _temp])
                ):
                    continue
        else:
            if loose:
                _temp = a_dict[key] if key in a_dict else b_dict[key]
                if isinstance(_temp, (dict, list)) and not _temp:
                    continue
        return False


def list_equality(a_list: list, b_list: list, loose: bool = False) -> bool:
    """Deep comparison of lists that may contain nested dictionaries and lists.
    Supports unordered comparison and loose equality rules without modifying inputs.

    Args:
        a_list (list): First list to compare
        b_list (list): Second list to compare
        loose (bool): Whether to apply loose comparison rules

    Returns:
        bool: True if lists are equal according to specified rules
    """
    # Type checking
    for inp in [a_list, b_list]:
        if not isinstance(inp, list):
            return False

    if len(a_list) != len(b_list):
        return False

    # Create deep copies to ensure we don't modify originals
    unmatched_b = copy.deepcopy(b_list)

    for item_a in a_list:
        found_match = False

        for idx, item_b in enumerate(unmatched_b):
            # Direct equality
            if item_a == item_b:
                unmatched_b.pop(idx)
                found_match = True
                break

            # Nested dict comparison
            elif isinstance(item_a, dict) and isinstance(item_b, dict):
                if dict_equality(item_a, item_b, loose=loose):
                    unmatched_b.pop(idx)
                    found_match = True
                    break

            # Nested list comparison
            elif isinstance(item_a, list) and isinstance(item_b, list):
                if list_equality(item_a, item_b, loose=loose):
                    unmatched_b.pop(idx)
                    found_match = True
                    break

        if not found_match:
            return False

    return True
