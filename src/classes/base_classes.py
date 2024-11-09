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
    internal_name: str | None = None

    def __len__(self) -> int:
        return len(self.mons)

    def has_base(self):
        for mon in self.mons.values():
            if mon.parent_pack is not None:
                if mon.parent_pack.is_base:
                    return True
        return False

    def __str__(self):
        _outp = ""
        _outp += f"#{self.dex_num} - {self.name}\n"

        keys = list(self.mons.keys())

        for i, k in enumerate(keys):
            pack_name = k
            p = self.mons[pack_name]
            outp = repr(p)
            out_parts = outp.split("\n")
            out_parts[0] = f"{i+1}. {pack_name}"
            outp = "\n".join(out_parts)
            _outp += f"{outp}\n"
        return _outp
