from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from classes.base_classes import PackHolder
from constants.runtime_const import gcr_settings
from constants.text_constants import DefaultNames
from utils.dict_utils_transitive import compare
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
    extracted_sas: dict[Any, dict] = field(default_factory=dict)


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

        _ = input("--break--")

    def _process(self):
        _to_check: set[str] = self._attached_combiner.defined_pokemon.copy()
        _checked: set[str] = set()

        _to_check = self._attached_combiner._sort_pokemon_str(inp=_to_check)

        for pok_name in list(_to_check)[::-1]:  # TODO CHANGE THIS BACK !!!!!!!!!!!!!
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
                print(ph, end="")
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
            _base_form_species = _base.forms[DefaultNames.BASE_FORM].species.source

            extracted_path_to_species = Merger._extract_mons_data_from_common(
                base_form=_base_form_species, mons=_proc_mons
            )

            # path_to_species_index: dict[Path, dict] = dict()
            # for mon in _proc_mons:
            #     for form in mon.forms.values():
            #         key = form.get_species_paths_key()

            #         if (key in path_to_species_index) or (
            #             (key[0] is None) and (key[1] is None)
            #         ):
            #             continue

            #         if (key[0] is not None) and (key[1] is not None):
            #             path_to_species_index[key] = Merger._merge_species_with_sas(
            #                 species=form.species.source,
            #                 species_additions=[form.species_additions.source],
            #             )
            #         else:
            #             path_to_species_index[key] = (
            #                 form.species.source
            #                 if form.species is not None
            #                 else form.species_additions.source
            #             )

            # if path_to_species_index:
            #     extracted_path_to_species = Merger._extract_against_common(
            #         common_base=_base_form_species,
            #         inpt_species=path_to_species_index,
            #         internal_name=holder.internal_name,
            #     )

            #   pass

    @staticmethod
    def _extract_mons_data_from_common(base_form: dict, mons: list["Pokemon"]):
        path_to_species_index: dict[Path, dict] = dict()
        extracted_path_to_species = dict()
        for mon in mons:
            for form in mon.forms.values():
                key = form.get_species_paths_key()

                if (key in path_to_species_index) or (
                    (key[0] is None) and (key[1] is None)
                ):
                    continue

                if (key[0] is not None) and (key[1] is not None):
                    path_to_species_index[key] = Merger._merge_species_with_sas(
                        species=form.species.source,
                        species_additions=[form.species_additions.source],
                    )
                else:
                    path_to_species_index[key] = (
                        form.species.source
                        if form.species is not None
                        else form.species_additions.source
                    )

        if path_to_species_index:
            extracted_path_to_species = Merger._extract_against_common(
                common_base=base_form,
                inpt_species=path_to_species_index,
            )
        return extracted_path_to_species

    @staticmethod
    def _make_common_and_extract(
        inpt_species: dict[Any, dict],
        internal_name: str | None = None,
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
                internal_name=internal_name,
            ),
        )

        return outp

    @staticmethod
    def _extract_against_common(
        common_base: dict,
        inpt_species: dict[Any, dict],
        internal_name: str | None = None,
    ) -> dict[Any, dict]:
        """From BASE and species, extract -additions-"""

        _special_form_keys = ["forms", "evolutions"]
        outp: dict[Path, dict] = dict()

        for sp_key, species in inpt_species.items():
            outp[sp_key] = dict()

            for c_key in species:  # keys from addition not in base
                if c_key in _special_form_keys:
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
        overwrite: bool = False,
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
            if compare(*vals, loose=True):
                _outp[key] = vals[0]
            else:
                _most_common = max(set(vals), key=vals.count)
                _outp[key] = _most_common
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
            overwrite=overwrite,
            include=include,
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
