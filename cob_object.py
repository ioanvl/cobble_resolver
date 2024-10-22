from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, LiteralString, Optional
import json
from json import JSONDecodeError
import zipfile
from cli_utils import keypress, positive_int_choice

DEBUG = False

square_f = "\u25a3"
square_e = "\u25a1"

default_animation_types: list[str] = [
    "ground_idle",
    "ground_walk",
    "ground_run" "air_idle",
    "air_fly",
    "water_idle",
    "water_swim",
    "render",
    "cry",
    "faint",
    "recoil",
    "blink",
    "sleep",
    "water_sleep",
    "physical",
    "special",
    "status",
]


def bool_square(inp: bool = False) -> str:
    return square_f if inp else square_e


@dataclass
class bcfo:
    file_path: Path
    source: dict
    # partial: bool = False


class FeatureType(Enum):
    FLAG = "flag"
    CHOICE = "choice"
    INTEGER = "integer"


@dataclass
class Feature(bcfo):
    name: str
    keys: list[str]
    feat_type: FeatureType
    aspect: bool

    # duplicate: bool = False

    def __repr__(self) -> str:
        return f"{str(self.feat_type.name)[0:2]} - {self.name}"


@dataclass
class FeatureAssignment(bcfo):
    name: str


@dataclass
class SpawnEntry:
    file_path: Path


@dataclass
class ResolverEntry:
    order: int
    models: set[Path] = field(default_factory=set)

    posers: set[Path] = field(default_factory=set)
    animations: set[Path] = field(default_factory=set)

    textures: set[Path] = field(default_factory=set)
    has_shiny: bool = False

    aspects: set[str] = field(default_factory=set)

    requested_animations: dict[str, dict[str, bool]] = field(default_factory=dict)
    # present_animations: set[str] = field(default_factory=set)

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


@dataclass
class PokemonForm:
    name: str

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
            ret += f"{s} {self.name}\n"
        ret += f"{s} "
        ret += f"DATA: Spawn:{bool_square(len(self.spawn_pool))} | "
        ret += f"S:{self.__square_atr(self.species)}"
        ret += f"/{self.__square_atr(self.species_additions)}:SA "
        # ret += f"| LOOKS: {bool_square(len(self.resolver_assignments))}"

        ret += f"\n{s} {'-' * 10}"
        return ret

    @property
    def comp_stamp(self) -> list[bool]:
        res = list()
        res.append(bool(len(self.spawn_pool)))
        res.append(self.species is not None)
        res.append(self.species_additions is not None)
        x = bool(len(self.resolver_assignments))
        res.append(x)
        if x:
            r = list(self._get_resolvers().values())[0].comp_stamp
            res.extend(r)

        else:
            res.extend([0, 0, 0, 0, 0])

        return res

    def _get_resolvers(self) -> dict[int, ResolverEntry]:
        if self.parent_pack is None:
            return {}
        return {r: self.parent_pokemon.resolvers[r] for r in self.resolver_assignments}

    def _st(self) -> LiteralString:
        return f"{' '*(3 if (self.name != 'base_form') else 0)}|"

    def __square_atr(self, val: Any) -> str:
        return bool_square(val is not None)


@dataclass
class Pokemon:
    internal_name: str
    name: str | None = None
    dex_id: int | None = None

    features: list[str] = field(default_factory=list)
    forms: dict[str, PokemonForm] = field(default_factory=dict)
    resolvers: dict[int, ResolverEntry] = field(default_factory=dict)

    parent_pack: Optional["Pack"] = None
    selected: bool = False

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


