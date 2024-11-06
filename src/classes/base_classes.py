from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from classes.pokemon import Pokemon


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


@dataclass
class PackHolder:
    mons: dict[str, "Pokemon"]
    dex_num: int
    name: str
