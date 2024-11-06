import re
from enum import Enum


class bcolors(Enum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def __str__(self) -> str:
        return str(self.value)


def cprint(text: str, color: bcolors = bcolors.ENDC) -> str:
    return f"{color}{text}{bcolors.ENDC}"


def next_candidate_name(current, separators=None, position="last"):
    """
    Find next name by incrementing a number in the string.

    Args:
        current: String to process
        separators: List of separator characters (default: ['-', '_', '.', ''])
        position: Which number to increment ('last', 'first', or zero-based index)
    """
    if separators is None:
        separators = ["-", "_", ".", ""]

    sep_pattern = "|".join(map(re.escape, separators))
    pattern = rf"(.*?(?:{sep_pattern}))(\d+)"

    # Find all matches
    matches = list(re.finditer(pattern, current))

    if not matches:
        # No numbers found, append with first separator
        sep = separators[0] if separators else ""
        return f"{current}{sep}1"

    # Determine which match to use
    if position == "last":
        match = matches[-1]
    elif position == "first":
        match = matches[0]
    elif isinstance(position, int) and 0 <= position < len(matches):
        match = matches[position]
    else:
        raise ValueError(f"Invalid position. Found {len(matches)} numbers.")

    # Split string into three parts: before match, the match, after match
    start = current[: match.start()]
    matched_prefix = match.group(1)
    number = int(match.group(2))
    end = current[match.end() :]

    return f"{start}{matched_prefix}{number + 1}{end}"
