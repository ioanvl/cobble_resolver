from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from utils.get_resource import load_json_from_path
from utils.text_utils import bcolors, next_candidate_name

if TYPE_CHECKING:
    from classes.pokemon import Pokemon


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


class Merger:
    @staticmethod
    def merge_spawns(mons: list[Pokemon], _process_mods: bool = False) -> dict[str, Any]:
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
    def merge_data(mons: list[Pokemon], _process_mods: bool = False):
        _proc_mons = [
            m
            for m in mons
            if not (
                (m.parent_pack.is_mod and (not _process_mods)) or m.parent_pack.is_base
            )
        ]

        _base = None
        if x := [m for m in mons if m.parent_pack.is_base]:
            _base = x[0]

        if _base is not None:
            Merger.extract_sas(base_mon=_base, pack_mons=_proc_mons)

        raise NotImplementedError

    @staticmethod
    def extract_sas(base_mon: Pokemon, pack_mons: list[Pokemon]):
        raise NotImplementedError
