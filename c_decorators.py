import functools
import json
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Callable, TypeVar
from cli_utils import clear_line

T = TypeVar("T")


# Version 1: Call function for each file
def safe_parse_per_file(
    component_attr: str, file_pattern: str = "*.json", DEBUG: bool = False
):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> None:
            if (self.component_location is None) or (
                getattr(self.component_location, component_attr, None) is None
            ):
                if self.verbose:
                    print(f"-- No {component_attr.replace('_', ' ').title()}")
                return None

            print(f"-- Parsing {component_attr.replace('_', ' ').title()}")

            location = getattr(self.component_location, component_attr)

            for file_path in location.rglob(file_pattern):
                try:
                    try:
                        with file_path.open() as f:
                            data = json.load(f)
                    except (UnicodeDecodeError, JSONDecodeError) as _:
                        if DEBUG:
                            print(f"WARN!! - {file_path}")
                            _ = input()
                        continue

                    func(self, file_path, data, *args, **kwargs)

                except Exception as e:
                    print(f"\n\n{file_path}\n\n")
                    raise e

            if not self.verbose:
                print(clear_line, end="")

        return wrapper

    return decorator