@dataclass
class PackLocations:
    resolvers: Path | None = None
    models: Path | None = None
    textures: Path | None = None
    animations: Path | None = None
    posers: Path | None = None

    lang: Path | None = None

    species: Path | None = None
    species_additions: Path | None = None
    spawn_pool_world: Path | None = None
    species_features: Path | None = None
    species_features_assignments: Path | None = None

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
            (self.resolvers is not None)
            or (self.models is not None)
            or (self.textures is not None)
            or (self.animations is not None)
            or (self.posers is not None)
            or (self.lang is not None)
            or (self.species is not None)
            or (self.species_additions is not None)
            or (self.spawn_pool_world is not None)
            or (self.species_features is not None)
            or (self.species_features_assignments is not None)
        )


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

        self.is_base: bool = False
        self.is_mod: bool = False

    def _run(self) -> None:
        self._prepare()
        self._process()

    # ============================================================

    def _prepare(self) -> None:
        self._folder_setup()
        self._unpack()
        self._determine_base()
        self._get_paths()

        self.name = (
            "BASE"
            if (self.is_base and (self.folder_location.name == "resources"))
            else self.folder_location.name
        )

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
            return

        if self.zip_location is not None:
            if self._extraction_path is None:
                self._extraction_path = self.zip_location.parent / ".temp"
            self.folder_location = self._extraction_path / self.zip_location.stem
            self.folder_location.mkdir(parents=True, exist_ok=True)

    def _unpack(self) -> None:
        if self.zip_location is None:
            return
        with zipfile.ZipFile(str(self.zip_location), "r") as zip_ref:
            zip_ref.extractall(self.folder_location)

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
        if (self.folder_location / "LICENSE").exists():
            self.is_mod = True

            check = [c for c in self.folder_location.rglob("*cobblemon-common*")]
            if len(check):
                self.is_base = True

    def _get_paths(self) -> None:
        val = PackLocations()
        if (temp_assets := self.folder_location / "assets" / "cobblemon").exists():
            if (temp_assets_bedrock := (temp_assets / "bedrock")).exists():
                if (temp_assets_bedrock / "pokemon").exists():
                    temp_assets_bedrock = temp_assets_bedrock / "pokemon"

                if (x := temp_assets_bedrock / "animations").exists():
                    val.animations = x
                if (x := temp_assets_bedrock / "models").exists():
                    val.models = x
                if (x := temp_assets_bedrock / "posers").exists():
                    val.posers = x
                if (x := temp_assets_bedrock / "resolvers").exists():
                    val.resolvers = x
                elif (x := temp_assets_bedrock / "species").exists():
                    val.resolvers = x
            if (temp_assets / "lang").exists():
                val.lang = temp_assets / "lang"
            if (temp_assets / "textures" / "pokemon").exists():
                val.textures = temp_assets / "textures" / "pokemon"

        data_flag = False
        if (temp_data := self.folder_location / "data" / "cobblemon").exists():
            data_flag = True
        elif (temp_data := self.folder_location / "data").exists():
            for candidate in temp_data.iterdir():
                if candidate.is_dir():
                    if (
                        ((candidate / "spawn_pool_world").exists())
                        or ((candidate / "species").exists())
                        or ((candidate / "species_additions").exists())
                        or ((candidate / "species_features").exists())
                        or ((candidate / "species_feature_assignments").exists())
                    ):
                        temp_data = candidate
                        data_flag = True
                        break

        if data_flag:
            if (x := temp_data / "spawn_pool_world").exists():
                val.spawn_pool_world = x
            if (x := temp_data / "species").exists():
                val.species = x
            if (x := temp_data / "species_additions").exists():
                val.species_additions = x
            if (x := temp_data / "species_features").exists():
                val.species_features = x
            if (x := temp_data / "species_feature_assignments").exists():
                val.species_features_assignments = x
        self.component_location = val

    # ============================================================

    def _process(self) -> None:
        print(f"Running pack: {self.name}")
        self._get_features()
        self._get_pokemon()

        self._stamp_forms()

    # ------------------------------------------------------------

    def _get_features(self) -> None:  # STEP 0
        if (self.component_location is None) or (
            self.component_location.species_features is None
        ):
            print("-- No Features")
            return
        print("-- Parsing Features")

        for t in self.component_location.species_features.iterdir():
            if t.suffix == ".json":
                with t.open() as f:
                    data = json.load(f)
                self.features[t.stem] = Feature(
                    name=t.stem,
                    keys=data.get("keys", list()),
                    feat_type=FeatureType(data.get("type", "flag")),
                    aspect=data.get("isAspect", False),
                    file_path=t,
                    source=data,
                )

    def _get_feature_assignments(self) -> None:  # STEP 0b #TODO?
        if (self.component_location is None) or (
            self.component_location.species_features_assignments is None
        ):
            print("-- No Feature Assignments")
            return
        print("-- Parsing Feature Assignments")

        for t in self.component_location.species_features_assignments.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except UnicodeDecodeError as _:
                    continue

                self.feature_assignments.append(
                    FeatureAssignment(file_path=t, source=data, name=t.stem)
                )

                # ---------------
                # process?
                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

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
        self._get_looks_resolvers()

        self._get_looks_animations()
        self._update_defined_animation_types()
        self._assign_requested_animations()

        self._resolve_requested_animations()
        self._resolve_un_requested_animations()

    # ------------------------------------------------------------

    def _get_data_species(self) -> None:  # STEP 1
        """parse through species files"""
        if (self.component_location is None) or (
            self.component_location.species is None
        ):
            print("-- No Species")
            return
        print("-- Parsing Species")

        for t in self.component_location.species.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError) as _:
                    if DEBUG:
                        print(f"WARN!! - {t}")
                        _ = input()
                    continue
                pok = Pokemon(
                    internal_name=t.stem,
                    name=data["name"],
                    dex_id=data.get("nationalPokedexNumber", -1),
                    features=data.get("features", list()),
                    forms={
                        "base_form": PokemonForm(
                            name="base_form",
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
            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    def _get_data_species_additions(self) -> None:  # STEP 1b
        if (self.component_location is None) or (
            self.component_location.species_additions is None
        ):
            print("-- No Species Additions")
            return
        print("-- Parsing Species Additions")

        for t in self.component_location.species_additions.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError) as _:
                    if DEBUG:
                        print(f"WARN!! - {t}")
                        _ = input()
                    continue

                # ---------------
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
                            "base_form": PokemonForm(
                                name="base_form",
                                aspects=data.get("aspects", list()),
                                species_additions=bcfo(file_path=t, source=data),
                            )
                        },
                    )
                else:
                    self.pokemon[target].features.extend(data.get("features", list()))
                    self.pokemon[target].forms["base_form"].species_additions = bcfo(
                        file_path=t, source=data
                    )
                    self.pokemon[target].forms["base_form"].aspects.extend(
                        data.get("aspects", list())
                    )

                forms: list = data.get("forms", list())
                for i_form in forms:
                    form_name = (str(i_form["name"])).lower()
                    if form_name not in self.pokemon[target].forms:
                        self.pokemon[target].forms[form_name] = PokemonForm(
                            name=form_name,
                            aspects=i_form.get("aspects", list()),
                            species_additions=bcfo(file_path=t, source=i_form),
                        )
                    else:
                        self.pokemon[target].forms[form_name].species_additions = bcfo(
                            file_path=t, source=i_form
                        )
                        self.pokemon[target].forms[form_name].aspects.extend(
                            i_form.get("aspects", list())
                        )

                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    def _get_data_spawn(self) -> None:  # STEP 1c
        if (self.component_location is None) or (
            self.component_location.spawn_pool_world is None
        ):
            print("-- No Spawn Data")
            return
        print("-- Parsing Spawn Data")

        for in_spawn_file in self.component_location.spawn_pool_world.rglob("*.json"):
            try:
                try:
                    with in_spawn_file.open() as f:
                        data = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError) as _:
                    if DEBUG:
                        print(f"WARN!! - {in_spawn_file}")
                        _ = input()
                    continue

                # ---------------
                spawns = data.get("spawns", list())

                for spawn_entry in spawns:
                    pok: str = spawn_entry["pokemon"]
                    pok_parts: list[str] = pok.split(" ")
                    pok_name: str = pok_parts[0]

                    if pok_name not in self.pokemon:
                        if DEBUG:
                            print(f"WARN!! - {pok_name}, not found")
                            _ = input()
                        self.pokemon[pok_name] = Pokemon(
                            internal_name=pok_name,
                            dex_id=-1,
                            forms={"base_form": PokemonForm(name="base_form")},
                        )

                    flag = False
                    if len(pok_parts) > 1:
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
                                if feat_choice.lower() in self.pokemon[pok_name].forms:
                                    self.pokemon[pok_name].forms[
                                        feat_choice.lower()
                                    ].spawn_pool.append(in_spawn_file)
                                    self.pokemon[pok_name].forms[
                                        feat_choice.lower()
                                    ].spawn_pool = list(
                                        set(
                                            self.pokemon[pok_name]
                                            .forms[feat_choice.lower()]
                                            .spawn_pool
                                        )
                                    )
                                    continue
                            else:
                                selected = ""
                                if feat_name in self.features:
                                    selected = self.features[feat_name].source[
                                        "aspectFormat"
                                    ]
                                else:
                                    for val in self.features.values():
                                        if feat_name in val.keys:
                                            selected = val.source["aspectFormat"]
                                            break
                                if selected:
                                    aspect = selected.replace("{{choice}}", feat_choice)
                        else:
                            aspect = feat_parts[0]

                        for form in self.pokemon[pok_name].forms.values():
                            if aspect in form.aspects:
                                form.spawn_pool.append(in_spawn_file)
                                form.spawn_pool = list(set(form.spawn_pool))
                                flag = True
                                break
                    if not flag:
                        self.pokemon[pok_name].forms["base_form"].spawn_pool.append(
                            in_spawn_file
                        )
                        self.pokemon[pok_name].forms["base_form"].spawn_pool = list(
                            set(self.pokemon[pok_name].forms["base_form"].spawn_pool)
                        )

                # ---------------

            except Exception as e:
                print(f"\n\n{in_spawn_file}\n\n")
                raise e

    # ------------------------------------------------------------

    def _get_looks_resolvers(self) -> None:  # STEP 2 #TODO
        """STEP 2 - parse through resolvers"""
        if (self.component_location is None) or (
            self.component_location.resolvers is None
        ):
            print("-- No Resolver Data")
            return
        print("-- Parsing Resolver Data")

        if self.component_location.posers:
            for t in self.component_location.posers.rglob("*.json"):
                self.component_location.posers_dict[t.stem] = t

        if self.component_location.models:
            for t in self.component_location.models.rglob("*.json"):
                self.component_location.models_dict[t.stem] = t

        if self.component_location.textures:
            for t in self.component_location.textures.rglob("*.png"):
                self.component_location.textures_dict[t.stem] = t

        for t in self.component_location.resolvers.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError) as _:
                    if DEBUG:
                        print(f"WARN!! - {t}")
                        _ = input()
                    continue

                # ---------------
                pok_name: str = str(data["species"]).split(":")[-1]

                if pok_name not in self.pokemon:
                    self.pokemon[pok_name] = Pokemon(
                        internal_name=pok_name,
                        dex_id=-1,
                        forms={"base_form": PokemonForm(name="base_form")},
                    )

                order = data.get("order", -1)
                if order in list(self.pokemon[pok_name].resolvers.keys()):
                    # if for some reason theres a duplicate key, give it a new negative one
                    order = (
                        min(min(list(self.pokemon[pok_name].resolvers.keys())), 0) - 1
                    )

                new_resolver_entry = ResolverEntry(order=order)
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
                    self.pokemon[pok_name].forms["base_form"].resolver_assignments.add(
                        order
                    )

                self.pokemon[pok_name].resolvers[order] = new_resolver_entry

                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    def _resolve_variation_or_layer(
        self, entry: dict, existing_resolver: ResolverEntry
    ) -> ResolverEntry:
        if self.component_location.posers:
            if x := entry.get("poser", ""):
                poser_name: str = str(x).split(":")[-1]

                if (
                    epath := self.component_location.posers / f"{poser_name}.json"
                ).exists():
                    existing_resolver.posers.add(epath)
                    if poser_name in self.component_location.posers_dict:
                        del self.component_location.posers_dict[poser_name]
                else:
                    if poser_name in self.component_location.posers_dict:
                        existing_resolver.posers.add(
                            self.component_location.posers_dict[poser_name]
                        )
                        del self.component_location.posers_dict[poser_name]

        if self.component_location.models:
            if x := entry.get("model", ""):
                model_name: str = str(x).split(":")[-1]
                if (
                    epath := self.component_location.models / f"{model_name}.json"
                ).exists():
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

    def _get_looks_animations(self) -> None:  # STEP 3
        if (self.component_location is None) or (
            self.component_location.animations is None
        ):
            print("-- No Animations")
            return
        print("-- Parsing Animations")

        for t in self.component_location.animations.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except (UnicodeDecodeError, JSONDecodeError) as _:
                    if DEBUG:
                        print(f"WARN!! - {t}")
                        _ = input()
                    continue

                # ---------------
                anims = data.get("animations", dict())
                if not isinstance(anims, dict):
                    continue

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
                    self.present_animations[name][move].add(t)

                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    def _update_defined_animation_types(self) -> None:  # STEP 3b
        self.defined_animation_types.update(default_animation_types)

        for p_entry in self.present_animations.values():
            self.defined_animation_types.update(list(p_entry.keys()))

    # ------------------------------

    def _assign_requested_animations(self) -> None:  # STEP 3c
        for pok in self.pokemon.values():
            for res in pok.resolvers.values():
                requested: set[tuple[str, str]] = set()
                for pose in list(res.posers):
                    try:
                        with pose.open() as f:
                            data = json.load(f)
                    except (UnicodeDecodeError, JSONDecodeError) as _:
                        if DEBUG:
                            print(f"WARN!! - {pose}")
                            _ = input()
                        continue

                    for def_anim in self.defined_animation_types:
                        if def_anim in data:
                            requested.add(
                                self._parse_poser_animation_line(
                                    poser_line=data[def_anim]
                                )
                            )
                    if "animations" in data:
                        requested.update(
                            self._parse_poser_animation_entry(data["animations"])
                        )

                    for _, pose_data in (data.get("poses", dict())).items():
                        requested.update(
                            self._navigate_poser_entry(poser_entry=pose_data)
                        )

                for req_entry in list(requested):
                    p_name, anim_name = req_entry
                    if p_name not in res.requested_animations:
                        res.requested_animations[p_name] = dict()
                    if anim_name not in res.requested_animations[p_name]:
                        res.requested_animations[p_name][anim_name] = False

    def _navigate_poser_entry(
        self, poser_entry: dict, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        for t in ["quirks", "animations"]:
            existing_set.update(
                self._parse_poser_animation_entry(poser_entry.get(t, None))
            )

        return existing_set

    def _parse_poser_animation_entry(
        self, poser_entry: Any, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        if isinstance(poser_entry, str):
            existing_set.add(self._parse_poser_animation_line(poser_line=poser_entry))
        elif isinstance(poser_entry, list):
            existing_set.update(
                self._parse_poser_animation_list(poser_entry=poser_entry)
            )
        elif isinstance(poser_entry, dict):
            existing_set.update(
                self._parse_poser_animation_dict(poser_entry=poser_entry)
            )

        return existing_set

    def _parse_poser_animation_list(
        self, poser_entry: list, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        for pl in poser_entry:
            existing_set.update(self._parse_poser_animation_entry(pl))

        return existing_set

    def _parse_poser_animation_dict(
        self, poser_entry: dict, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        if "animations" in poser_entry:
            existing_set.update(
                self._parse_poser_animation_entry(poser_entry=poser_entry["animations"])
            )
            del poser_entry["animations"]

        for move, pl in poser_entry.items():
            existing_set.update(self._parse_poser_animation_entry(pl))

        return existing_set

    def _parse_poser_animation_line(self, poser_line: str | None) -> tuple[str, str]:
        if not poser_line:
            return ("", "")

        for stw in ["q.bedrock", "q.bedrock_quirk", "bedrock"]:
            if poser_line.startswith(stw):
                return self._extract_poser_animation_line(poser_line=poser_line)
        return ("", "")

    def _extract_poser_animation_line(self, poser_line: str) -> tuple[str, str]:
        poser_line = self._extract_parentheses(poser_line=poser_line)
        parts = poser_line.split(",")
        name = parts[0].strip(" ''").strip('"')
        move = parts[1]
        if move.startswith("q."):
            move = self._extract_parentheses(move)
        move = move.strip(" ''").strip('"')
        return (name, move)
        "" "faint" ""

    def _extract_parentheses(self, poser_line: str) -> str:
        parts = poser_line.split("(")
        poser_line = "(".join(parts[1:]) if len(parts) > 2 else parts[1]
        parts = poser_line.split(")")
        poser_line = ")".join(parts[:-1]) if len(parts) > 2 else parts[0]
        return poser_line

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

    def _stamp_forms(self) -> None:
        for p in self.pokemon.values():
            p.parent_pack = self

            for f in p.forms.values():
                f.parent_pack = self
                f.parent_pokemon = p

    # ============================================================

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
        print(
            f"\nPokemon: {len(self.pokemon)}  Forms: {sum([len(p.forms) for p in self.pokemon.values()])}"
        )


class Combiner:
    def __init__(self, dir_name: Path | None = None):
        if (not dir_name) or (not dir_name.exists()):
            self.dir_name = Path(filedialog.askdirectory())
        else:
            self.dir_name = dir_name

        self.extraction_path: str = ""

        self.pack_paths: set[Path] = set()
        self.packs: list[Pack] = list()

        self.defined_pokemon: set[str] = set()

    def run(self) -> None:
        self._gather_packs()
        self._prepare()
        self._process()

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
        print(f"\n#{'='*25}\n#  PREPARING\n#{'='*25}\n")
        self.extraction_path = self.dir_name / ".temp"
        self.extraction_path.mkdir(parents=True, exist_ok=True)
        for p in self.packs:
            p._extraction_path = self.extraction_path

        for p in self.packs:
            p._prepare()

        self._remove_empty_packs()

        if len(["_" for p in self.packs if p.is_base]) > 1:
            raise RuntimeError("Multiple [BASE] type packs present.")

    def _remove_empty_packs(self) -> None:
        for p in self.packs:
            if not bool(p.component_location):
                self.packs.remove(p)

    # ------------------------------------------------------------

    def _process(self) -> None:
        print(f"\n#{'='*25}\n#  PROCESSING\n#{'='*25}\n")
        for p in self.packs:
            p._process()

        for p in self.packs:
            self.defined_pokemon.update(list(p.pokemon.keys()))

        self._resolution_core()

    def _resolution_core(self) -> None:
        print(f"\n#{'='*25}\n#  RESOLVE\n#{'='*25}\n")
        for pok_name in self.defined_pokemon:
            entities: list[Pokemon] = list()
            for pack in self.packs:
                if pok_name in pack.pokemon.keys():
                    entities.append(pack.pokemon[pok_name].parent_pack.name)
            if len(entities) > 1:
                self._resolution_pokemon(pokemon_name=pok_name)

    def _resolution_pokemon(self, pokemon_name: str) -> None:
        temp_holder: dict[str, Pokemon] = dict()

        d_num: int = 0
        d_name: str = ""

        for pack in self.packs:
            if pokemon_name in pack.pokemon.keys():
                temp_holder[pack.name] = pack.pokemon[pokemon_name]
                if (
                    (temp_holder[pack.name].dex_id != -1)
                    and (not d_num)
                    and (not d_name)
                ):
                    d_num = temp_holder[pack.name].dex_id
                    d_name = temp_holder[pack.name].name
        if not d_name:
            d_name = (
                list(temp_holder.values())[0].name
                or f"[{list(temp_holder.values())[0].internal_name}]"
            )
            # print(f"={pack.name}")
            # print(repr(pack.pokemon[pokemon_name]))
        flag = False
        selected_key: str = ""
        if len(temp_holder) == 2 and ("BASE" in temp_holder):
            keys = list(temp_holder.keys())
            keys.remove("BASE")

            b_patch = temp_holder["BASE"].forms["base_form"].comp_stamp
            o_patch = temp_holder[keys[0]].forms["base_form"].comp_stamp

            if ((not b_patch[0]) and o_patch[0]) and (
                ((not b_patch[3]) and o_patch[3])
                or ((not all(b_patch[4:])) and (all(o_patch[4:])))
            ):
                selected_key = keys[0]
                temp_holder[selected_key].selected = True
                flag = True

        if flag:
            print(f"--AUTO-- \n#{d_num} - {d_name}  [{selected_key}]")
        else:
            print(f"#{d_num} - {d_name}")

            keys = list(temp_holder.keys())

            for i, k in enumerate(keys):
                pack_name = k
                p = temp_holder[pack_name]
                outp = repr(p)
                out_parts = outp.split("\n")
                out_parts[0] = f"{i}. {pack_name}"
                outp = "\n".join(out_parts)
                print(outp)

            k_in = positive_int_choice(max_ch=len(keys), text="Pack choice: ")

            selected_key = keys[k_in]
            temp_holder[selected_key].selected = True
            print(f"\033[A\r{' '*40}\r", end="")
            print(f"- {k_in}. [{selected_key}]")

        print("=" * 25)

    # ------------------------------------------------------------

    def _cleanup(self) -> None:
        pass


RUN_TYPE = 1
SELECTED_PACK = [1, 3, 7]

if __name__ == "__main__":
    if RUN_TYPE == 0:
        packs = [
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/AlolaMons_v1.3.zip",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cobblemon-fabric-1.5.2+1.20.1.jar",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cobble-Remodels_v5.1.zip",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/z_AllTheMons-Release4-Version55.zip",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/pokeinsanoV1.7.zip",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/MegamonsFabric-1.2.1.jar",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/pokemans_v9.72.zip",
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cardboard_Cutout_Mon_v1.3.zip",
        ]
        working_dir = Path(
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/cobblemon-main"
        )

        if isinstance(SELECTED_PACK, int):
            SELECTED_PACK = [SELECTED_PACK]
        for sp in SELECTED_PACK:
            p = Pack(zip_location=Path(packs[((sp - 1) % len(packs))]))
            p._run()
            from pprint import pprint

            p.display(20)
            pprint(list(p.features.values()))

        # pprint(p.feature_assignments)
    elif RUN_TYPE == 1:
        hot_dir = Path(
            "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_hot_test"
        )
        comb = Combiner(dir_name=hot_dir)
        comb.run()
    elif RUN_TYPE == 2:
        comb = Combiner()
        comb.run()
