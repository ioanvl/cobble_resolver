from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from classes.base_classes import PackHolder
from constants.runtime_const import gcr_settings
from constants.text_constants import DefaultNames
from utils.get_resource import load_json_from_path
from utils.text_utils import bcolors, next_candidate_name

if TYPE_CHECKING:
    from classes.combiner.combiner import Combiner
    from classes.pokemon import Pokemon
    from classes.pokemon_form import PokemonForm


class MergeST(Enum):
    FULL = -1
    NO = 0
    PARTIAL = 1


merge_color_assignment: dict[int, bcolors] = {
    -1: bcolors.OKGREEN,
    0: bcolors.ENDC,
    1: bcolors.OKCYAN,
}


@dataclass
class MergeStatus:
    spawn_pool: MergeST = MergeST.NO
    species: MergeST = MergeST.NO
    species_additions: MergeST = MergeST.NO


@dataclass
class MergeData:
    spawn_pool: dict = field(default_factory=dict)
    species: dict = field(default_factory=dict)
    species_additions: dict = field(default_factory=dict)


@dataclass
class mOutputW:
    _common_base: dict
    extracted_sas: dict[Path, dict] = field(default_factory=dict)


@dataclass
class mOutputZ:
    _common_base_addition: dict
    choice_sas: dict[Path, dict] = field(default_factory=dict)


