from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from constants.runtime_const import gcr_settings
from constants.text_constants import DefaultNames
from utils.text_utils import bcolors, c_text

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
    data: dict[str, str]


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

    def display(
        self,
        color: bool = False,
        only_graphics: bool = False,
        exclude_merged: bool = False,
        show_merged: bool = False,
    ):
        outp, _ = self._display(
            color=color,
            only_graphics=only_graphics,
            exclude_merged=exclude_merged,
            show_merged=show_merged,
        )
        return outp

    def _get_auto_merged_keys(self) -> list[str]:
        return [
            k
            for k in self.mons.keys()
            if (
                (not self.mons[k].has_graphics())
                and (
                    self.mons[k].is_fully_data_merged()
                    or self.mons[k].is_partially_data_merged()
                )
            )
        ]

    def _get_generation(self) -> str | None:
        if DefaultNames.BASE_COBBLE_MOD in self.mons:
            species_file = (
                self.mons[DefaultNames.BASE_COBBLE_MOD]
                .forms[DefaultNames.BASE_FORM]
                .species.source
            )
            if "labels" in species_file:
                for label in species_file["labels"]:
                    if label.startswith("gen"):
                        return label[-1]

        for mon in self.mons.values():
            for form in mon.forms.values():
                if form.species is not None:
                    species_file = form.species.source
                    if "labels" in species_file:
                        for label in species_file["labels"]:
                            if label.startswith("gen"):
                                return label[-1]

    def _get_graphics_keys(self) -> list[str]:
        return [k for k in self.mons.keys() if self.mons[k].has_graphics()]

    def _get_unprocessable_keys(self) -> list[str]:
        return [
            k
            for k, mon in self.mons.items()
            if (
                (mon.parent_pack.is_base)
                or (mon.parent_pack.is_mod and (not gcr_settings.PROCESS_MODS))
            )
        ]

    def _display(
        self,
        color: bool = False,
        only_graphics: bool = False,
        exclude_merged: bool = False,
        show_merged: bool = False,
    ):
        _outp = ""
        _outp += f"#{self.dex_num} - {self.name}\n"

        keys = list(self.mons.keys())
        if only_graphics:
            keys = [k for k in keys if self._get_graphics_keys()]
        if exclude_merged:
            keys = [k for k in keys if k not in self._get_auto_merged_keys()]

        if show_merged:
            _temp = [
                k
                for k in self.mons.keys()
                if ((k not in keys) and k != DefaultNames.BASE_COBBLE_MOD)
            ]
            _temp = [
                c_text(k, color=None if (not color) else self._entry_color(self.mons[k]))
                for k in _temp
            ]
            if _temp:
                _outp += f"{'-' * 10}\n"
                for _t in _temp:
                    _outp += _t
                    _outp += "\n"
                _outp += f"{'-' * 10}\n"

        for i, k in enumerate(keys):
            pack_name = k
            p = self.mons[pack_name]
            outp = p._display(
                color=color, exclude_merged=exclude_merged, merge_mode=show_merged
            )
            out_parts = outp.split("\n")

            out_parts[0] = c_text(
                f"{i+1}. {pack_name}",
                color=None if (not color) else self._entry_color(mon=self.mons[k]),
            )

            outp = "\n".join(out_parts)
            _outp += f"{outp}\n"
        return _outp, keys

    @staticmethod
    def _entry_color(mon: "Pokemon") -> bcolors:
        if mon.parent_pack.is_base or (
            mon.parent_pack.is_mod and (not gcr_settings.PROCESS_MODS)
        ):
            return bcolors.UNDERLINE
        elif mon.is_fully_data_merged():
            return bcolors.OKGREEN
        elif mon.is_partially_data_merged():
            return bcolors.OKCYAN
        else:
            return bcolors.ENDC

    def __str__(self) -> str:
        return self.display(color=False, only_graphics=False)
