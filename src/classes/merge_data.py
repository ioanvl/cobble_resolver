from __future__ import annotations

import copy
import json
import random
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from classes.base_classes import PackHolder
from classes.pokemon import MergePokemon
from constants.runtime_const import gcr_settings
from constants.text_constants import DefaultNames
from utils.cli_utils.keypress import clear_line, keypress
from utils.dict_utils import combine
from utils.dict_utils_transitive import compare
from utils.get_resource import load_json_from_path
from utils.text_utils import bcolors, cprint, next_candidate_name

if TYPE_CHECKING:
    from classes.combiner.combiner import Combiner
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


@dataclass
class mOutputW:
    _common_base: dict
    extracted_sas: dict[Any, dict] = field(default_factory=dict)


@dataclass
class MergeDataOutput:
    extracted_path_to_additions: dict[tuple[Path | None, Path | None], dict]
    extracted_base: dict | None = None


@dataclass
class MergePackHolder:
    original_holder: PackHolder
    merged_spawn_data: dict[str, Any]
    extracted_addition: MergeDataOutput | None
    choice_options: None | list[str]

    auto_pick: bool = False
    pick: str | None = None


@dataclass
class mOutputZ:
    _common_base_addition: dict
    choice_sas: dict[Path, dict] = field(default_factory=dict)