class Merger:
    def __init__(self, attached_combiner: Optional["Combiner"] = None):
        self._attached_combiner: Optional["Combiner"] = attached_combiner

    def process(self, attached_combiner: Optional["Combiner"] = None):
        self._attached_combiner = attached_combiner or self._attached_combiner
        if self._attached_combiner is None:
            raise RuntimeError
        self._process()

    def _process(self):
        _to_check: set[str] = self._attached_combiner.defined_pokemon.copy()
        _checked: set[str] = set()

        _to_check = self._attached_combiner._sort_pokemon_str(inp=_to_check)

        for pok_name in _to_check:
            ph: PackHolder = self._attached_combiner._make_pack_holder(
                pokemon_name=pok_name
            )

            if len(ph) == 1:
                if ph.has_base():
                    continue
                else:
                    pack_name = list(ph.mons.keys())[0]
                    ph.mons[pack_name].select()
                    self._attached_combiner._print_pack_choise(
                        number=ph.dex_num,
                        name=ph.name,
                        selected_pack=pack_name,
                        selection_type="ADD",
                    )
                    _checked.add(pok_name)
            else:
                Merger.merge(holder=ph)

    @staticmethod
    def merge(holder: PackHolder, _process_mods: bool = gcr_settings.PROCESS_MODS):
        merged_spawn: dict[str, Any] = Merger.merge_spawns(
            mons=list(holder.mons.values()), _process_mods=_process_mods
        )

        Merger.merge_data(holder=holder, _process_mods=_process_mods)

    @staticmethod
    def merge_spawns(
        mons: list[Pokemon], _process_mods: bool = gcr_settings.PROCESS_MODS
    ) -> dict[str, Any]:
        outp = {
            "enabled": True,
            "neededInstalledMods": set(),
            "neededUninstalledMods": set(),
            "spawns": list(),
        }
        spawns: dict[str, dict] = dict()
        path_status: dict[Path, MergeST] = dict()

        _proc_mons = [
            m
            for m in mons
            if not (
                (m.parent_pack.is_mod and (not _process_mods)) or m.parent_pack.is_base
            )
        ]
        _flat_forms = [f for m in _proc_mons for f in m.forms.values()]

        for form in _flat_forms:
            flag = False

            pok_name = form.parent_pokemon.internal_name

            for sp_path in form.spawn_pool:
                if sp_path in path_status:
                    continue
                if not (data := load_json_from_path(sp_path)):  # TODO change to bcfo data
                    continue
                flag = True

                outp["neededInstalledMods"].update(
                    data.get("neededInstalledMods", list())
                )
                outp["neededUninstalledMods"].update(
                    data.get("neededUninstalledMods", list())
                )

                for sp_entry in outp.get("spawns", list()):
                    # try: <-- add
                    entry_name = sp_entry["pokemon"].split(" ")[0]
                    if (
                        pok_name != entry_name
                    ):  # filter in case of files containing multiple pokemon
                        continue

                    sp_id: str = sp_entry["id"]
                    del sp_entry["id"]
                    if not any(
                        [
                            (sp_entry == existing_spawn)
                            for existing_spawn in spawns.values()
                        ]
                    ):
                        while True:
                            if sp_id in spawns:
                                sp_id = next_candidate_name(sp_id)
                            else:
                                break
                        spawns[sp_id] = sp_entry
            if flag:
                if form.merge_status is None:
                    form.merge_status = MergeStatus()
                form.merge_status.spawn_pool = MergeST.FULL

        outp["neededInstalledMods"] = list(outp["neededInstalledMods"])
        outp["neededUninstalledMods"] = list(outp["neededUninstalledMods"])

        for key, item in spawns:
            item["id"] = key
            outp["spawns"].append(item)

        return outp

    @staticmethod
    def merge_data(holder: PackHolder, _process_mods: bool = gcr_settings.PROCESS_MODS):
        mons = list(holder.mons.values())
        _proc_mons = [
            m
            for m in mons
            if not (
                (m.parent_pack.is_mod and (not _process_mods)) or m.parent_pack.is_base
            )
        ]
        if not _proc_mons:
            return

        _base: Optional["Pokemon"] = None
        if x := [m for m in mons if m.parent_pack.is_base]:
            _base = x[0]

        if _base is not None:
            path_to_species_index: dict[Path, dict] = dict()
            for mon in _proc_mons:
                for form in mon.forms.values():
                    spec = form.species
                    if spec is None:
                        continue
                    if spec.file_path in path_to_species_index:
                        continue
                    else:
                        path_to_species_index[spec.file_path] = spec.source
            if path_to_species_index:
                extracted_path_to_species = Merger.ex(
                    common_base=_base.forms[DefaultNames.BASE_FORM].species.source,
                    inpt_species=path_to_species_index,
                    internal_name=holder.internal_name,
                )

                pass

        # raise NotImplementedError

    @staticmethod
    def dblyou(
        inpt_species: dict[Path, dict], internal_name: str | None = None
    ) -> mOutputW:
        """Out of multiple species extract a common -BASE-"""

        _all_keys = set()
        for species in inpt_species.values():
            _all_keys.update(list(species.keys()))

        _common_base = dict()

        for c_key in _all_keys:
            if (
                len(
                    (x := set([sp[c_key] for sp in inpt_species.values() if c_key in sp]))
                )  # this is "loose" - a key can pass if it exists in a single species
                == 1
            ) and (
                all([(c_key in sp) for sp in inpt_species.values()])
                or (not gcr_settings.SPECIES_STRICT_KEY_MATCH)
            ):
                val = x[0]
                _common_base[c_key] = val

        outp = mOutputW(
            _common_base=_common_base,
            extracted_sas=Merger.ex(
                common_base=_common_base,
                inpt_species=inpt_species,
                internal_name=internal_name,
            ),
        )

        return outp

    @staticmethod
    def ex(
        common_base: dict,
        inpt_species: dict[Path, dict],
        internal_name: str | None = None,
    ) -> dict[Path, dict]:
        """From BASE and species, extract -additions-"""

        outp: dict[Path, dict] = dict()

        for sp_key, species in inpt_species.items():
            outp[sp_key] = dict()
            for c_key in common_base:
                if c_key in species:  # keys from base, that differ
                    if species[c_key] != common_base[c_key]:
                        outp[sp_key][c_key] = species[c_key]
            for c_key in species:  # keys from addition not in base
                if c_key not in common_base:  # that'd be an asshole to debug
                    outp[sp_key][c_key] = species[c_key]
            # if outp[sp_key]:
            #     if ("target" not in outp[sp_key]) and (internal_name is not None):
            #         outp[sp_key]["target"] = f"cobblemon:{internal_name}"
        return outp

    @staticmethod
    def extract_forms_against_base_pok(
        base_pok_forms_: dict[str, dict], pack_forms: dict[Path, dict[str, dict]]
    ):
        raise NotImplementedError
    
    @staticmethod
    def extract_evos_against_base_pok

    @staticmethod
    def why(
        common_base: dict,
        inpt_additions: dict[Path, dict],
    ) -> dict[Path, dict]:
        """From BASE and additions, cleanup the -additions-"""
        # aka remove common keys
        outp: dict[Path, dict] = dict()

        for sp_key, species in inpt_additions:
            outp[sp_key] = dict()
            for c_key in species:
                if not (
                    (c_key in common_base) and (common_base[c_key] == species[c_key])
                ):
                    outp[sp_key][c_key] = species[c_key]
        return outp

    @staticmethod
    def zet(inpt_additions: dict[Path, dict]):
        """From multiple additions extract a -common- and -diffs-"""
        return Merger.dblyou(inpt_species=inpt_additions)  # ....right?
