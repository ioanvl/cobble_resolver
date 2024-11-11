from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import TYPE_CHECKING

from classes.base_classes import (
    Feature,
    FeatureAssignment,
    FeatureType,
    LangEntry,
    LangResultEntry,
    bcfo,
)
from classes.evolutions import EvolutionCollection, EvolutionEntry
from classes.pack.poser_parser import PoserResolver
from classes.pokemon import Pokemon
from classes.pokemon_form import PokemonForm, ResolverEntry
from classes.sounds import SoundPack
from constants.generic import default_animation_types
from constants.runtime_const import DEBUG, gcr_settings
from constants.text_constants import DefaultNames, TextSymbols
from utils.cli_utils.generic import bool_square
from utils.cli_utils.keypress import clear_line
from utils.directory_utils import clear_empty_dir
from utils.safe_parse_deco import safe_parse_per_file
from utils.text_utils import next_candidate_name

if TYPE_CHECKING:
    from classes.combiner import Combiner


@dataclass
class PackLocations:
    home_location: Path | None = None

    resolvers: set[Path] = field(default_factory=set)
    models: set[Path] = field(default_factory=set)
    textures: Path | None = None
    animations: set[Path] = field(default_factory=set)
    posers: set[Path] = field(default_factory=set)

    sounds: Path | None = None
    sound_jsons: set[Path] = field(default_factory=set)

    lang: Path | None = None

    species: set[Path] = field(default_factory=set)
    species_additions: set[Path] = field(default_factory=set)
    spawn_pool_world: set[Path] = field(default_factory=set)
    species_features: set[Path] = field(default_factory=set)
    species_features_assignments: set[Path] = field(default_factory=set)

    posers_dict: dict[str, Path] = field(default_factory=dict)
    models_dict: dict[str, Path] = field(default_factory=dict)
    textures_dict: dict[str, Path] = field(default_factory=dict)

    def __repr__(self) -> str:
        res: str = ""
        res += f"Sp:{bool_square(self.spawn_pool_world)} "
        res += f"S:{bool_square(self.species)} "
        res += f"SA:{bool_square(self.species_additions)} | "

        res += f"F:{bool_square(self.species_features)} "
        res += f"FA:{bool_square(self.species_features_assignments)} | "

        res += f"R:{bool_square(self.resolvers)} "
        res += f"M:{bool_square(self.models)} "
        res += f"T:{bool_square(self.textures)} "
        res += f"P:{bool_square(self.posers)} "
        res += f"A:{bool_square(self.animations)} "
        return res

    def __bool__(self) -> bool:
        return (
            bool(self.resolvers)
            or bool(self.models)
            or bool(self.animations)
            or bool(self.posers)
            or (self.textures is not None)
            or (self.lang is not None)
            or bool(self.species)
            or bool(self.species_additions)
            or bool(self.spawn_pool_world)
            or bool(self.species_features)
            or bool(self.species_features_assignments)
        )

    def _delete_registered_paths(self) -> None:
        for x in [
            self.lang,
            self.textures,
        ]:
            if x and x.exists() and x.is_dir():
                shutil.rmtree(x)
        for y in [
            self.animations,  #
            self.models,  #
            self.posers,  #
            self.resolvers,  #
            self.species,
            self.species_additions,
            self.spawn_pool_world,
            self.species_features,
            self.species_features_assignments,
        ]:
            for x in y:
                if x and x.exists() and x.is_dir():
                    shutil.rmtree(x)


