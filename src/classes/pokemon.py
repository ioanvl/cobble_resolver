from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from classes.base_classes import PackHolder
from classes.sounds import SoundEntry
from utils.text_utils import bcolors, cprint

if TYPE_CHECKING:
    from classes.evolutions import EvolutionEntry
    from classes.pack import Pack
    from classes.pokemon_form import PokemonForm, ResolverEntry


@dataclass
class MergePokemon:
    internal_name: str
    name: str | None = None
    dex_id: int | None = None

    species_base: dict | None = None
    species_addition: dict | None = None
    spawn_pool: dict | None = None

    picked_mon: Pokemon | None = None
    extra_mons: list[str] = field(default_factory=list)

    holder: PackHolder | None = None


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
    merged: bool = False
    merge_pick: bool = False

    requested: int = 0
    request_transfered: int = 0

    sa_transfers_received: set[Path] = field(default_factory=set)

    _extracted_sa: dict = field(default_factory=dict)

    is_pseudoform: bool = False

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

    def is_fully_data_merged(self):
        return all([f.is_fully_data_merged() for f in self.forms.values()])

    def is_partially_data_merged(self):
        return any([f.is_fully_data_merged() for f in self.forms.values()]) or any(
            [f.is_partially_data_merged() for f in self.forms.values()]
        )

    def _display(
        self,
        color: bool = True,
        exclude_merged: bool = False,
        merge_mode: bool = False,
    ):
        ret: str = f"#{self.dex_id} - "
        if self.is_pseudoform:
            ret += f"[{cprint(text="PF", color=bcolors.WARNING)}]"
        if self.name is None:
            ret += f"[{self.internal_name}]"
        else:
            ret += f"{self.name}"

        for f in self.forms.values():
            ret += "\n"
            ret += f._display(color=color, merge_mode=merge_mode)
        return ret

    def __repr__(self) -> str:
        return self._display(color=False)

    def has_graphics(self):
        return bool(self.resolvers)
