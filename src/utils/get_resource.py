import json
import os
import sys
from pathlib import Path

from constants.runtime_const import DEBUG


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # We're running in development mode
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def load_json_from_path(json_path: Path) -> dict:
    try:
        with json_path.open() as f:
            data = json.load(f)
    except (UnicodeDecodeError, json.JSONDecodeError):
        if DEBUG:
            print(f"WARN!! - {json_path}")
            _ = input()
        return dict()
    return data
