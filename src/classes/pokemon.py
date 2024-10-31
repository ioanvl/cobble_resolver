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
from classes.sounds import SoundEntry
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from classes.pokemon_form import PokemonForm, ResolverEntry
    from classes.pack import Pack
    from classes.evolutions import EvolutionEntry


@dataclass
class Pokemon:
    internal_name: str
    name: str | None = None
    dex_id: int | None = None

    features: list[str] = field(default_factory=list)
    forms: dict[str, PokemonForm] = field(default_factory=dict)
    resolvers: dict[int, ResolverEntry] = field(default_factory=dict)

    sound_entry: SoundEntry | None = None

    parent_pack: Optional["Pack"] = None
    selected: bool = False

    requested: int = 0
    request_transfered: int = 0

    sa_transfers_received: set[Path] = field(default_factory=set)

    pre_evos: int = 0
    evos: int = 0

    def select(self) -> None:
        if not self.parent_pack:
            return  # means the pack hasnt been processed
        self.selected = True
        # self._mark_requests()

    def _mark_requests(self) -> None:
        evo_requests: list[EvolutionEntry] = (
            self.parent_pack.registered_evolutions.get_evolutions(
                result=self.internal_name
            )
        )

        for entry in evo_requests:
            if entry.is_addition:
                self.sa_transfers_received.add(entry.file_path)

            pre_evolution = entry.from_pokemon
            pre_evolution = pre_evolution.split("_")[0]

            if pre_evolution in self.parent_pack.pokemon:
                self.parent_pack.pokemon[pre_evolution].requested += 1
                if entry.is_addition:
                    self.parent_pack.pokemon[pre_evolution].request_transfered += 1

    def _remaining_requests(self) -> bool:
        return bool(self.requested - self.request_transfered)

    def _is_actively_requested(self) -> bool:
        if self._remaining_requests():
            if self.parent_pack and self.parent_pack.registered_evolutions:
                evos = self.parent_pack.registered_evolutions.get_evolution_names(
                    source=self.internal_name, result=self.internal_name
                )
                return bool(
                    sum(
                        [
                            (1 if self.parent_pack.pokemon[name].selected else 0)
                            for name in evos
                            if name in self.parent_pack.pokemon
                        ]
                    )
                )
        return False

    def get_all_export_paths(self):
        res: set[Path] = set()
        for form in self.forms.values():
            res.update(form.get_all_paths())
        if self.sound_entry is not None:
            res.update(self.sound_entry.get_all_files())
        res.update(self.sa_transfers_received)
        res.update(self._get_relevant_feature_files())
        return list(res)

    def get_all_paths(self) -> set[Path]:
        res: set[Path] = set()
        res.update(self.get_all_export_paths())
        for r in self.resolvers.values():
            res.update(r.get_all_paths())
        return res

    def _get_relevant_feature_files(self) -> set[Path]:
        res: set[Path] = set()
        feats: set[str] = set(self.features)
        for fa in self.parent_pack.feature_assignments:
            if self.internal_name in fa.incl_pokemon:
                res.add(fa.file_path)
                feats.update(fa.source.get("features", list()))
        for feat in feats:
            if feat in self.parent_pack.features:
                res.add(self.parent_pack.features[feat].file_path)
            else:
                for pf in self.parent_pack.features.values():
                    if feat in pf.keys:
                        res.add(pf.file_path)
        return res

    def __repr__(self) -> str:
        ret: str = f"#{self.dex_id} - "
        if self.name is None:
            ret += f"[{self.internal_name}]"
        else:
            ret += f"{self.name}"

        for f in self.forms.values():
            ret += "\n"
            pok_f: str = repr(f)
            if al := len(f.resolver_assignments):
                p_parts = pok_f.split("\n")
                p_parts.append(p_parts[-1])
                p_parts[-2] = (
                    f"{f._st()} {repr(self.resolvers[list(f.resolver_assignments)[0]])}"
                )
                if al > 1:
                    p_parts[-2] = p_parts[-2] + f"  +{al-1}"
                pok_f = "\n".join(p_parts)
            ret += pok_f
        return ret
