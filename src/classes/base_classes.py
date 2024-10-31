from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, Generator, Iterable, Literal, LiteralString, Optional
import json
from json import JSONDecodeError
import zipfile
import shutil


@dataclass
class bcfo:
    file_path: Path
    source: dict
    # partial: bool = False


class FeatureType(Enum):
    FLAG = "flag"
    CHOICE = "choice"
    INTEGER = "integer"


@dataclass
class Feature(bcfo):
    name: str
    keys: list[str]
    feat_type: FeatureType
    aspect: bool

    # duplicate: bool = False

    def __repr__(self) -> str:
        return f"{str(self.feat_type.name)[0:2]} - {self.name}"


@dataclass
class FeatureAssignment(bcfo):
    name: str
    incl_pokemon: list[str]


@dataclass
class LangEntry:
    name: str
    file_path: Path
    source: dict
    incl_pokemon: set[str] = field(default_factory=set)


@dataclass
class LangResultEntry:
    name: str
    data: dict