class Pack:
    def __init__(
        self,
        zip_location: Path | None = None,
        folder_location: Path | None = None,
        _extraction_path: Path | None = None,
    ) -> None:
        self.zip_location: Path | None = zip_location
        self.folder_location: Path | None = folder_location
        self._extraction_path: Path | None = _extraction_path

        self.component_location: PackLocations | None

        self.name: str = ""

        self.pokemon: dict[str, Pokemon] = dict()
        self.features: dict[str, Feature] = dict()
        self.feature_assignments: list[FeatureAssignment] = list()

        self.defined_animation_types: set[str] = set()
        self.present_animations: dict[str, dict[str, set[Path]]] = dict()
        self.accessed_animations: set[str] = set()

        self.sounds: SoundPack | None = None

        self.lang_entries: list[LangEntry] = list()
        self.registered_evolutions: EvolutionCollection = EvolutionCollection()

        self.is_base: bool = False
        self.is_mod: bool = False

        self.parent_combiner: "Combiner" | None = None
        self.verbose: bool = False

    def run(self) -> None:
        self._prepare()
        self._process()

    # ============================================================

    def get_all_pack_paths(self) -> None:
        path_set: set[Path] = set()
        for p in self.pokemon.values():
            path_set.update(p.get_all_paths())
        for f in self.features.values():
            path_set.add(f.file_path)
        for f in self.feature_assignments:
            path_set.add(f.file_path)
        for x in self.present_animations:
            for y in self.present_animations[x]:
                path_set.update(self.present_animations[x][y])
        for le in self.lang_entries:
            path_set.add(le.file_path)
        path_set.update(self.sounds.get_all_files())
        return path_set

    def export(
        self,
        export_path: Path | None = None,
        selected: bool = True,
        export_mods: bool = False,
        move_leftovers: Path | None = None,
    ):
        outut_name: str = f"{self.name}_CORE"
        if not export_path:
            output_path: Path = self.folder_location.parent / outut_name
        else:
            output_path = export_path

        output_path.mkdir(parents=True, exist_ok=True)

        _overall_set = self.get_all_pack_paths()

        # -----------------------------------------
        path_set: set[Path] = set()
        delete_set: set[Path] = set()
        mflag = self.is_base or self.is_mod
        if (not mflag) or (mflag and export_mods):
            for pok in self.pokemon.values():
                if pok.selected or (not selected):
                    path_set.update(pok.get_all_export_paths())
                # else:
                #     delete_set.update(pok.get_all_export_paths())

            # for fa in self.feature_assignments:  #TODO....maybe?
            #     path_set.add(fa.file_path)

        # delete_set = delete_set.difference(path_set)

        delete_set = _overall_set.difference(path_set)

        c = 0
        for p in path_set:
            if p:
                if p.is_dir():
                    print(f"[e] - {p}")  # TODO sometimes a "cobblemon\sounds\pokemon"
                    continue  # appears here and fucks things up
                np = output_path / p.relative_to(self.folder_location)
                np.parent.mkdir(parents=True, exist_ok=True)

                if np.exists() and (
                    (
                        (
                            (np.parent == "species_additions")
                            or (np.parent.parent == "species_additions")
                        )
                        and gcr_settings.KEEP_DUPLICATE_SAS_ON_MOVE
                    )
                    or (
                        (
                            (np.parent == "spawn_pool_world")
                            or (np.parent.parent == "spawn_pool_world")
                        )
                        and gcr_settings.KEEP_DUPLICATE_SPAWNS_ON_MOVE
                    )
                ):
                    while True:
                        candidate_name = np.stem
                        candidate_name = next_candidate_name(candidate_name)
                        if not (
                            np := (np.parent / f"{candidate_name}.{np.suffix}")
                        ).exists():
                            break

                try:
                    shutil.move(p, np)
                except Exception as e:
                    if np.exists():
                        pass
                    else:
                        raise e
                c += 1
        # -----------------------------------------
        if not export_path:
            self._export_langs()

        # -----------------------------------------
        del_flag = False
        try:
            for p in delete_set:
                if p and p.exists():
                    p.unlink()

            self.component_location._delete_registered_paths()
            clear_empty_dir(
                s_path=self.folder_location,
                items_to_delete=[
                    "__MACOSX",
                    ".DS_Store",
                    "desktop.ini",
                    "READ ME.txt",
                    "README.txt",
                ],
            )
            del_flag = True
        except PermissionError:
            print(f"Could not exclude unused files for {self.name}")
            if move_leftovers:
                print("-Partial pack will not be produced")
            del_flag = False
        # -----------------------------------------
        # for p_i in ["pack.png", "pack.mcmeta"]:
        #     if (p := (self.folder_location / p_i)).exists():
        #         p.unlink()

        mv_count = 0
        if isinstance(move_leftovers, Path) and del_flag:
            mv_count = self._move_leftovers(export_path=move_leftovers)

        outp = f"{c} Moved "
        if d := (len(path_set) - c):
            outp += f"- {d} Missed "
        if mv_count:
            outp += f"| {mv_count} Repackaged "
        if d := (len(delete_set)):
            outp += f"| {d} Excluded "
        outp += f"|| {self.name}"
        print(outp)

    def _move_leftovers(self, export_path: Path) -> int | None:
        if x := (len([i for i in self.folder_location.rglob("*") if i.is_dir()])):
            shutil.make_archive(
                f"{str((export_path / f"[ce]_{self.name}"))}",
                format="zip",
                root_dir=str(self.folder_location),
            )
            return x

    def _export_langs(self, export_path: Path) -> None:
        langs = self._get_lang_export()
        l_path = export_path / "assets" / "cobblemon" / "lang"
        l_path.mkdir(parents=True, exist_ok=True)
        for l_entry in langs:
            (l_path / f"{l_entry.name}").write_text(json.dumps(l_entry.data))

    def _get_lang_export(self) -> list[LangResultEntry]:
        selected = [
            p
            for p in self.pokemon
            if (self.pokemon[p].selected or self.pokemon[p].merged)
        ]
        not_selected = [
            p
            for p in self.pokemon
            if ((not self.pokemon[p].selected) and (not self.pokemon[p].merged))
        ]

        res = list()
        for lang in self.lang_entries:
            res_d: dict[str, str] = dict()

            sk = [p for p in lang.incl_pokemon if p in selected]
            dk = [p for p in lang.incl_pokemon if p in not_selected]
            selected_keys = [
                k
                for k in lang.source.keys()
                if ((len(k.split(".")) > 2) and (k.split(".")[2] in sk))
            ]
            deselected_keys = [
                k
                for k in lang.source.keys()
                if ((len(k.split(".")) > 2) and (k.split(".")[2] in dk))
            ]

            for k in selected_keys:
                res_d[k] = lang.source[k]

            for k in lang.source.keys():
                if (k not in selected_keys) and (k not in deselected_keys):
                    res_d[k] = lang.source[k]

            res.append(LangResultEntry(name=lang.name, data=res_d))
        return res

    def _get_sound_export(self) -> dict:
        res = dict()
        for pok in self.pokemon.values():
            if pok.selected or pok.merged:
                for form in pok.forms.values():
                    if form.sound_entry is not None:
                        res.update(form.sound_entry.data)
        return res

    # ============================================================

    def _prepare(self) -> None:
        self._folder_setup()
        self._determine_base()
        self._get_paths()

        self.name = "BASE" if (self.is_base) else self.folder_location.name

        outp = f"{self.name}  -  Mod:{bool_square(self.is_mod)} "
        outp += f"BASE:{bool_square(self.is_base)}\n "
        outp += f"{repr(self.component_location)}"
        print(outp)

    # ------------------------------------------------------------

    def _folder_setup(self) -> None:
        if (
            (self.zip_location is None)
            and (self.folder_location is None)
            and (self._extraction_path is None)
        ):
            print("ERROR - no paths given.")
            return

        if self.folder_location is not None:
            if self._extraction_path is None:
                self._extraction_path = self.folder_location.parent / ".temp"
            new_folder_location = self._extraction_path / self.folder_location.name
            new_folder_location.mkdir(parents=True, exist_ok=True)
            print(f"Copying {self.folder_location.name}")
            shutil.copytree(
                src=self.folder_location, dst=new_folder_location, dirs_exist_ok=True
            )
            print(clear_line, end="")
            self.folder_location = new_folder_location

        if self.zip_location is not None:
            if self._extraction_path is None:
                self._extraction_path = self.zip_location.parent / ".temp"
            self.folder_location = self._extraction_path / self.zip_location.stem
            self.folder_location.mkdir(parents=True, exist_ok=True)
            self._unpack()

    def _unpack(self) -> None:
        if self.zip_location is None:
            return
        print(f"Unpacking {self.zip_location.name}")
        with zipfile.ZipFile(str(self.zip_location), "r") as zip_ref:
            zip_ref.extractall(self.folder_location)
        print(clear_line, end="")

    def _determine_base(self) -> None:
        if (
            (not (self.folder_location / "assets").exists())
            and (not (self.folder_location / "data").exists())
            and (self.folder_location / "common").exists()
        ):
            self.is_base = True
            self.folder_location = (
                self.folder_location / "common" / "src" / "main" / "resources"
            )
            return
        if (self.folder_location / "LICENSE").exists():
            self.is_mod = True

            check = [c for c in self.folder_location.rglob("*cobblemon-common*")]
            if len(check):
                self.is_base = True
                return
        if (x := (self.folder_location / "fabric.mod.json")).exists():
            self.is_mod = True
            try:
                with x.open() as f:
                    data = json.load(f)
                    if data.get("id", "") == "cobblemon":
                        self.is_base = True
                        return
            except Exception:
                pass

    def _get_paths(self) -> None:
        val = PackLocations()

        val.home_location = self.folder_location
        if (temp_assets := self.folder_location / "assets").exists():
            for tmpast in temp_assets.iterdir():
                for looks_candidate in ["bedrock", "bedrock/pokemon"]:
                    if (temp_assets_bedrock := (tmpast / looks_candidate)).exists():
                        if (x := temp_assets_bedrock / "animations").exists():
                            val.animations.add(x)
                        if (x := temp_assets_bedrock / "models").exists():
                            val.models.add(x)
                        if (x := temp_assets_bedrock / "posers").exists():
                            val.posers.add(x)
                        if (x := temp_assets_bedrock / "resolvers").exists():
                            val.resolvers.add(x)
                        elif (x := temp_assets_bedrock / "species").exists():
                            val.resolvers.add(x)
                if (x := (tmpast / "lang")).exists():
                    val.lang = x
                if (x := (tmpast / "textures" / "pokemon")).exists():
                    val.textures = x
                if (x := (tmpast / "sounds" / "pokemon")).exists():
                    val.sounds = x
                if (x := (tmpast / "sounds.json")).exists():
                    val.sound_jsons.add(x)

        for data_candidate in [
            "data/cobblemon",
            "data",
        ]:
            if (temp_data := self.folder_location / data_candidate).exists():
                for candidate in temp_data.iterdir():
                    if candidate.is_dir():
                        if (x := candidate / "spawn_pool_world").exists():
                            val.spawn_pool_world.add(x)
                        if (x := candidate / "species").exists():
                            val.species.add(x)
                        if (x := candidate / "species_additions").exists():
                            val.species_additions.add(x)
                        if (x := candidate / "species_features").exists():
                            val.species_features.add(x)
                        if (x := candidate / "species_feature_assignments").exists():
                            val.species_features_assignments.add(x)

        self.component_location = val

    # ============================================================

    def _process(self) -> None:
        print(f"Processing.. {self.name}")
        self._get_features()
        self._get_pokemon()
        self._get_lang()

        self._detect_pseudoforms()

        self._get_sounds()

        self._stamp_forms()

        for p in self.pokemon.values():
            p._mark_requests()

        if not self.verbose:
            print(clear_line, end="")
            print(f"[{TextSymbols.check_mark}] {self.name}")

    # ------------------------------------------------------------
    @safe_parse_per_file(component_attr="species_features", DEBUG=DEBUG)
    def _get_features(self, input_file_path: Path, data: dict) -> None:  # STEP 0
        self.features[input_file_path.stem] = Feature(
            name=input_file_path.stem,
            keys=data.get("keys", list()),
            feat_type=FeatureType(data.get("type", "flag")),
            aspect=data.get("isAspect", False),
            file_path=input_file_path,
            source=data,
        )

    @safe_parse_per_file(component_attr="species_features_assignments", DEBUG=DEBUG)
    def _get_feature_assignments(
        self, input_file_path: Path, data: dict
    ) -> None:  # STEP 0b #TODO?
        self.feature_assignments.append(
            FeatureAssignment(
                file_path=input_file_path,
                source=data,
                name=input_file_path.stem,
                incl_pokemon=data.get("pokemon", list()),
            )
        )
        # ---------------
        # process?
        # ---------------

    # ------------------------------------------------------------

    def _detect_pseudoforms(self) -> None:
        tally: dict[str, list[Pokemon]] = dict()

        for p in self.pokemon.values():
            if (x := p.forms[DefaultNames.BASE_FORM].species) is not None:
                name = x.source.get("name", None)
                if name is None:
                    continue
                lang = [la for la in self.lang_entries if la.name == "en_us"]
                if lang:
                    lang: LangEntry = lang[0]

                    if (key := f"cobblemon.species.{name}.name") in lang:
                        name = lang[key]

                if name not in tally:
                    tally[name] = list()
                tally[name].append(p)

        for p_name, mons in tally.items():
            if len(mons) > 1:
                orig = [mon for mon in mons if mon.internal_name == p_name.lower()]
                if orig:
                    if len(orig) > 1:
                        print("!! PSEUDOFORM CHECK: Multiple with same internal name..")
                    orig = orig[0]
                    for ps_mon in mons:
                        if ps_mon is not orig:
                            ps_mon.is_pseudoform = True

    # ------------------------------------------------------------

    def _get_pokemon(self) -> None:
        self._get_data()

        self._get_looks()

    def _get_data(self) -> None:
        self._get_data_species()
        self._get_data_species_additions()

        self._get_feature_assignments()

        self._get_data_spawn()

    def _get_looks(self) -> None:
        self._get_looks_files()

        self._get_looks_animations()
        self._update_defined_animation_types()
        self._assign_requested_animations()

        self._resolve_requested_animations()
        self._resolve_un_requested_animations()

    def _get_lang(self) -> None:
        if (self.component_location is None) or (self.component_location.lang is None):
            if self.verbose:
                print("-- No Language data")
            return
        print("-- Parsing Language data")

        for t in self.component_location.lang.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data: dict[str, str] = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError):
                    if DEBUG:
                        print(f"WARN!! - {t}")
                        _ = input()
                    continue

                # ---------------

                start_k = "cobblemon.species."
                len_en = LangEntry(file_path=t, source=data, name=t.name)
                len_en.incl_pokemon.update(
                    [k.split(".")[2] for k in data.keys() if k.startswith(start_k)]
                )

                self.lang_entries.append(len_en)

                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e
        if not self.verbose:
            print(clear_line, end="")

    # ------------------------------------------------------------

    @safe_parse_per_file(component_attr="species", DEBUG=DEBUG)
    def _get_data_species(self, t: Path, data: dict) -> None:  # STEP 1
        """parse through species files"""
        pok = Pokemon(
            internal_name=t.stem,
            name=data["name"],
            dex_id=data.get("nationalPokedexNumber", -1),
            features=data.get("features", list()),
            forms={
                DefaultNames.BASE_FORM: PokemonForm(
                    name=DefaultNames.BASE_FORM,
                    aspects=(data.get("aspects", list())),
                    species=bcfo(file_path=t, source=data),
                )
            },
        )

        forms: list = data.get("forms", list())
        for i_form in forms:
            pok.forms[(str(i_form["name"])).lower()] = PokemonForm(
                name=i_form["name"],
                aspects=(i_form.get("aspects", list())),
                species=bcfo(file_path=t, source=i_form),
            )
        self.pokemon[pok.internal_name] = pok
        self._register_evolutions(data=data, name=pok.internal_name, file_path=t)

    def _register_evolutions(
        self, data: dict, name: str, file_path: Path, is_addition: bool = False
    ) -> None:
        for ev in data.get("evolutions", list()):
            self.registered_evolutions.add(
                EvolutionEntry(
                    from_pokemon=name,
                    to_pokemon=ev["result"],
                    file_path=file_path,
                    is_addition=is_addition,
                )
            )
        if ("preEvolution" in data) and (data["preEvolution"]):
            self.registered_evolutions.add(
                EvolutionEntry(
                    from_pokemon=data["preEvolution"],
                    to_pokemon=name,
                    file_path=file_path,
                    is_addition=is_addition,
                )
            )
        for form in data.get("forms", list()):
            self._register_evolutions(
                data=form,
                name=f"{name}_{form['name']}",
                file_path=file_path,
                is_addition=is_addition,
            )

    @safe_parse_per_file(component_attr="species_additions", DEBUG=DEBUG)
    def _get_data_species_additions(
        self, input_file_path: Path, data: dict
    ) -> None:  # STEP 1b
        target_parts: str = (str(data["target"])).split(":")
        if len(target_parts) > 1:
            target = target_parts[1]
        else:
            target = target_parts[0]

        if target not in self.pokemon:
            self.pokemon[target] = Pokemon(
                internal_name=target,
                dex_id=data.get("nationalPokedexNumber", -1),
                features=data.get("features", list()),
                forms={
                    DefaultNames.BASE_FORM: PokemonForm(
                        name=DefaultNames.BASE_FORM,
                        aspects=data.get("aspects", list()),
                        species_additions=bcfo(file_path=input_file_path, source=data),
                    )
                },
            )
        else:
            self.pokemon[target].features.extend(data.get("features", list()))
            self.pokemon[target].forms[DefaultNames.BASE_FORM].species_additions = bcfo(
                file_path=input_file_path, source=data
            )
            self.pokemon[target].forms[DefaultNames.BASE_FORM].aspects.extend(
                data.get("aspects", list())
            )

        forms: list = data.get("forms", list())
        for i_form in forms:
            form_name = (str(i_form["name"])).lower()
            if form_name not in self.pokemon[target].forms:
                self.pokemon[target].forms[form_name] = PokemonForm(
                    name=form_name,
                    aspects=i_form.get("aspects", list()),
                    species_additions=bcfo(file_path=input_file_path, source=i_form),
                )
            else:
                self.pokemon[target].forms[form_name].species_additions = bcfo(
                    file_path=input_file_path, source=i_form
                )
                self.pokemon[target].forms[form_name].aspects.extend(
                    i_form.get("aspects", list())
                )

        self._register_evolutions(
            data=data, name=target, file_path=input_file_path, is_addition=True
        )

    @safe_parse_per_file(component_attr="spawn_pool_world", DEBUG=DEBUG)
    def _get_data_spawn(self, input_file_path: Path, data: dict) -> None:  # STEP 1c
        spawns = data.get("spawns", list())

        for spawn_entry in spawns:
            pok: str = spawn_entry["pokemon"]

            pok_name, aspect = self._extract_name_and_aspect(
                full_pokemon_string=pok, available_features=self.features
            )

            if pok_name not in self.pokemon:
                if DEBUG:
                    print(f"WARN!! - {pok_name}, not found")
                    _ = input()
                self.pokemon[pok_name] = Pokemon(
                    internal_name=pok_name,
                    dex_id=-1,
                    forms={
                        DefaultNames.BASE_FORM: PokemonForm(name=DefaultNames.BASE_FORM)
                    },
                )

            if aspect:  # if you found an aspect, match it or create
                if relevant_forms := self._match_aspect_to_form(
                    aspect=aspect, pokemon=self.pokemon[pok_name]
                ):
                    for form in relevant_forms:
                        form.spawn_pool.append(input_file_path)
                        form.spawn_pool = list(set(form.spawn_pool))
                else:
                    # new_form = PokemonForm(name=f"--{aspect}")
                    new_form = PokemonForm(name=f"--{aspect}", aspects=[aspect])
                    new_form.spawn_pool.append(input_file_path)
                    self.pokemon[pok_name].forms[new_form.name] = new_form

            else:  # else add to primary
                self.pokemon[pok_name].forms[DefaultNames.BASE_FORM].spawn_pool.append(
                    input_file_path
                )
                self.pokemon[pok_name].forms[DefaultNames.BASE_FORM].spawn_pool = list(
                    set(self.pokemon[pok_name].forms[DefaultNames.BASE_FORM].spawn_pool)
                )

    @staticmethod
    def _extract_name_and_aspect(
        full_pokemon_string: str, available_features: dict[str, Feature] = dict()
    ) -> tuple[str, str]:
        pok_parts: list[str] = full_pokemon_string.split(" ")
        pok_name: str = pok_parts[0]

        aspect: str = ""
        if len(pok_parts) > 1:  # try to find an aspect
            feat_parts: list[str] = pok_parts[1].split("=")

            if len(feat_parts) > 1:  # choice
                feat_name: str = feat_parts[0]
                feat_choice: str = feat_parts[1]

                if feat_choice.lower() in [
                    "true",
                    "false",
                ]:  # fix for some dumb stuff
                    if feat_choice.lower() == "true":
                        aspect = feat_parts[0]
                elif feat_name.lower() == "form":  # fix other dumb stuff
                    aspect = feat_choice.lower()
                else:
                    selected = ""
                    if feat_name in available_features:
                        selected = available_features[feat_name].source["aspectFormat"]
                    else:
                        for val in available_features.values():
                            if feat_name in val.keys:
                                selected = val.source["aspectFormat"]
                                break
                    if selected:
                        aspect = selected.replace("{{choice}}", feat_choice)
            else:
                aspect = feat_parts[0]
        if not aspect:
            feat_parts = pok_name.split("_")
            if len(feat_parts) > 1:
                aspect = (
                    "_".join(feat_parts[1:]) if len(feat_parts) > 2 else feat_parts[1]
                )
                pok_name = feat_parts[0]
        return pok_name, aspect

    @staticmethod
    def _match_aspect_to_form(aspect: str, pokemon: Pokemon) -> list[PokemonForm]:
        outp: list[PokemonForm] = list()

        for name, form in pokemon.forms.items():
            if (aspect in form.aspects) or (aspect.lower() == name.lower()):
                outp.append(form)
        return outp

    # ------------------------------------------------------------

    def _get_looks_files(self) -> None:  # STEP 2
        """STEP 2 - parse through resolvers"""
        for t_set in self.component_location.posers:
            for t in t_set.rglob("*.json"):
                self.component_location.posers_dict[t.stem] = t

        for t_set in self.component_location.models:
            for t in t_set.rglob("*.json"):
                self.component_location.models_dict[t.stem] = t

        if self.component_location.textures:
            for t in self.component_location.textures.rglob("*.png"):
                self.component_location.textures_dict[t.stem] = t

        self._get_looks_resolvers()

    @safe_parse_per_file(component_attr="resolvers", DEBUG=DEBUG)
    def _get_looks_resolvers(self, input_file_path: Path, data: dict) -> None:
        pok_name: str = str(data["species"]).split(":")[-1]

        if pok_name not in self.pokemon:
            self.pokemon[pok_name] = Pokemon(
                internal_name=pok_name,
                dex_id=-1,
                forms={DefaultNames.BASE_FORM: PokemonForm(name=DefaultNames.BASE_FORM)},
            )

        order = data.get("order", -1)
        if order in list(self.pokemon[pok_name].resolvers.keys()):
            # if for some reason theres a duplicate key, give it a new negative one
            order = min(min(list(self.pokemon[pok_name].resolvers.keys())), 0) - 1

        new_resolver_entry = ResolverEntry(order=order, own_path=input_file_path)
        aspects: list[str] = list()
        # ----- parsing through variations
        for v in data.get("variations", list()):
            new_resolver_entry = self._resolve_variation_or_layer(
                entry=v, existing_resolver=new_resolver_entry
            )
            v_aspects = v.get("aspects", list())
            aspects.extend(v_aspects)

        # ----- assignemt to correct subforms
        aspects = list(set(aspects))

        if "shiny" in aspects:
            new_resolver_entry.has_shiny = True
            aspects.remove("shiny")

        flag = False
        for asp in aspects:
            for form in self.pokemon[pok_name].forms.values():
                if asp in form.aspects:
                    form.resolver_assignments.add(order)
                    flag = True
        if not flag:
            self.pokemon[pok_name].forms[DefaultNames.BASE_FORM].resolver_assignments.add(
                order
            )

        self.pokemon[pok_name].resolvers[order] = new_resolver_entry

    def _resolve_variation_or_layer(
        self, entry: dict, existing_resolver: ResolverEntry
    ) -> ResolverEntry:
        for _temp_ in self.component_location.posers:
            if x := entry.get("poser", ""):
                poser_name: str = str(x).split(":")[-1]

                if (epath := _temp_ / f"{poser_name}.json").exists():
                    existing_resolver.posers.add(epath)
                    if poser_name in self.component_location.posers_dict:
                        del self.component_location.posers_dict[poser_name]
                else:
                    if poser_name in self.component_location.posers_dict:
                        existing_resolver.posers.add(
                            self.component_location.posers_dict[poser_name]
                        )
                        del self.component_location.posers_dict[poser_name]

        for _temp_ in self.component_location.models:
            # if self.component_location.models:
            if x := entry.get("model", ""):
                model_name: str = str(x).split(":")[-1]
                if (epath := _temp_ / f"{model_name}.json").exists():
                    existing_resolver.models.add(epath)
                    if model_name in self.component_location.models_dict:
                        del self.component_location.models_dict[model_name]
                else:
                    if model_name in self.component_location.models_dict:
                        existing_resolver.models.add(
                            self.component_location.models_dict[model_name]
                        )
                        del self.component_location.models_dict[model_name]

        if self.component_location.textures:
            if x := entry.get("texture", ""):
                t_entries = list()
                if isinstance(x, dict):
                    t_entries.extend(x.get("frames", list()))
                else:
                    t_entries.append(x)

                for tex_entry in t_entries:
                    parts: list[str] = str(tex_entry).split("/")
                    if "pokemon" in parts:
                        index = parts.index("pokemon")
                        partial_path = "/".join(parts[index + 1 :])

                        if (
                            epath := self.component_location.textures / partial_path
                        ).exists():
                            existing_resolver.textures.add(epath)
                            if epath.stem in self.component_location.textures_dict:
                                del self.component_location.textures_dict[epath.stem]
                        else:
                            if parts[-1] in self.component_location.textures_dict:
                                existing_resolver.textures.add(
                                    self.component_location.textures_dict[parts[-1]]
                                )
                                del self.component_location.textures_dict[parts[-1]]

        for layer in entry.get("layers", list()):
            existing_resolver = self._resolve_variation_or_layer(
                entry=layer, existing_resolver=existing_resolver
            )

        return existing_resolver

    # ------------------------------------------------------------

    @safe_parse_per_file(component_attr="animations", DEBUG=DEBUG)
    def _get_looks_animations(self, input_file_path: Path, data: dict) -> None:  # STEP 3
        anims = data.get("animations", dict())
        if not isinstance(anims, dict):
            return

        for key in anims.keys():
            key_parts: list[str] = str(key).split(".")
            if len(key_parts) == 1:
                # no animation group, e.g. pikachu's "education"
                name = "__null__"
                move = key_parts[0]
            else:
                name = key_parts[1]
                move = key_parts[2]

            if name not in self.present_animations:
                self.present_animations[name] = dict()
            if move not in self.present_animations[name]:
                self.present_animations[name][move] = set()
            self.present_animations[name][move].add(input_file_path)

    def _update_defined_animation_types(self) -> None:  # STEP 3b
        self.defined_animation_types.update(default_animation_types)

        for p_entry in self.present_animations.values():
            self.defined_animation_types.update(list(p_entry.keys()))

    def _assign_requested_animations(self) -> None:  # STEP 3c
        for pok in self.pokemon.values():
            for res in pok.resolvers.values():
                requested: set[tuple[str, str]] = set()
                for pose in list(res.posers):
                    try:
                        with pose.open() as f:
                            data = json.load(f)
                    except (UnicodeDecodeError, JSONDecodeError):
                        if DEBUG:
                            print(f"WARN!! - {pose}")
                            _ = input()
                        continue

                    for def_anim in self.defined_animation_types:
                        if def_anim in data:
                            requested.add(
                                PoserResolver._parse_poser_animation_line(
                                    poser_line=data[def_anim]
                                )
                            )
                    if "animations" in data:
                        requested.update(
                            PoserResolver._parse_poser_animation_entry(data["animations"])
                        )

                    for _, pose_data in (data.get("poses", dict())).items():
                        requested.update(
                            PoserResolver._navigate_poser_entry(poser_entry=pose_data)
                        )

                for req_entry in list(requested):
                    p_name, anim_name = req_entry
                    if p_name not in res.requested_animations:
                        res.requested_animations[p_name] = dict()
                    if anim_name not in res.requested_animations[p_name]:
                        res.requested_animations[p_name][anim_name] = False

    # ------------------------------

    # ------------------------------

    def _resolve_requested_animations(self) -> None:  # STEP 3d
        for pok in self.pokemon.values():
            for resolver in pok.resolvers.values():
                for pn in resolver.requested_animations.keys():
                    rn_res = self.present_animations.get(pn, dict())
                    for req_anim in resolver.requested_animations[pn].keys():
                        if req_anim in rn_res:
                            resolver.animations.update(rn_res[req_anim])
                            self.accessed_animations.add(pn)  # mark pokemon
                            resolver.requested_animations[pn][req_anim] = True

    def _resolve_un_requested_animations(self) -> None:  # STEP 3e
        un_requested: set[str] = set(list(self.present_animations.keys())).difference(
            self.accessed_animations
        )

        for pok in un_requested:
            parts = pok.split("_")
            pok_name = parts[0]
            pok_aspect = parts[0] if len(parts) > 1 else None

            if pok_name in self.pokemon:
                pok_entity: Pokemon = self.pokemon[pok_name]
                if not pok_aspect:
                    self._present_animation_update_resolver(
                        pokemon=pok_entity, resolver_entry=0, pa_name=pok
                    )
                else:
                    flag = False
                    for key, resolver in pok_entity.resolvers.items():
                        if pok_aspect in resolver.aspects:
                            self._present_animation_update_resolver(
                                pokemon=pok_entity, resolver_entry=key, pa_name=pok
                            )
                            flag = True
                    if not flag:
                        self._present_animation_update_resolver(
                            pokemon=pok_entity, resolver_entry=0, pa_name=pok
                        )

    def _present_animation_update_resolver(
        self, pokemon: Pokemon, resolver_entry: int, pa_name: str
    ) -> None:
        if resolver_entry not in pokemon.resolvers:
            pokemon.resolvers[resolver_entry] = ResolverEntry(order=resolver_entry)
        for a_entry in self.present_animations[pa_name].values():
            pokemon.resolvers[resolver_entry].animations.update(a_entry)
        self.accessed_animations.add(pa_name)

    # ------------------------------------------------------------

    def _get_sounds(self) -> None:
        self.sounds = SoundPack(
            _parent_pack=self, _base_folder=self.component_location.sounds
        )
        if self.component_location.sound_jsons:
            try:
                sj = list(self.component_location.sound_jsons)[0]
                with sj.open() as f:  # TODO
                    data = json.load(f)
                    self.sounds.assignment = bcfo(file_path=sj, source=data)
            except (UnicodeDecodeError, JSONDecodeError):
                if DEBUG:
                    print(f"WARN!! - {sj}")
                    _ = input()

        self._get_sound_files()
        self.sounds.process()
        self._assign_sound_files()

    def _get_sound_files(self) -> None:
        if self.component_location.sounds:
            for sound_file in self.component_location.sounds.rglob("*.ogg"):
                self.sounds._loose_files.add(sound_file)

    def _assign_sound_files(self) -> None:
        for pokemon_sound in self.sounds:
            name, aspect = self._extract_name_and_aspect(
                pokemon_sound.internal_name, available_features=self.features
            )

            if name not in self.pokemon:
                self.pokemon[name] = Pokemon(
                    internal_name=name,
                    dex_id=-1,
                    forms={
                        DefaultNames.BASE_FORM: PokemonForm(name=DefaultNames.BASE_FORM)
                    },
                )

            if aspect:  # if you found an aspect, match it or create
                if relevant_forms := self._match_aspect_to_form(
                    aspect=aspect, pokemon=self.pokemon[name]
                ):
                    for form in relevant_forms:
                        form.sound_entry = pokemon_sound

                else:
                    # new_form = PokemonForm(name=f"--{aspect}")
                    new_form = PokemonForm(name=f"--{aspect}", aspects=[aspect])
                    new_form.sound_entry = pokemon_sound
                    self.pokemon[name].forms[new_form.name] = new_form
            else:
                self.pokemon[name].forms[
                    DefaultNames.BASE_FORM
                ].sound_entry = pokemon_sound

    # ------------------------------------------------------------

    def _assign_evo_score(self):
        for entry in self.registered_evolutions.evolutions:
            if (x := self._cleanup_evo_name(entry.to_pokemon)) in self.pokemon:
                self.pokemon[x].pre_evos += 1

            if (x := self._cleanup_evo_name(entry.from_pokemon)) in self.pokemon:
                self.pokemon[x].evos += 1

    def _cleanup_evo_name(self, name: str) -> str:
        if name:
            name = name.split(" ")[0]
            name = name.split("_")[0]
            return name
        return ""

    def _stamp_forms(self) -> None:
        for p in self.pokemon.values():
            p.parent_pack = self

            for f in p.forms.values():
                f.parent_pack = self
                f.parent_pokemon = p

    # ============================================================

    def _dirty_pokedex_fix(self) -> None:
        _edited_files: set[Path] = set()
        for pok in self.pokemon.values():
            if not pok.selected:
                continue
            flag = False
            for form in pok.forms.values():
                for x in [form.species, form.species_additions]:
                    if x is not None:
                        flag = True
                        e_path = x.file_path
                        if (e_path not in _edited_files) and e_path.exists():
                            data = json.loads(e_path.read_text())
                            data["implemented"] = True
                            if pok.is_pseudoform and gcr_settings.EXCLUDE_PSEUDOFORMS:
                                data["implemented"] = False
                            e_path.write_text(json.dumps(data, indent=8))
                            _edited_files.add(e_path)
            if not flag:
                if [
                    item
                    for form in pok.forms.values()
                    for item in form.spawn_pool
                    if item
                ]:
                    sa = {
                        "target": f"cobblemon:{pok.internal_name}",
                        "implemented": True,
                    }
                    if self.component_location.species_additions:
                        target_path = (
                            list(self.component_location.species_additions)[0]
                            / f"{pok.internal_name}.json"
                        )
                    else:
                        target_path = (
                            self.folder_location
                            / "data"
                            / "cobblemon"
                            / "species_additions"
                        )
                        target_path.mkdir(parents=True, exist_ok=True)
                        target_path = target_path / f"{pok.internal_name}.json"

                    target_path.write_text(json.dumps(sa, indent=2))
                    pok.forms[list(pok.forms.keys())[0]].spawn_pool.append(target_path)

    # ============================================================

    def __repr__(self) -> str:
        res: str = str()
        res += f"Px{len(self.pokemon)} "
        res += f"Fx{sum([len(p.forms) for p in self.pokemon.values()])} "
        res += f"| {self.name or self.folder_location or self.zip_location} "
        return res

    def display(self, pagination: int | None = None) -> None:
        for i, p in enumerate(
            sorted(
                self.pokemon.values(),
                key=lambda item: (item.dex_id, item.internal_name),
            )
        ):
            print(p)
            if (pagination) and (not (i % pagination)) and i:
                _ = input("Press any key to continue..")
                print(f"\033[A\r{' '*40}\r", end="")
        outp = f"\nPokemon: {len(self.pokemon)}  "
        outp += f"Forms: {sum([len(p.forms) for p in self.pokemon.values()])}"
        print(outp)
