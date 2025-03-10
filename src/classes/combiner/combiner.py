import json
import shutil
from pathlib import Path
from tkinter import filedialog
from typing import Any, Iterable, Literal

from classes.base_classes import LangResultEntry, PackHolder
from classes.merge_data import Merger
from classes.pack import Pack
from classes.pokemon import Pokemon
from classes.pokemon_form import PokemonForm
from constants.runtime_const import gcr_settings, settings_menu
from constants.text_constants import DefaultNames, HelperText
from utils.cli_utils.generic import display_help_menu, line_header, pack_name_choice
from utils.cli_utils.keypress import clear, clear_line, keypress, positive_int_choice
from utils.cli_utils.reorder_list import reorder_menu
from utils.get_resource import get_resource_path
from utils.text_utils import bcolors, c_text

from .choice_rules import DualChoise_Risky, DualChoise_Simple


class Combiner:
    def __init__(self, dir_name: Path | None = None):
        self.extraction_path: str = ""

        self.pack_paths: set[Path] = set()
        self.packs: list[Pack] = list()

        self.defined_pokemon: set[str] = set()

        # -----------------------

        if (not dir_name) or (not dir_name.exists()):
            if gcr_settings.AUTO_START:
                dir_name = self._get_working_dir()
                if dir_name is None:
                    exit()
                else:
                    self.dir_name = dir_name
            else:
                self._menu()
        else:
            self.dir_name = dir_name

        self.output_pack_path = self.dir_name / "output" / "CORE_Pack"

        # -----------------------

        self._process_mods = False
        self._allow_risky_rules = True

        self.__helper_message_displayed = False

        self._load_order: list = list()

    def run(self) -> None:
        self._prep_output_path()
        self._gather_packs()
        self._prepare()
        self._process()
        self.export()
        self._cleanup()

    def _prep_output_path(self) -> None:
        try:
            if self.output_pack_path.exists():
                if self.output_pack_path.is_dir():
                    shutil.rmtree(self.output_pack_path)
        except Exception:
            print("Failed preparing output folder")
            exit()

    def export(self) -> None:
        line_header("Exporting")
        for pack in self.packs:
            if pack.is_base or (pack.is_mod and (not self._process_mods)):
                continue
            if gcr_settings.POKEDEX_FIX:
                pack._dirty_pokedex_fix()
            pack.export(
                export_path=self.output_pack_path,
                move_leftovers=self.output_pack_path.parent,
            )

        self._export_langs(folder_path=self.output_pack_path)

        self._export_sound_json(folder_path=self.output_pack_path)

        self._write_pack_mcmeta(folder_path=self.output_pack_path)

        self._write_credits(folder_path=self.output_pack_path)

        self._get_icon()

        self._compress_pack(folder_path=self.output_pack_path)

    def _get_icon(self) -> None:
        try:
            _icon = (
                DefaultNames.ALT_ICON
                if gcr_settings.ALTERNATE_ICON
                else DefaultNames.ICON_NAME
            )
            icon_path = Path(get_resource_path(f"src/images/{_icon}.png"))
            shutil.copy(
                icon_path,
                (self.output_pack_path / "pack.png"),
            )
        except Exception as e:
            print(f"Failed to get icon: {e}")

    def _export_langs(self, folder_path: Path) -> None:
        res_d: dict[str, LangResultEntry] = dict()
        _accounted_merge_picks: set[str] = set()
        for p in self.packs[::-1]:
            if p.is_base or (p.is_mod and (not gcr_settings.PROCESS_MODS)):
                continue
            l_es: list[LangResultEntry] = p._get_lang_export()

            for entry in l_es:
                if entry.name not in res_d:
                    res_d[entry.name] = LangResultEntry(name=entry.name, data=dict())

                for l_key, l_entry in entry.data.items():
                    if l_key.startswith("cobblemon.species."):
                        _name_attempts: set[str] = set()
                        l_name = l_key.split(".")[2]
                        if l_name not in p.pokemon:
                            _name_attempts.add(l_name)
                            l_name = "".join(l_name.split("_"))
                        if l_name not in p.pokemon:
                            _name_attempts.add(l_name)
                            l_name, aspect = p._extract_name_and_aspect(
                                full_pokemon_string=l_key.split(".")[2],
                                available_features=p.features,
                            )
                        if l_name not in p.pokemon:
                            _name_attempts.add(l_name)
                            l_name = "".join(l_name.split("_"))

                        _selected_att = None
                        if l_name not in p.pokemon:
                            _name_attempts.add(l_name)
                            for _attempt_pok in p.pokemon.values():
                                if _attempt_pok.internal_name in _name_attempts:
                                    _selected_att = _attempt_pok
                                    break
                                for _att_form in _attempt_pok.forms.values():
                                    if _att_form.species is not None:
                                        if (
                                            _att_form.species.source.get(
                                                "name", ""
                                            ).lower()
                                        ) in _name_attempts:
                                            _selected_att = _attempt_pok
                                            break
                                    if _att_form.species_additions is not None:
                                        _name_parts = (
                                            _att_form.species_additions.source.get(
                                                "target", "_:_"
                                            ).lower()
                                        ).split(":")
                                        if len(_name_parts) > 1:
                                            __att_name = _name_parts[1]
                                        else:
                                            __att_name = _name_parts[0]
                                        if __att_name in _name_attempts:
                                            _selected_att = _attempt_pok
                                            break
                                if _selected_att is not None:
                                    break
                            if _selected_att is None:
                                if gcr_settings.SHOW_WARNINGS:
                                    print(
                                        c_text(
                                            f"--! Found unmatched language entry: {l_key}",
                                            color=bcolors.WARNING,
                                        )
                                    )
                            # if f"{entry.name}_{l_key}" not in _accounted_merge_picks:
                            #     res_d[entry.name].data[l_key] = l_entry

                        _selected_pok = None
                        if l_name in p.pokemon:
                            _selected_pok = p.pokemon[l_name]
                        elif _selected_att is not None:
                            _selected_pok = _selected_att

                        if _selected_pok is not None:
                            if (_selected_pok.merged and _selected_pok.merge_pick) or (
                                _selected_pok.selected
                            ):
                                res_d[entry.name].data[l_key] = l_entry
                                _accounted_merge_picks.add(f"{entry.name}_{l_key}")
                        else:
                            if f"{entry.name}_{l_key}" not in _accounted_merge_picks:
                                res_d[entry.name].data[l_key] = l_entry

                    else:
                        res_d[entry.name].data[l_key] = l_entry

        export_path = folder_path / "assets" / "cobblemon" / "lang"
        export_path.mkdir(parents=True, exist_ok=True)
        for l_entry in res_d.values():
            (export_path / l_entry.name).write_text(json.dumps(l_entry.data, indent=4))

    def _export_sound_json(self, folder_path: Path):
        res = dict()
        _accounted_merge_picks: set[str] = set()
        for p in self.packs[::-1]:
            if p.is_base or (p.is_mod and (not gcr_settings.PROCESS_MODS)):
                continue
            for s_pok in p.pokemon.values():
                if s_pok.selected:
                    res.update(s_pok.get_sound_export())
                if s_pok.merged:
                    pok_sounds = s_pok.get_sound_export()
                    if s_pok.merge_pick:
                        res.update(pok_sounds)
                        _accounted_merge_picks.update(list(pok_sounds.keys()))
                    else:
                        for s_key, s_entry in pok_sounds.items():
                            if s_key not in _accounted_merge_picks:
                                res[s_key] = s_entry

        (folder_path / "assets" / "cobblemon" / "sounds.json").write_text(
            json.dumps(res, indent=4)
        )

    def _write_credits(self, folder_path: Path) -> None:
        (folder_path / "credits.txt").write_text(self._create_credits())

    def _create_credits(self) -> str:
        res: dict[str, Iterable[str]] = dict()
        res_packs: set[str] = set()
        for p in self.packs:
            if (p.name == "BASE") or (p.is_mod and (not self._process_mods)):
                continue
            for pok in p.pokemon:
                if (p.pokemon[pok].selected) or p.pokemon[pok].merged:
                    if pok not in res:
                        res[pok] = set()
                    res[pok].add(p.name)
                    res_packs.add(p.name)

        for key in res:
            res[key] = list(res[key])

        outp_text = "Many thanks to the creators of these packs for their work"

        return (
            outp_text
            + "\n\n"
            + json.dumps(list(res_packs), indent=2)
            + "\n\n"
            + json.dumps(res, indent=3)
        )

    def _get_pack_mcmeta(self) -> dict[str, dict[str, Any]]:
        return {"pack": {"pack_format": 15, "description": self._get_description()}}

    def _get_description(self):
        return "Combined pack created with CobblemonResolver"

    def _write_pack_mcmeta(self, folder_path: Path) -> None:
        mc = self._get_pack_mcmeta()
        (folder_path / "pack.mcmeta").write_text(json.dumps(mc))

    def _compress_pack(self, folder_path: Path) -> None:
        for _ in range(3):
            try:
                shutil.make_archive(
                    str(folder_path.parent / DefaultNames.FINAL_PACK_NAME),
                    format="zip",
                    root_dir=str(folder_path),
                )
                break
            except Exception:
                _ = input(
                    "Packaging failed.. If you have the pack open, \
    from a previous attempt please close it and retry.. Press [Enter] to retry"
                )

    # ------------------------------------------------------------

    def _gather_packs(self) -> None:
        accepted_formats = [".zip", ".jar"]
        for f_path in self.dir_name.iterdir():
            if (
                f_path.is_dir() and f_path.stem != ".temp"
            ) or f_path.suffix in accepted_formats:
                self.pack_paths.add(f_path)
                self.packs.append(
                    Pack(
                        folder_location=f_path if f_path.is_dir() else None,
                        zip_location=None if f_path.is_dir() else f_path,
                    )
                )

    # ------------------------------------------------------------

    def _prepare(self) -> None:
        line_header("Preparing")
        self.extraction_path = self.dir_name / ".temp"
        self.extraction_path.mkdir(parents=True, exist_ok=True)
        for p in self.packs:
            if p:
                try:
                    p._extraction_path = self.extraction_path
                    p._prepare()
                    print("")
                except Exception as e:
                    print("\n\n")
                    print(f"{c_text(f"{'='*40}", color=bcolors.FAIL)}")

                    print(f"Fatal error unpacking [{p.get_name()}] - ignoring pack.")
                    print(f"\nError msg ->\n {e or '[missing]'}")

                    print(f"{c_text(f"{'='*40}", color=bcolors.FAIL)}")

                    p.component_location = None

        self._remove_empty_packs()

        for p in self.packs:
            p.parent_combiner = self

        if len(["_" for p in self.packs if p.is_base]) > 1:
            raise RuntimeError("Multiple [BASE] type packs present.")

        # get load order if exists
        _lo_path = self.dir_name / "_load_order.json"
        if _lo_path.exists():
            try:
                self._load_order = json.loads(_lo_path.read_text())
            except Exception:
                pass

        self._menu()

        self._reorder_packs()

    def _menu(self):
        _prep_flag = bool(self.packs)
        while True:
            clear()
            line_header("CobbleResolver")

            if _prep_flag:
                print("[S]tart\n")
                print("[L]oad Order")
            else:
                print("[S]elect working folder\n")

            print("[O]ptions\n")
            print("[H]elp\n")
            print(f"[{'ESC/' if not _prep_flag else ''}E]xit\n")

            _inp = keypress("Enter option:..").lower()

            if _inp == "e" or ((_inp == "esc") and (not _prep_flag)):
                exit()
            elif _inp == "s":
                if _prep_flag:
                    return
                else:
                    if (x := self._get_working_dir()) is not None:
                        self.dir_name = x
                        clear()
                        return
            elif _inp == "l" and _prep_flag:
                self._edit_load_order()
            elif _inp == "o":
                settings_menu(gcr_settings)
            elif _inp == "h":
                display_help_menu()

    def _get_working_dir(self) -> None | Path:
        dir_name = Path(filedialog.askdirectory())
        if dir_name == Path("."):
            return None
        else:
            return dir_name

    def _edit_load_order(self) -> None:
        _load_order = self._load_order or [_pack.name for _pack in self.packs]
        _load_order = [
            _l for _l in _load_order if _l in [_pack.name for _pack in self.packs]
        ]
        for _p in self.packs:
            if _p.name not in _load_order:
                _load_order.append(_p.name)

        if (new_order := reorder_menu(_load_order)) is not None:
            self._load_order = new_order

        if self._load_order:
            _lo_path = self.dir_name / "_load_order.json"
            _lo_path.write_text(json.dumps(self._load_order, indent=3))

    def _reorder_packs(self) -> None:
        if self._load_order is None:
            return
        _new_order_list = list()
        for _name in self._load_order:
            _temp = [pack for pack in self.packs if pack.name == _name]
            if not _temp:
                # maybe old load order?
                if gcr_settings.SHOW_WARNINGS:
                    print(c_text(f"--! Invalid entry in load order: {_name}"))
                continue
            for i in _temp:
                _new_order_list.append(i)
        _unordered = [pack for pack in self.packs if pack not in _new_order_list]
        for i in _unordered:
            _new_order_list.append(i)
        if len(_new_order_list) != len(self.packs):
            raise RuntimeError

        self.packs = _new_order_list

    def _remove_empty_packs(self) -> None:
        flag = False
        for p in self.packs:
            if (not isinstance(p, Pack)) or (not bool(p.component_location)):
                print(c_text(text=f"{p.get_name()} - ignored.", color=bcolors.FAIL))
                flag = True
                self.packs.remove(p)
        if flag:
            _ = input("\n\nPress [Enter] to continue..")

    # ------------------------------------------------------------

    def _process(self) -> None:
        line_header("Processing")

        for p in self.packs:
            p._process()

        for p in self.packs:
            self.defined_pokemon.update(list(p.pokemon.keys()))

        line_header("Resolving")

        if gcr_settings.OP_MODE.value:
            self._merge_v_a()
        else:
            # self._resolution_core()
            self._resolution_greedy()

    def _sort_pokemon_str(self, inp: Iterable[str]):
        return sorted(
            inp,
            key=lambda x: (
                sum([1 for p in self.packs if (x in p.pokemon)]),
                -(
                    int(
                        any(
                            [
                                (p.pokemon[x]._is_actively_requested())
                                for p in self.packs
                                if (x in p.pokemon)
                            ]
                        )
                    )
                ),
                -(
                    max(
                        [
                            (
                                (p.pokemon[x]._remaining_requests())
                                if p.pokemon[x]._is_actively_requested()
                                else 0
                            )
                            for p in self.packs
                            if (x in p.pokemon)
                        ]
                    )
                ),
                max([p.pokemon[x].evos for p in self.packs if (x in p.pokemon)]),
                (
                    max([p.pokemon[x].pre_evos for p in self.packs if (x in p.pokemon)])
                    + max([p.pokemon[x].evos for p in self.packs if (x in p.pokemon)])
                ),
            ),
        )

    def _merge_v_a(self):
        merger = Merger(attached_combiner=self)
        merger.process()

    def _resolution_greedy(self) -> None:
        _to_check: set[str] = self.defined_pokemon.copy()
        _checked: set[str] = set()

        _to_check = self._sort_pokemon_str(inp=_to_check)

        for p_name in _to_check:
            if sum([1 for p in self.packs if (p_name in p.pokemon)]) == 1:
                ph: PackHolder = self._make_pack_holder(pokemon_name=p_name)

                pack, sel_type = self._single_simple_add(holder=ph.mons)
                ph.mons[pack].select()
                self._print_pack_choise(
                    number=ph.dex_num,
                    name=ph.name,
                    selected_pack=pack,
                    selection_type=sel_type,
                )
                _checked.add(p_name)
        for i in _checked:
            _to_check.remove(i)
        self._greedy_step_double(remaining=_to_check)

    def _greedy_step_double(self, remaining: set[str]) -> None:
        _avail_checks = [self._dual_choice]
        _to_check: set[str] = remaining.copy()

        _to_check = self._sort_pokemon_str(inp=_to_check)

        while True:
            _num_flag = False
            _checked: set[str] = set()
            for p_name in _to_check:
                if sum([1 for p in self.packs if (p_name in p.pokemon)]) == 2:
                    _num_flag = True
                    ph: PackHolder = self._make_pack_holder(pokemon_name=p_name)

                    flag = False
                    selected_key: str = ""
                    selection_type: str = ""
                    for check in _avail_checks:
                        if not flag:
                            selected_key, selection_type = check(holder=ph.mons)
                            flag: bool = selected_key is not None
                    if flag:
                        _checked.add(p_name)
                        ph.mons[selected_key].select()
                        self._print_pack_choise(
                            number=ph.dex_num,
                            name=ph.name,
                            selected_pack=selected_key,
                            selection_type=selection_type,
                        )
            if not _num_flag:
                break
            for i in _checked:
                _to_check.remove(i)
            _checked = set()

            for p_name in _to_check:
                if (
                    sum([1 for p in self.packs if (p_name in p.pokemon)]) == 2
                ):  # TODO fuckin optimize this, for the love of god
                    self._choose_pack(
                        pack_holder=self._make_pack_holder(pokemon_name=p_name)
                    )
                    _to_check.remove(
                        p_name
                    )  # TODO IS this dangerous? editing but also breaking
                    break
        self._greedy_step_rest(remaining=_to_check)

    def _greedy_step_rest(self, remaining: set[str]) -> None:
        _to_check: set[str] = remaining.copy()

        _to_check = self._sort_pokemon_str(inp=_to_check)

        for p_name in _to_check:
            self._choose_pack(pack_holder=self._make_pack_holder(pokemon_name=p_name))

    def _make_pack_holder(self, pokemon_name: str) -> PackHolder:
        holder: dict[str, Pokemon] = dict()

        d_num: int = 0
        d_name: str = ""

        for pack in self.packs:
            if pokemon_name in pack.pokemon.keys():
                holder[pack.name] = pack.pokemon[pokemon_name]
                if (holder[pack.name].dex_id != -1) and (not d_num) and (not d_name):
                    d_num = holder[pack.name].dex_id
                    d_name = holder[pack.name].name
        if not d_name:
            d_name = (
                list(holder.values())[0].name
                or f"[{list(holder.values())[0].internal_name}]"
            )
        return PackHolder(
            mons=holder, dex_num=d_num, name=d_name, internal_name=pokemon_name
        )

    def _resolution_core(self) -> None:
        line_header("Resolving")
        for pok_name in self.defined_pokemon:
            self._resolution_pokemon(pokemon_name=pok_name)

    def _resolution_pokemon(self, pokemon_name: str) -> None:
        ph: PackHolder = self._make_pack_holder(pokemon_name=pokemon_name)

        flag = False
        selected_key: str = ""
        selection_type: str = ""

        checks = [self._single_simple_add, self._dual_choice]
        for check in checks:
            if not flag:
                selected_key, selection_type = check(holder=ph.mons)
                flag = selected_key is not None

        if flag:
            self._print_pack_choise(
                number=ph.dex_num,
                name=ph.name,
                selected_pack=selected_key,
                selection_type=selection_type,
            )
        else:
            self._choose_pack(pack_holder=ph)

    def _single_simple_add(
        self, holder: dict[str, Pokemon]
    ) -> tuple[str, Literal["A"]] | tuple[None, None]:
        if len(holder) == 1:
            selected_key = list(holder.keys())[0]
            holder[selected_key].select()
            return (selected_key, "A")
        return (None, None)

    def _dual_choice(
        self, holder: dict[str, Pokemon]
    ) -> tuple[str, str] | tuple[None, None]:
        if len(holder) == 2:
            if "BASE" in holder:
                pack, stype = self._dual_choice_against_base(holder=holder)
                if pack is not None:
                    return (pack, stype)

            for _check in [
                self._dual_choice_only_mods_ignore,
                self._dual_choice_mod_and_pack,
            ]:
                pack, stype = _check(holder=holder)
                if pack is not None:
                    return (pack, stype)
        return (None, None)

    def _dual_choice_against_base(
        self, holder: dict[str, Pokemon]
    ) -> tuple[Literal["R"], str] | tuple[None, None]:
        keys = list(holder.keys())
        keys.remove("BASE")
        other_key = keys[0]

        for _ckeck in [
            self._dual_choice_against_base_add,
            self._dual_choice_against_base_add_spawn,
        ]:
            pack, stype = _ckeck(holder=holder, other_key=other_key)
            if pack is not None:
                return (pack, stype)
        return (None, None)

    def _dual_choice_against_base_add(
        self, holder: dict[str, Pokemon], other_key: str, mod_key: str = "BASE"
    ) -> tuple[str, Literal["R"]] | tuple[None, None]:
        b_patch = holder[mod_key].forms[DefaultNames.BASE_FORM].comp_stamp
        o_patch = holder[other_key].forms[DefaultNames.BASE_FORM].comp_stamp

        if ((not b_patch[0]) and o_patch[0]) and (
            ((not b_patch[3]) and o_patch[3])
            or ((not all(b_patch[4:])) and (all(o_patch[4:])))
        ):
            holder[other_key].select()
            return (other_key, "R")
        return (None, None)

    def _dual_choice_against_base_add_spawn(
        self, holder: dict[str, Pokemon], other_key: str, mod_key: str = "BASE"
    ) -> tuple[str, Literal["R"]] | tuple[None, None]:
        fb = holder[mod_key].forms[DefaultNames.BASE_FORM]
        fo = holder[other_key].forms[DefaultNames.BASE_FORM]

        if (
            (not fb.has_spawn())
            and (fb.has_graphics())
            and fo.has_spawn()
            and (not fo.has_graphics())
        ):
            holder[other_key].select()
            return (other_key, "R")
        return (None, None)

    def _dual_choice_only_mods_ignore(
        self, holder: dict[str, Pokemon]
    ) -> tuple[str, Literal["I"]] | tuple[None, None]:
        if (
            all(
                [
                    (p.parent_pack.is_base or p.parent_pack.is_mod)
                    for p in holder.values()
                ]
            )
        ) and (not self._process_mods):
            return (list(holder.keys())[0], "I")
        return (None, None)

    def _dual_choice_mod_and_pack(
        self, holder: dict[str, Pokemon]
    ) -> tuple[str, str] | tuple[None, None]:
        if (
            sum(
                [
                    (p.parent_pack.is_base or p.parent_pack.is_mod)
                    for p in holder.values()
                ]
            )
            == 1
        ):
            fm: PokemonForm = [
                p
                for p in holder.values()
                if (p.parent_pack.is_base or p.parent_pack.is_mod)
            ][0].forms[DefaultNames.BASE_FORM]
            fo: PokemonForm = [
                p
                for p in holder.values()
                if not (p.parent_pack.is_base or p.parent_pack.is_mod)
            ][0].forms[DefaultNames.BASE_FORM]

            for _check in [
                DualChoise_Simple._dual_choice_mod_and_remodel,
                DualChoise_Simple._dual_choice_mod_and_pack_addition,
                DualChoise_Risky._dual_choice_mod_and_species,
                DualChoise_Risky._dual_choice_mod_w_g_and_spawn,
                DualChoise_Risky._dual_choice_mod_and_req_pack,
                DualChoise_Risky._dual_choice_mod_and_req_pack_2,
                DualChoise_Simple._dual_choice_mod_remodel,
                DualChoise_Simple._dual_choice_card,
                DualChoise_Simple._dual_choice_card_2,
                DualChoise_Simple._dual_choice_card_3,
            ]:
                pack, stype = _check(pok_mod=fm, pok_other=fo)
                if pack is not None:
                    return (pack, stype)
        return (None, None)

    def _print_pack_choise(
        self,
        number: int,
        name: str,
        selected_pack: str | None,
        selection_type: str = "M",
    ) -> None:
        if selected_pack is not None:
            x = [p for p in self.packs if p.name == selected_pack][0]
            if (x.is_base and (selection_type in ["A"])) or (
                (x.is_mod and (not x.is_base)) and (not self._process_mods)
            ):
                return

        print(f"-- AUTO [{selection_type}] -- \n#{number} - {name}  [{selected_pack}]")

        print("=" * 25)

    def _choose_pack(self, pack_holder: PackHolder):
        if not self.__helper_message_displayed and (
            gcr_settings.SHOW_HELPER_TEXT and not gcr_settings.AUTO_LOAD_ORDER_MODE
        ):
            print(HelperText.AUTO_MANUAL_CHOISE)
            _ = input("Press [Enter] to continue..")
            print(clear_line, end="")
            self.__helper_message_displayed = True

        mons: dict[str, Pokemon] = pack_holder.mons
        keys = list(mons.keys())

        if gcr_settings.AUTO_LOAD_ORDER_MODE:
            print(str(pack_holder), end="")
            while True:
                k_in = positive_int_choice(
                    max_ch=(len(keys) + 1),
                    text="Pack choice:   [Num.#] Pack",
                )
                if k_in:
                    break
                else:
                    print(f"\033[A\r{' '*40}\r", end="")

            selected_key = keys[k_in - 1]
            print(clear_line, end="")
            print("=" * 25)
        else:
            selected_key = keys[0]

        mons[selected_key].select()
        pack_name_choice(selected_key)
        self._print_pack_choise(
            number=pack_holder.dex_num,
            name=pack_holder.name,
            selected_pack=selected_key,
            selection_type=c_text(text="=AUTO LOAD ORDER=", color=bcolors.WARNING),
        )

    def _is_selected(self, pokemon_name: str) -> bool:
        return bool(
            sum(
                [
                    p.pokemon[pokemon_name].selected
                    for p in self.packs
                    if (pokemon_name in p.pokemon)
                ]
            )
        )

    # ------------------------------------------------------------

    def _cleanup(self) -> None:
        try:
            print("Deleting temporary folder")
            shutil.rmtree(str(self.dir_name / ".temp"))
        except Exception:
            print(f"{clear_line} -Could not remove temporary folder")
        print(clear_line, end="")
        try:
            print("Deleting intermefite folder")
            shutil.rmtree(self.output_pack_path)
        except Exception:
            print(f"{clear_line} -Could not remove intermediate folder")
        print(clear_line, end="")
