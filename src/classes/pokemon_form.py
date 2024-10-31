from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, Generator, Iterable, Literal, LiteralString, Optional
import json
from json import JSONDecodeError
import zipfile
import shutil
from utils.cli_utils.keypress import positive_int_choice
from utils.safe_parse_deco import safe_parse_per_file
from utils.cli_utils.keypress import clear_line
from constants.char_constants import TextSymbols
from utils.cli_utils.generic import bool_square, line_header
from utils.directory_utils import clear_empty_dir
from typing import TYPE_CHECKING


from classes.base_classes import bcfo


if TYPE_CHECKING:
    from classes.pokemon import Pokemon
    from classes.pack import Pack


@dataclass
class PokemonForm:
    name: str | None = None

    aspects: list[str] = field(default_factory=list)
    # looks
    resolver_assignments: set[int] = field(default_factory=set)

    species: bcfo | None = None
    species_additions: bcfo | None = None

    spawn_pool: list[Path] = field(default_factory=list)

    parent_pokemon: Optional["Pokemon"] = None
    parent_pack: Optional["Pack"] = None

    def __repr__(self) -> str:
        s: str = self._st()
        ret: str = ""
        if self.name != "base_form":
            ret += f"{s} {self.name if self.name else self.aspects}\n"
        ret += f"{s} "
        ret += f"DATA: Spawn:{bool_square(len(self.spawn_pool))} | "
        ret += f"S:{self.__square_atr(self.species)}"
        ret += f"/{self.__square_atr(self.species_additions)}:SA "

        if self.name == "base_form" and (self.parent_pokemon is not None):
            ret += (
                f"| {TextSymbols.music_symbol}:{bool_square(self.parent_pack.sounds)} "
            )
            if self.parent_pokemon.sa_transfers_received:
                ret += " +SA"

            if self.parent_pokemon.requested:
                ret += " +Req"
                if req_diff := (
                    self.parent_pokemon.requested
                    - self.parent_pokemon.request_transfered
                ):
                    ret += f"[{req_diff}]"
                    if self.parent_pokemon._is_actively_requested():
                        ret += TextSymbols.left_arrow
                    # else:
                    #     if self.parent_pack and self.parent_pack.parent_combiner:
                    #         if self.parent_pack.parent_combiner._is_selected(
                    #             pokemon_name=self.parent_pokemon.internal_name
                    #         ):
                    #             ret += TextSymbols.x_symbol

                else:
                    ret += f"[{TextSymbols.check_mark}]"

        ret += f"\n{s} {'-' * 10}"
        return ret

    @property
    def comp_stamp(self) -> list[bool]:
        res = list()
        res.append(self.has_spawn())
        res.append(self.has_species_data())
        res.append(self.species_additions is not None)
        x = bool(len(self.resolver_assignments))
        res.append(x)
        if x:
            r: list[bool] = list(self._get_resolvers().values())[0].comp_stamp
            res.extend(r)

        else:
            res.extend([False, False, False, False, False])

        return res

    def get_all_paths(self) -> list[Path]:
        res: set[Path] = set()
        for x in [self.species, self.species_additions]:
            if x:
                res.add(x.file_path)
        for s in self.spawn_pool:
            res.add(s)
        if self.parent_pokemon:
            for i in self.resolver_assignments:
                res.update(self.parent_pokemon.resolvers[i].get_all_paths())
        return list(res)

    def is_complete(self) -> bool:
        return (
            self.has_spawn()
            and self.has_species_data()
            and self.is_graphically_complete()
        )

    def is_addition(self, only: bool = True) -> bool:
        stamp = self.comp_stamp
        flag2 = (sum(stamp) == 1) if only else (not stamp[1])
        return stamp[2] and flag2

    def is_species(self, only: bool = True) -> bool:
        stamp = self.comp_stamp
        flag2 = (sum(stamp) == 1) if only else (not stamp[2])
        return stamp[1] and flag2

    def is_data(self) -> bool:
        stamp = self.comp_stamp
        return stamp[1] and stamp[2] and (sum(stamp) == 2)

    def has_spawn(self) -> bool:
        return bool(len(self.spawn_pool))

    def has_species_data(self) -> bool:
        return self.species is not None

    def has_addition_data(self) -> bool:
        return self.species_additions is not None

    def has_sp_data(self) -> bool:
        return self.has_species_data() or self.has_addition_data()

    def is_graphically_complete(self) -> bool:
        stamp = self.comp_stamp
        return stamp[3] and stamp[4] and stamp[6] and stamp[7] and stamp[8]

    def has_graphics(self) -> bool:
        stamp: list[bool] = self.comp_stamp
        if stamp[3]:
            if any(stamp[4:]):
                return True
        return False

    def _get_resolvers(self) -> dict[int, "ResolverEntry"]:
        if self.parent_pack is None:
            return {}
        return {r: self.parent_pokemon.resolvers[r] for r in self.resolver_assignments}

    def is_requested(self) -> bool:
        if self.parent_pokemon:
            return bool(
                self.parent_pokemon.requested
                and (
                    self.parent_pokemon.requested
                    - self.parent_pokemon.request_transfered
                )
            )
        return False

    def _st(self) -> LiteralString:
        return f"{' '*(3 if (self.name != 'base_form') else 0)}|"

    def __square_atr(self, val: Any) -> str:
        return bool_square(val is not None)


@dataclass
class ResolverEntry:
    order: int
    own_path: Path | None = None
    models: set[Path] = field(default_factory=set)

    posers: set[Path] = field(default_factory=set)
    animations: set[Path] = field(default_factory=set)

    textures: set[Path] = field(default_factory=set)
    has_shiny: bool = False

    aspects: set[str] = field(default_factory=set)

    requested_animations: dict[str, dict[str, bool]] = field(default_factory=dict)
    # TODO add warning for missing animations

    def __repr__(self) -> str:
        res: str = ""
        res += f"M:{bool_square(len(self.models))} | "

        res += f"P:{bool_square(len(self.posers))} "
        res += f"A:{bool_square(len(self.animations))} | "

        res += f"T:{bool_square(len(self.textures))} "
        res += f"Ts:{bool_square(self.has_shiny)} "

        return res

    @property
    def comp_stamp(self) -> list[bool]:
        res = list()
        res.append(bool(len(self.models)))

        res.append(bool(len(self.posers)))
        res.append(bool(len(self.animations)))

        res.append(bool(len(self.textures)))
        res.append(self.has_shiny)
        return res

    def get_all_paths(self) -> set[Path]:
        res: set[Path] = set()
        res.add(self.own_path)
        for x in [self.models, self.posers, self.animations, self.textures]:
            res.update(x)
        return res