class Merger:
    def __init__(self, attached_combiner: Optional["Combiner"] = None):
        self._attached_combiner: Optional["Combiner"] = attached_combiner

        self._mons_to_move: dict[str, PackHolder] = dict()
        self._mons_to_merge: dict[str, MergePackHolder] = dict()

        self.merged_mons: dict[str, MergePokemon] = dict()

    def process(self, attached_combiner: Optional["Combiner"] = None):
        self._attached_combiner = attached_combiner or self._attached_combiner
        if self._attached_combiner is None:
            raise RuntimeError
        self._process()
        self._merge_final_pokemon()

        self._export_mons()
        # self._attached_combiner.export()

        # _ = input("--break--")

    def _merge_final_pokemon(self):
        for pok_name, merge_holder in self._mons_to_merge.items():
            print(pok_name)

            if all(
                [
                    k in merge_holder.original_holder._get_unprocessable_keys()
                    for k in merge_holder.original_holder.mons.keys()
                ]
            ):
                pass

            extras: set[str] = set(merge_holder.original_holder.mons.keys())
            extras.difference(set([merge_holder.pick]))
            extras.difference(set(merge_holder.original_holder._get_unprocessable_keys()))

            # pick = merge_holder.pick if (merge_holder.pick is not None) else None
            pick_mon = (
                merge_holder.original_holder.mons[merge_holder.pick]
                if merge_holder.pick is not None
                else None
            )

            if DefaultNames.BASE_COBBLE_MOD in merge_holder.original_holder.mons:
                _species_base = (
                    merge_holder.original_holder.mons[DefaultNames.BASE_COBBLE_MOD]
                    .forms[DefaultNames.BASE_FORM]
                    .species.source
                )
            else:
                _species_base = merge_holder.extracted_addition.extracted_base

            extra_sas = list()
            for ex in extras:
                if ex_sa := merge_holder.original_holder.mons[ex]._extracted_sa:
                    extra_sas.append(ex_sa)
            _final_species = self._merge_species_with_sas(
                species=_species_base,
                species_additions=extra_sas,
                overwrite=False,
                include=True,
            )

            # _merged_extras_sa = self._extract_against_common(
            #     common_base=_species_base,
            #     inpt_species={0: _merged_extras_sa},
            # )[0]

            if pick_mon:
                if (not pick_mon.parent_pack.is_base) or (
                    pick_mon.parent_pack.is_mod and (not gcr_settings.PROCESS_MODS)
                ):
                    _final_species = self._merge_species_with_sas(
                        species=_final_species,
                        species_additions=[pick_mon._extracted_sa],
                        overwrite=True,
                        include=True,
                    )

            # _final_sa["target"] = f"cobblemon:{pok_name}"
            if gcr_settings.POKEDEX_FIX:
                _final_species["implemented"] = True
                if pick_mon:
                    if pick_mon.is_pseudoform and gcr_settings.EXCLUDE_PSEUDOFORMS:
                        _final_species["implemented"] = False

            outp = MergePokemon(
                internal_name=pok_name,
                name=merge_holder.original_holder.name,
                dex_id=merge_holder.original_holder.dex_num,
                picked_mon=pick_mon,
                extra_mons=extras,
                holder=merge_holder.original_holder,
                # species_addition=_final_sa,
                spawn_pool=merge_holder.merged_spawn_data,
                species_base=_final_species,
            )
            # if (
            #     DefaultNames.BASE_COBBLE_MOD not in merge_holder.original_holder.mons
            # ) and (
            #     (
            #         not any(
            #             [
            #                 p.parent_pack.is_mod
            #                 for p in merge_holder.original_holder.mons.values()
            #             ]
            #         )
            #     )
            #     and (not gcr_settings.PROCESS_MODS)
            # ):
            #     outp.species_base = merge_holder.extracted_addition.extracted_base
            self.merged_mons[pok_name] = outp

    def _export_mons(self, target_path: Path | None = None):
        if target_path is None:
            target_path = self._attached_combiner.output_pack_path

        for pok_name, merge_mon in self.merged_mons.items():
            # move _other_ sounds first, _then_ we ll overwrite with selected
            for s_mon in merge_mon.holder.mons.values():
                if s_mon.parent_pack.is_base or (
                    s_mon.parent_pack.is_mod and (not gcr_settings.PROCESS_MODS)
                ):
                    continue
                sound_set: set[Path] = set()
                if (merge_mon.picked_mon is not None) and (s_mon is merge_mon.picked_mon):
                    continue
                for s_form in s_mon.forms.values():
                    if s_form.sound_entry is not None:
                        sound_set.update(s_form.sound_entry.get_all_files())
                Merger._move_path_set_to_target(
                    path_set=sound_set,
                    target_path=target_path,
                    relative_to=s_mon.parent_pack.folder_location,
                )

            pok_path_set: set[Path] = set()
            if merge_mon.picked_mon is not None:
                if (merge_mon.picked_mon.parent_pack.is_base) or (
                    merge_mon.picked_mon.parent_pack.is_mod
                    and (not gcr_settings.PROCESS_MODS)
                ):
                    # skip graphics
                    pass
                else:
                    for resv in merge_mon.picked_mon.resolvers.values():
                        pok_path_set.update(resv.get_all_paths())
                    for form in merge_mon.picked_mon.forms.values():
                        if (sd := form.sound_entry) is not None:
                            pok_path_set.update(sd.get_all_files())
                    pok_path_set.update(
                        merge_mon.picked_mon._get_relevant_feature_files()
                    )

                Merger._move_path_set_to_target(
                    path_set=pok_path_set,
                    target_path=target_path,
                    relative_to=merge_mon.picked_mon.parent_pack.folder_location,
                )
                # for p in pok_path_set:
                #     if p:
                #         if p.is_dir():
                #             print(
                #                 f"[er] - {p}"
                #             )  # TODO sometimes a "cobblemon\sounds\pokemon"
                #             continue  # appears here and fucks things up
                #         np = target_path / p.relative_to(
                #             merge_mon.picked_mon.parent_pack.folder_location
                #         )
                #         np.parent.mkdir(parents=True, exist_ok=True)
                #         try:
                #             shutil.move(p, np)
                #         except Exception:
                #             if np.exists():
                #                 pass
                #             else:
                #                 print(f"WARN: missed file: {(str(np))[:-25]}")
                #                 pass

            gen = merge_mon.holder._get_generation()
            if not gen:
                gen = "custom"
            else:
                gen = f"generation{gen}"

            data_path = target_path / "data" / "cobblemon"
            if merge_mon.species_base is not None:
                sp_path = data_path / "species" / gen / f"{pok_name}.json"
                sp_path.parent.mkdir(parents=True, exist_ok=True)
                sp_path.write_text(json.dumps(merge_mon.species_base, indent=6))
            if merge_mon.species_addition is not None:
                sp_path = data_path / "species_additions" / gen / f"{pok_name}.json"
                sp_path.parent.mkdir(parents=True, exist_ok=True)
                sp_path.write_text(json.dumps(merge_mon.species_addition, indent=6))
            if merge_mon.spawn_pool is not None:
                sp_path = (
                    data_path
                    / "spawn_pool_world"
                    / f"{(int(merge_mon.dex_id)):04d}_{pok_name}.json"
                )
                sp_path.parent.mkdir(parents=True, exist_ok=True)
                sp_path.write_text(json.dumps(merge_mon.spawn_pool, indent=6))

                pass

    @staticmethod
    def _move_path_set_to_target(
        path_set: set[Path], target_path: Path, relative_to: Path
    ):
        for p in path_set:
            if p:
                if p.is_dir():
                    print(f"[er] - {p}")  # TODO sometimes a "cobblemon\sounds\pokemon"
                    continue  # appears here and fucks things up
                np = target_path / p.relative_to(relative_to)
                np.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(p, np)
                except Exception:
                    if np.exists():
                        pass
                    else:
                        print(f"WARN: missed file: {(str(np))[:-25]}")
                        pass

    def _process(self):
        _to_check: set[str] = self._attached_combiner.defined_pokemon.copy()
        # _checked: set[str] = set()

        _needs_choice: dict[str, MergeDataOutput] = dict()

        _to_check = self._attached_combiner._sort_pokemon_str(inp=_to_check)

        for pok_name in list(_to_check):  # [::-1]:
            ph: PackHolder = self._attached_combiner._make_pack_holder(
                pokemon_name=pok_name
            )

            if pok_name in ["indeedee", "pyroar", "irontreads"]:
                pass  # TODO debug

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
                    # _checked.add(pok_name)
                    self._mons_to_move[pok_name] = ph
            else:
                merge_data: MergePackHolder = Merger.merge(holder=ph)

                if (merge_data.choice_options is None) or (
                    len(merge_data.choice_options) == 1
                ):
                    pack_name = (
                        merge_data.choice_options[0]
                        if merge_data.choice_options is not None
                        else None
                    )
                    self._attached_combiner._print_pack_choise(
                        number=ph.dex_num,
                        name=ph.name,
                        selected_pack=pack_name,
                        selection_type=cprint(text="===MERGE==", color=bcolors.WARNING),
                    )
                    # _checked.add(pok_name)
                    if pack_name is not None:
                        ph.mons[pack_name].merge_pick = True
                    merge_data.auto_pick = True
                    merge_data.pick = pack_name
                else:
                    _needs_choice[pok_name] = merge_data

                for _m_mon in ph.mons.values():
                    _m_mon.merged = True

                self._mons_to_merge[pok_name] = merge_data

        self.make_pack_choices(mon_packs=_needs_choice)

    def make_pack_choices(self, mon_packs: dict[str, MergePackHolder]):
        for pok_name, merge_holder in mon_packs.items():
            disp, keys = merge_holder.original_holder._display(
                color=True, only_graphics=True, exclude_merged=True, show_merged=True
            )
            print(disp, end="\n\n")
            if True:  # for debugging purposes
                _err = None
                while True:
                    print(clear_line, end="")
                    if _err is not None:
                        print(f"Invalid choice: [{_err}]")
                    inp = keypress("Input pack choice Num[#]: ")
                    if _err is not None:
                        print(clear_line, end="")
                    try:
                        inp = int(inp)
                    except Exception:
                        _err = inp
                        continue
                    if inp > 0 and inp <= len(keys):
                        break
                    else:
                        _err = inp
                if _err is not None:
                    print(clear_line)
                print(clear_line, end="")

                pick = keys[inp - 1]
            else:
                pick = keys[random.randrange(0, len(keys))]

            print(cprint(f"={'-'*15}", color=bcolors.WARNING))
            print(f"Selected: [{pick}]")
            print(cprint(f"={'-'*15}", color=bcolors.WARNING))
            print("=" * 25)

            merge_holder.pick = pick

            self._mons_to_merge[pok_name] = merge_holder

    @staticmethod
    def merge(holder: PackHolder, _process_mods: bool = gcr_settings.PROCESS_MODS):
        merged_spawn: dict[str, Any] = Merger.merge_spawns(
            mons=list(holder.mons.values()), _process_mods=_process_mods
        )
        path_to_species_index: None | MergeDataOutput = Merger.merge_data(
            holder=holder, _process_mods=_process_mods
        )
        options: None | list[str] = Merger.decide_from_viable_picks(mon_holder=holder)

        return MergePackHolder(
            original_holder=holder,
            merged_spawn_data=merged_spawn,
            extracted_addition=path_to_species_index,
            choice_options=options,
        )

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
            # if not (
            #     (m.parent_pack.is_mod and (not _process_mods)) or m.parent_pack.is_base
            # )   #TODO check- I THINK thats a better approach?..
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

                for sp_entry in data.get("spawns", list()):
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

        for key, item in spawns.items():
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
            return None

        _base: Optional["Pokemon"] = None
        if x := [m for m in mons if m.parent_pack.is_base]:
            _base = x[0]

        _extracted_base: mOutputW | None = None
        if _base is not None:
            _base_form_species = _base.forms[DefaultNames.BASE_FORM].species.source

            extracted_path_to_species: dict[tuple[Path | None, Path | None], dict] = (
                Merger._extract_mons_data_from_common(
                    base_form=_base_form_species, mons=_proc_mons
                )
            )

        else:
            _inp_species = dict()
            for mon in mons:
                for form in mon.forms.values():
                    if (form.species is not None) and (
                        form.species.file_path not in _inp_species
                    ):
                        _inp_species[form.species.file_path] = form.species.source
            _extracted_base = Merger._make_common_and_extract(
                inpt_species=_inp_species,
                inclussive=False,
            )
            extracted_path_to_species: dict[tuple[Path | None, Path | None], dict] = (
                Merger._extract_mons_data_from_common(
                    base_form=_extracted_base._common_base,
                    mons=_proc_mons,
                    pre_extracted_species=_extracted_base.extracted_sas,
                )
            )

        Merger.assign_merge_scores(
            extracted_data=extracted_path_to_species, mons=_proc_mons
        )

        return MergeDataOutput(
            extracted_base=_extracted_base._common_base if _extracted_base else None,
            extracted_path_to_additions=extracted_path_to_species,
        )

    @staticmethod
    def decide_from_viable_picks(mon_holder: PackHolder) -> None | list[str]:
        _g_keys = mon_holder._get_graphics_keys()

        if not _g_keys:
            return None
        else:
            return _g_keys

    @staticmethod
    def assign_merge_scores(extracted_data: dict[Any, dict], mons: list["Pokemon"]):
        __ignored_keys = ["target", "dex_id", "evolutions", "forms"]
        if gcr_settings.COMBINE_POKEMON_MOVES:
            __ignored_keys.append("moves")
        for mon in mons:
            for form in mon.forms.values():
                full_flag = False
                key = form.get_species_paths_key()
                if (key[0] is None) and (key[1] is None):
                    continue
                _data = extracted_data[key]

                if form.name == DefaultNames.BASE_FORM:
                    if all([(k in __ignored_keys) for k in _data]):
                        full_flag = True
                else:
                    _forms = [
                        f for f in _data.get("forms", list()) if f["name"] == form.name
                    ]
                    if not _forms:
                        full_flag = True
                    else:
                        _form = _forms[0]
                        if all([(k in __ignored_keys) for k in _form]):
                            full_flag = True
                if form.species is not None:
                    form.merge_status.species = (
                        MergeST.FULL
                        if (full_flag or (form.species_additions is not None))
                        else MergeST.PARTIAL
                    )
                if form.species_additions is not None:
                    form.merge_status.species_additions = (
                        MergeST.FULL if full_flag else MergeST.PARTIAL
                    )

    @staticmethod
    def _extract_mons_data_from_common(
        base_form: dict,
        mons: list["Pokemon"],
        pre_extracted_species: dict[Path, dict] | None = None,
    ):
        path_to_species_index: dict[Path, dict] = dict()
        extracted_path_to_species = dict()
        for mon in mons:
            mon_form_keys = set()

            for form in mon.forms.values():
                key = form.get_species_paths_key()

                if (key in path_to_species_index) or (
                    (key[0] is None) and (key[1] is None)
                ):
                    continue

                if (key[0] is not None) and (key[1] is not None):
                    _temp = form.species.source
                    if pre_extracted_species is not None:
                        _key = form.species.file_path
                        if _key in pre_extracted_species:
                            _temp = pre_extracted_species[_key]

                    path_to_species_index[key] = Merger._merge_species_with_sas(
                        species=_temp,
                        species_additions=[form.species_additions.source],
                        overwrite=True,
                        include=True,
                    )
                else:
                    if form.species is not None:
                        _temp = form.species.source
                        if pre_extracted_species is not None:
                            _key = form.species.file_path
                            if _key in pre_extracted_species:
                                _temp = pre_extracted_species[_key]
                    else:
                        _temp = form.species_additions.source
                    path_to_species_index[key] = _temp
                mon_form_keys.add(key)

        if path_to_species_index:
            extracted_path_to_species = Merger._extract_against_common(
                common_base=base_form,
                inpt_species=path_to_species_index,
            )

            for mon in mons:
                mon_form_keys = set()
                for form in mon.forms.values():
                    mon_form_keys.add(form.get_species_paths_key())
                _final_sa = dict()
                if mon_form_keys:
                    mon_sa = [
                        _fin_sa
                        for _fo_key, _fin_sa in path_to_species_index.items()
                        if _fo_key in mon_form_keys
                    ]
                    if mon_sa:  # avoid (None, None)
                        _final_sa = Merger._merge_species_with_sas(
                            species=dict(),
                            species_additions=mon_sa,
                            overwrite=True,  # shouldnt matter
                            include=True,
                        )
                mon._extracted_sa = _final_sa
        return extracted_path_to_species

    @staticmethod
    def _make_common_and_extract(
        inpt_species: dict[Any, dict],
        inclussive: bool | None = None,
    ) -> mOutputW:  # inclusive etc - and then change the if bellow
        """Out of multiple species extract a common -BASE-"""

        _all_keys = set()
        for species in inpt_species.values():
            _all_keys.update(list(species.keys()))

        _common_base = dict()

        for c_key in _all_keys:
            if all([(c_key in sp) for sp in inpt_species.values()]) or (
                inclussive or (not gcr_settings.SPECIES_STRICT_KEY_MATCH)
            ):
                val = [sp[c_key] for sp in inpt_species.values() if c_key in sp]
                if compare(*val, loose=True):
                    _common_base[c_key] = val[0]

        outp = mOutputW(
            _common_base=_common_base,
            extracted_sas=Merger._extract_against_common(
                common_base=_common_base,
                inpt_species=inpt_species,
            ),
        )

        return outp

    @staticmethod
    def _extract_against_common(
        common_base: dict,
        inpt_species: dict[Any, dict],
        exclude_existing: bool = False,
    ) -> dict[Any, dict]:
        """From BASE and species, extract -additions-"""

        _special_form_keys = ["forms", "evolutions"]
        outp: dict[Any, dict] = dict()

        for sp_key, species in inpt_species.items():
            outp[sp_key] = dict()

            for c_key in species:  # keys from addition not in base
                if c_key in _special_form_keys:
                    continue
                if c_key in common_base and exclude_existing:
                    continue
                if (c_key not in common_base) or (
                    not compare(species[c_key], common_base[c_key], loose=True)
                ):  # that'd be an asshole to debug
                    outp[sp_key][c_key] = species[c_key]
        # ------------------------------------------------------------------------
        paths_to_evos = Merger.extract_evos_against_base_pok(
            base_pok_evos=common_base.get("evolutions", list()),
            sp_evos={
                in_p: in_data.get("evolutions", list())
                for in_p, in_data in inpt_species.items()
            },
        )
        for e_path, e_dict in paths_to_evos.items():
            if not e_dict:
                continue
            for ev_id, ev_data in e_dict.items():
                ev_data["id"] = ev_id
            outp[e_path]["evolutions"] = [ev for ev in e_dict.values()]
        # ------------------------------------------------------------------------
        paths_to_forms = Merger.extract_forms_against_base_pok(
            base_pok_forms=common_base.get("forms", list()),
            pack_forms={
                in_p: in_data.get("forms", list())
                for in_p, in_data in inpt_species.items()
            },
        )
        for f_path, f_list in paths_to_forms.items():
            if not f_list:
                continue
            outp[f_path]["forms"] = f_list

        return outp

    @staticmethod
    def extract_forms_against_base_pok(
        base_pok_forms: list[dict], pack_forms: dict[Path, list[dict]]
    ) -> dict[Path, list[dict]]:
        _base_forms: dict[str, dict] = dict()
        for form in base_pok_forms:
            _base_forms[form["name"]] = form
        _sp_forms: dict[Path, list[dict]] = dict()

        for f_path, _forms in pack_forms.items():
            _sp_forms[f_path] = list()

            if compare(_forms, base_pok_forms, loose=True):
                continue
            for _form in _forms:
                _f_name = _form["name"]
                if not (
                    (_f_name in _base_forms)
                    and compare(_base_forms[_f_name], _form, loose=True)
                ):
                    _sp_forms[f_path].append(_form)

        return _sp_forms

    @staticmethod
    def extract_evos_against_base_pok(
        base_pok_evos: list[dict], sp_evos: dict[Path, list[dict]]
    ) -> dict[Path, dict[str, dict]]:
        _base_ev: dict[str, dict] = dict()
        _sp_evs: dict[Path, dict[str, dict]] = dict()

        _registered_ids: set[str] = set()

        for ev in base_pok_evos:
            if (ev_id := ev.get("id", None)) is None:
                continue
            ev_data = copy.deepcopy(ev)
            del ev_data["id"]
            _base_ev[ev_id] = ev_data

        _registered_ids.update(list(_base_ev.keys()))

        for sp_key, sp_pok in sp_evos.items():
            _sp_evs[sp_key] = dict()
            for ev in sp_pok:
                if (ev_id := ev.get("id", None)) is None:
                    continue
                ev_data = copy.deepcopy(ev)
                del ev_data["id"]

                if not any(
                    [compare(val, ev_data, loose=True) for val in _base_ev.values()]
                ):
                    while True:
                        if ev_id in _registered_ids:
                            ev_id = next_candidate_name(ev_id)
                        else:
                            _registered_ids.add(ev_id)
                            break
                    _sp_evs[sp_key][ev_id] = ev_data

        return _sp_evs

    @staticmethod
    def _merge_species_with_sas(
        species: dict,
        species_additions: list[dict],
        overwrite: bool = True,
        include: bool = True,
    ):
        _special_form_keys = ["forms", "evolutions"]
        _outp = {x: y for x, y in species.items()}

        _all_keys = list(
            set([key for sp_ad in species_additions for key in sp_ad.keys()])
        )

        _all_keys = sorted(
            _all_keys, key=lambda x: (-sum([(x in sp_ad) for sp_ad in species_additions]))
        )

        for key in _all_keys:
            if (
                (key in _special_form_keys)
                or ((key in species) and (not overwrite))
                or ((key not in species) and (not include))
            ):
                continue

            vals = [x[key] for x in species_additions if key in x]
            if key in species:
                vals.insert(0, species[key])
            if compare(*vals, loose=True):
                _outp[key] = vals[0]
            elif (key == "moves") and gcr_settings.COMBINE_POKEMON_MOVES:
                _temp_out = set()
                _temp_out.update(species.get("moves", list()))
                for _v in vals:
                    _temp_out.update(_v)
                _outp[key] = list(_temp_out)
            else:
                try:
                    _most_common = max(set(vals), key=vals.count)
                    _outp[key] = _most_common
                except TypeError:
                    if include:
                        if isinstance(vals[0], (list, set, dict)):
                            _outp[key] = combine(*vals)
                        else:
                            _outp[key] = vals[0]
                    else:
                        if overwrite:
                            _outp[key] = vals[0]

        # ------------------------------------------------------------------------
        _outp["forms"] = Merger._merge_forms_with_form_additions(
            species=species.get("forms", list()),
            species_additions=[sa.get("forms", list()) for sa in species_additions],
            overwrite=overwrite,
            include=include,
        )
        # ------------------------------------------------------------------------
        _outp["evolutions"] = Merger._merge_evolutions_with_form_additions(
            species=species.get("evolutions", list()),
            species_additions=[sa.get("evolutions", list()) for sa in species_additions],
            overwrite=False,
            include=True,
        )
        # ------------------------------------------------------------------------
        return _outp

    @staticmethod
    def _merge_evolutions_with_form_additions(
        species: list,
        species_additions: list[list[dict]],
        overwrite: bool = False,
        include: bool = True,
    ):
        _outp: dict[str, dict] = dict()
        for evo in species:
            _outp[evo["id"]] = copy.deepcopy(evo)
            del _outp[evo["id"]]["id"]
        for sp in species_additions:
            for evo in sp:
                temp = copy.deepcopy(evo)
                id = temp["id"]
                del temp["id"]
                if id in _outp:
                    if overwrite:
                        _outp[id] = temp
                    else:
                        if include:
                            flag = False
                            for _out_evo in _outp.values():
                                if compare(temp, _out_evo):
                                    flag = True
                                    break
                            if not flag:
                                while True:
                                    if id in _outp:
                                        id = next_candidate_name(id)
                                    else:
                                        _outp[id] = temp
                                        break
                else:
                    if include:
                        _outp[id] = temp
        for _id, evo in _outp.items():
            evo["id"] = _id
        return list(_outp.values())

    @staticmethod
    def _merge_forms_with_form_additions(
        species: list,
        species_additions: list[list[dict]],
        overwrite: bool = False,
        include: bool = True,
    ) -> list:
        _base_forms = {form["name"]: form for form in species}
        _all_forms: dict[str, list[dict]] = dict()
        for __form_list in species_additions:
            for __sp_form in __form_list:
                f_name = __sp_form["name"]
                if f_name not in _all_forms:
                    _all_forms[f_name] = list()
                _all_forms[f_name].append(__sp_form)

        for _key, forms in _all_forms.items():
            if (not include) and (_key not in _base_forms):
                continue
            if _key in _base_forms:
                if not overwrite:
                    continue
                else:
                    # TODO: maybe remove if animation/behavior problems?
                    _base_forms[_key] = Merger._merge_species_with_sas(
                        species=_base_forms[_key],
                        species_additions=forms,
                        overwrite=overwrite,
                        include=include,
                    )
            else:
                _base_forms[_key] = Merger._merge_species_with_sas(
                    species=dict(),
                    species_additions=forms,
                    overwrite=overwrite,
                    include=include,
                )
        return list(_base_forms.values())

    # ------------------------------------------------------------------------
    pass
    # ------------------------------------------------------------------------
