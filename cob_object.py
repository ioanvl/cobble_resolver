from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any
import json
from json import JSONDecodeError
import zipfile
import os

DEBUG = False

square_f = "\u25a3"
square_e = "\u25a1"


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
class ResolverEntry(bcfo):
    order: int


@dataclass
class PokemonForm:
    name: str

    aspects: list[str] = field(default_factory=list)
    # looks
    resolvers: list[ResolverEntry] = field(default_factory=list)
    animation: bcfo | None = None
    model: bcfo | None = None
    poser: bcfo | None = None

    texture: str | None = None
    texture_shiny: str | None = None
    textures_extra: list[str] = field(default_factory=list)
    # data
    species: bcfo | None = None
    species_additions: bcfo | None = None

    spawn_pool: list[Path] = field(default_factory=list)

    def __repr__(self) -> str:
        s: str = f"{' '*(3 if (self.name != 'base_form') else 0)}|"
        ret: str = ""
        if self.name != "base_form":
            ret += f"{s} {self.name}\n"
        ret += f"{s} "
        ret += f"DATA: Spawn:{bool_square(len(self.spawn_pool))} "
        ret += f"S:{self.__square_atr(self.species)}/{self.__square_atr(self.species_additions)}:SA "

        if not (
            (self.animation is None)
            and (self.model is None)
            and (self.poser is None)
            and (not self.resolvers)
            and (self.texture is None)
            and (self.texture_shiny is None)
            and (not self.textures_extra)
        ):
            ret += f"\n{s} "
            ret += "LOOKS: "
            ret += f"Res:{bool_square(len(self.spawn_pool))} "
            ret == f"Anim:{self.__square_atr(self.animation)} "
            ret += f"Mod:{self.__square_atr(self.model)} "
            ret += f"Pos:{self.__square_atr(self.poser)} "
            ret += f"  T:{self.__square_atr(self.texture)} "
            ret += f"Ts:{self.__square_atr(self.texture_shiny)} "
            ret += (
                f"Tx:{'|' * len(self.textures_extra)}"
                if len(self.textures_extra)
                else ""
            )
        ret += f"\n{s} {'-' * 10}"
        return ret

    def __square_atr(self, val: Any) -> str:
        return bool_square(val is not None)


@dataclass
class Pokemon:
    internal_name: str
    name: str | None = None
    dex_id: int | None = None

    features: list[str] = field(default_factory=list)
    forms: dict[str, PokemonForm] = field(default_factory=dict)

    def __repr__(self) -> str:
        ret: str = f"#{self.dex_id} - {self.name if self.name is not None else self.internal_name}"
        for f in self.forms.values():
            ret += "\n"
            ret += repr(f)
        return ret


@dataclass
class PackLocations:
    animations: Path | None = None
    models: Path | None = None
    posers: Path | None = None
    resolvers: Path | None = None

    textures: Path | None = None

    lang: Path | None = None

    spawn_pool_world: Path | None = None
    species: Path | None = None
    species_additions: Path | None = None
    species_features: Path | None = None
    species_features_assignments: Path | None = None


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

        self.is_base: bool = False

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
        if (not (self.folder_location / "pack.mcmeta").exists()) and (
            self.folder_location / "kotlin"
        ).exists():
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

    def _get_feature_assignments(self) -> None:  # STEP 0b #TODO
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
        self._get_data_species()
        self._get_data_species_additions()

        self._get_feature_assignments()

        self._get_data_spawn()

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
                    dex_id=data["nationalPokedexNumber"],
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
                except UnicodeDecodeError as _:
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
            return

        for t in self.component_location.resolvers.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except UnicodeDecodeError as _:
                    continue

                # ---------------
                # ---------------
                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    # ============================================================

    def display(self, pagination: int | None = None) -> None:
        for i, p in enumerate(
            sorted(self.pokemon.values(), key=lambda item: item.dex_id)
        ):
            print(p)
            if (pagination is not None) and (not (i % pagination)) and i:
                _ = input("Press any key to continue..")
                print(f"\033[A\r{' '*40}\r", end="")


class Menu:
    def __init__(self):
        working_dir: str = ""

    def __start(self):
        dir_name = filedialog.askdirectory()


if __name__ == "__main__":
    working_dir = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/cobblemon-main"
    )

    p2 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/AlolaMons_v1.3.zip"
    )

    p3 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cobblemon-fabric-1.5.2+1.20.1.jar"
    )
    p4 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Dracomon_0.6.10.zip"
    )

    p5 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/z_AllTheMons-Release4-Version55.zip"
    )

    # p = Pack(folder_location=working_dir)
    p = Pack(zip_location=p5)

    p._run()
    from pprint import pprint

    p.display(10)

    print(len(p.pokemon.values()))
    # print(p.pokemon["tauros"])
    # print(p.pokemon["vikavolt"].forms[0])
    pprint(list(p.features.values()))
    # pprint(p.feature_assignments)
