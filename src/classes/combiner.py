import json
import shutil
from pathlib import Path
from tkinter import filedialog
from typing import Any, Iterable, Literal

from utils.cli_utils.generic import line_header
from utils.cli_utils.keypress import clear_line, positive_int_choice

from classes.base_classes import (
    LangResultEntry,
)
from classes.pack import Pack
from classes.pokemon import Pokemon
from classes.pokemon_form import PokemonForm


class Combiner:
    def __init__(self, dir_name: Path | None = None):
        if (not dir_name) or (not dir_name.exists()):
            self.dir_name = Path(filedialog.askdirectory())
            if self.dir_name == Path("."):
                exit()
        else:
            self.dir_name = dir_name

        self.output_pack_path = self.dir_name / "output" / "CORE_Pack"

        self.extraction_path: str = ""

        self.pack_paths: set[Path] = set()
        self.packs: list[Pack] = list()

        self.defined_pokemon: set[str] = set()

        self._process_mods = False
        self._allow_risky_rules = True

    def run(self) -> None:
        self._prep_output_path()
        self._gather_packs()
        self._prepare()
        self._process()
        self.export()

    def _prep_output_path(self) -> None:
        try:
            if self.output_pack_path.exists():
                if self.output_pack_path.is_dir():
                    shutil.rmtree(self.output_pack_path)
        except Exception:
            print("Failed preparing output folder")
            exit()

    def export(self) -> None:
        line_header("EXPORTING")
        for pack in self.packs:
            if pack.is_base or (pack.is_mod and (not self._process_mods)):
                continue
            pack._dirty_pokedex_fix()
            pack.export(
                export_path=self.output_pack_path,
                move_leftovers=self.output_pack_path.parent,
            )

        self._export_langs(folder_path=self.output_pack_path)

        self._export_sound_json(folder_path=self.output_pack_path)

        self._write_pack_mcmeta(folder_path=self.output_pack_path)

        self._write_credits(folder_path=self.output_pack_path)

        try:
            shutil.move(
                Path("pack.png").resolve(), (self.output_pack_path / "pack.png")
            )
        except Exception:
            print("Failed to get icon..")

        self._compress_pack(folder_path=self.output_pack_path)

        self._cleanup()

    def _export_langs(self, folder_path: Path) -> None:
        res_d: dict[str, LangResultEntry] = dict()
        for p in self.packs:
            l_es: list[LangResultEntry] = p._get_lang_export()

            for entry in l_es:
                if entry.name in res_d:
                    res_d[entry.name].data.update(entry.data)
                else:
                    res_d[entry.name] = entry

        export_path = folder_path / "assets" / "cobblemon" / "lang"
        export_path.mkdir(parents=True, exist_ok=True)
        for l_entry in res_d.values():
            (export_path / l_entry.name).write_text(json.dumps(l_entry.data))

    def _export_sound_json(self, folder_path: Path):
        res = dict()
        for p in self.packs:
            res.update(p._get_sound_export())

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
                if p.pokemon[pok].selected:
                    if pok not in res:
                        res[pok] = set()
                    res[pok].add(p.name)
                    res_packs.add(p.name)

        for key in res:
            res[key] = list(res[key])

        outp_text = "Many thanks to the creators of these packs of their work"

        return (
            outp_text
            + "\n\n"
            + json.dumps(list(res_packs), indent=2)
            + "\n\n"
            + json.dumps(res, indent=3)
        )

    def _get_pack_mcmeta(self) -> dict[str, dict[str, Any]]:
        return {"pack": {"pack_format": 15, "description": "CORE Test"}}

    def _write_pack_mcmeta(self, folder_path: Path) -> None:
        mc = self._get_pack_mcmeta()
        (folder_path / "pack.mcmeta").write_text(json.dumps(mc))

    def _compress_pack(self, folder_path: Path) -> None:
        shutil.make_archive(str(folder_path), format="zip", root_dir=str(folder_path))

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
        line_header("PREPARING")
        self.extraction_path = self.dir_name / ".temp"
        self.extraction_path.mkdir(parents=True, exist_ok=True)
        for p in self.packs:
            p._extraction_path = self.extraction_path

        for p in self.packs:
            p._prepare()
            print("")

        self._remove_empty_packs()

        for p in self.packs:
            p.parent_combiner = self

        if len(["_" for p in self.packs if p.is_base]) > 1:
            raise RuntimeError("Multiple [BASE] type packs present.")

    def _remove_empty_packs(self) -> None:
        for p in self.packs:
            if not bool(p.component_location):
                self.packs.remove(p)

    # ------------------------------------------------------------

    def _process(self) -> None:
        line_header("PROCESSING")

        for p in self.packs:
            p._process()

        for p in self.packs:
            self.defined_pokemon.update(list(p.pokemon.keys()))

        line_header("RESOLVING")

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

    def _resolution_greedy(self) -> None:
        _to_check: set[str] = self.defined_pokemon.copy()
        _checked: set[str] = set()

        _to_check = self._sort_pokemon_str(inp=_to_check)

        for p_name in _to_check:
            if sum([1 for p in self.packs if (p_name in p.pokemon)]) == 1:
                holder, num, name = self._make_pack_holder(p_name)
                pack, sel_type = self._single_simple_add(holder=holder)
                holder[pack].select()
                self._print_pack_choise(
                    number=num, name=name, selected_pack=pack, selection_type=sel_type
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
                    holder, num, name = self._make_pack_holder(p_name)

                    flag = False
                    selected_key: str = ""
                    selection_type: str = ""
                    for check in _avail_checks:
                        if not flag:
                            selected_key, selection_type = check(holder=holder)
                            flag: bool = selected_key is not None
                    if flag:
                        _checked.add(p_name)
                        holder[selected_key].select()
                        self._print_pack_choise(
                            number=num,
                            name=name,
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
                    holder, num, name = self._make_pack_holder(p_name)

                    self._choose_pack(holder=holder, number=num, name=name)
                    _to_check.remove(
                        p_name
                    )  # TODO IS this dangerous? editing but also breaking
                    break
        self._greedy_step_rest(remaining=_to_check)

    def _greedy_step_rest(self, remaining: set[str]) -> None:
        _to_check: set[str] = remaining.copy()

        _to_check = self._sort_pokemon_str(inp=_to_check)

        for p_name in _to_check:
            holder, num, name = self._make_pack_holder(p_name)
            self._choose_pack(holder=holder, number=num, name=name)

    def _make_pack_holder(
        self, pokemon_name: str
    ) -> tuple[dict[str, Pokemon], int, str]:
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
        return holder, d_num, d_name

    def _resolution_core(self) -> None:
        line_header("RESOLVING")
        for pok_name in self.defined_pokemon:
            self._resolution_pokemon(pokemon_name=pok_name)

    def _resolution_pokemon(self, pokemon_name: str) -> None:
        temp_holder, d_num, d_name = self._make_pack_holder(pokemon_name=pokemon_name)

        flag = False
        selected_key: str = ""
        selection_type: str = ""

        checks = [self._single_simple_add, self._dual_choice]
        for check in checks:
            if not flag:
                selected_key, selection_type = check(holder=temp_holder)
                flag = selected_key is not None

        if flag:
            self._print_pack_choise(
                number=d_num,
                name=d_name,
                selected_pack=selected_key,
                selection_type=selection_type,
            )
        else:
            self._choose_pack(holder=temp_holder, number=d_num, name=d_name)

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
        b_patch = holder[mod_key].forms["base_form"].comp_stamp
        o_patch = holder[other_key].forms["base_form"].comp_stamp

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
        fb = holder[mod_key].forms["base_form"]
        fo = holder[other_key].forms["base_form"]

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
            ][0].forms["base_form"]
            fo: PokemonForm = [
                p
                for p in holder.values()
                if not (p.parent_pack.is_base or p.parent_pack.is_mod)
            ][0].forms["base_form"]

            for _check in [
                self._dual_choice_mod_and_remodel,
                self._dual_choice_mod_and_pack_addition,
                self._dual_choice_mod_and_species,
                self._dual_choice_mod_w_g_and_spawn,
                self._dual_choice_mod_and_req_pack,
                self._dual_choice_mod_and_req_pack_2,
                self._dual_choice_mod_remodel,
                self._dual_choice_card,
                self._dual_choice_card_2,
                self._dual_choice_card_3,
            ]:
                pack, stype = _check(pok_mod=fm, pok_other=fo)
                if pack is not None:
                    return (pack, stype)
        return (None, None)

    def _dual_choice_mod_and_remodel(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G"]] | tuple[None, None]:
        if (pok_mod.has_spawn() and pok_mod.has_species_data()) and (
            (not pok_other.has_spawn())
            and (not pok_other.has_species_data())
            and pok_other.is_graphically_complete()
        ):
            return (pok_other.parent_pack.name, "G")
        return (None, None)

    def _dual_choice_mod_and_pack_addition(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G2"]] | tuple[None, None]:
        if (not pok_mod.has_graphics()) and pok_other.is_graphically_complete():
            return (pok_other.parent_pack.name, "G2")
        return (None, None)

    def _dual_choice_mod_and_species(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G3-R"]] | tuple[None, None]:
        if pok_other.is_species() and self._allow_risky_rules:
            return (pok_other.parent_pack.name, "G3-R")

        return (None, None)

    def _dual_choice_mod_w_g_and_spawn(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G4-R"]] | tuple[None, None]:
        if self._allow_risky_rules:
            if (
                (
                    pok_mod.is_graphically_complete()
                    and pok_other.is_graphically_complete()
                )
                and (pok_mod.has_sp_data() and (not pok_other.has_sp_data()))
                and ((not pok_mod.has_spawn()) and pok_other.has_spawn())
            ):
                return (pok_other.parent_pack.name, "G4-R")

        return (None, None)

    def _dual_choice_mod_and_req_pack(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5-R"]] | tuple[None, None]:
        if self._allow_risky_rules:
            if pok_mod.is_complete() and (
                (not pok_other.has_graphics()) and (pok_other.is_requested())
            ):
                return (pok_other.parent_pack.name, "G5-R")
        return (None, None)

    def _dual_choice_mod_and_req_pack_2(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5b-R"]] | tuple[None, None]:
        if self._allow_risky_rules:
            if pok_mod.is_complete() and (
                (pok_other.has_graphics())
                and (pok_other.is_requested())
                and pok_other.has_spawn()
                and (not pok_other.has_sp_data())
            ):
                return (pok_other.parent_pack.name, "G5b-R")
        return (None, None)

    def _dual_choice_mod_remodel(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5c-R"]] | tuple[None, None]:
        if pok_mod.is_complete() and (
            (not pok_other.has_spawn())
            and (not pok_other.has_sp_data() and pok_other.is_graphically_complete())
        ):
            return (pok_other.parent_pack.name, "G5c-R")
        return (None, None)

    def _dual_choice_card(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD"]] | tuple[None, None]:
        if (
            pok_mod.is_complete()
            and pok_mod.parent_pack.is_base
            and (not pok_other.has_spawn())
            and (not pok_other.has_sp_data())
            and (not pok_other.is_graphically_complete())
        ):
            return (pok_mod.parent_pack.name, "CARD")
        return (None, None)

    def _dual_choice_card_2(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD2"]] | tuple[None, None]:
        if (
            pok_mod.parent_pack.is_base
            and (not pok_mod.has_spawn())
            and (not pok_mod.has_graphics())
            and (pok_other.comp_stamp[4:] == [True, False, False, True, True])
        ):
            return (pok_other.parent_pack.name, "CARD2")
        return (None, None)

    def _dual_choice_card_3(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD3"]] | tuple[None, None]:
        if (
            pok_mod.parent_pack.is_base
            and (pok_mod.is_graphically_complete())
            and (not pok_other.has_spawn())
            and (not pok_other.has_sp_data())
            and (pok_other.comp_stamp[4:] == [True, False, False, True, True])
        ):
            return (pok_mod.parent_pack.name, "CARD3")
        return (None, None)

    def _print_pack_choise(
        self, number: int, name: str, selected_pack: str, selection_type: str = "M"
    ) -> None:
        x = [p for p in self.packs if p.name == selected_pack][0]
        if (x.is_base and (selection_type in ["A"])) or (
            (x.is_mod and (not x.is_base)) and (not self._process_mods)
        ):
            return

        print(f"-- AUTO [{selection_type}] -- \n#{number} - {name}  [{selected_pack}]")

        print("=" * 25)

    def _choose_pack(self, holder: dict[str, Pokemon], number: int, name: str):
        print(f"#{number} - {name}")

        keys = list(holder.keys())

        for i, k in enumerate(keys):
            pack_name = k
            p = holder[pack_name]
            outp = repr(p)
            out_parts = outp.split("\n")
            out_parts[0] = f"{i+1}. {pack_name}"
            outp = "\n".join(out_parts)
            print(outp)

        while True:
            k_in = positive_int_choice(
                max_ch=(len(keys) + 1),
                text="Pack choice:   [#].Pack  [E]xit",
            )
            if k_in:
                break
            else:
                print(f"\033[A\r{' '*40}\r", end="")

        selected_key = keys[k_in - 1]
        holder[selected_key].select()
        print(f"\033[A\r{' '*40}\r", end="")
        print(f"- {k_in}. [{selected_key}]")
        print("=" * 25)

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
