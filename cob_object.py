from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any
import json
import zipfile
import os

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

    # duplicate: bool = False

    def __repr__(self) -> str:
        return f"{str(self.feat_type.name)[0:2]} - {self.name}"


@dataclass
class FeatureAssignment(bcfo):
    name: str


@dataclass
class SpawnEntry(bcfo):
    id: str


@dataclass
class PokemonForm:
    name: str

    aspect: list[str] = field(default_factory=list)
    # looks
    animation: bcfo | None = None
    model: bcfo | None = None
    poser: bcfo | None = None
    resolver: bcfo | None = None

    texture: str | None = None
    texture_shiny: str | None = None
    textures_extra: list[str] = field(default_factory=list)
    # data
    species: bcfo | None = None
    species_additions: bcfo | None = None

    spawn_pool: list[SpawnEntry] = field(default_factory=list)

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
            and (self.resolver is None)
            and (self.texture is None)
            and (self.texture_shiny is None)
            and (not self.textures_extra)
        ):
            ret += f"\n{s} "
            ret += f"LOOKS: Anim:{self.__square_atr(self.animation)} "
            ret += f"Mod:{self.__square_atr(self.model)} "
            ret += f"Pos:{self.__square_atr(self.poser)} "
            ret += f"Res:{self.__square_atr(self.resolver)} "
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
    forms: list[PokemonForm] = field(default_factory=list)

    def __repr__(self) -> str:
        ret: str = f"#{self.dex_id} - {self.name if self.name is not None else self.internal_name}"
        for f in self.forms:
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

        self.name: str

        self.pokemon: dict[str, Pokemon] = dict()
        self.features: list[Feature] = list()
        self.feature_assignments: list[FeatureAssignment] = list()

        self.is_base: bool = False

    def _run(self):
        self._prepare()
        self._process()

    # ============================================================

    def _prepare(self) -> None:
        self._folder_setup()
        self._unpack()
        self._determine_base()

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

    def _determine_base(self):
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

    # ============================================================

    def _process(self) -> None:
        self._get_paths()
        self._get_features()
        self._get_feature_assignments()
        self._get_pokemon()

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
        if (temp_data := self.folder_location / "data" / "cobblemon").exists():
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

    # ------------------------------------------------------------

    def _get_features(self) -> None:
        if (self.component_location is None) or (
            self.component_location.species_features is None
        ):
            return

        for t in self.component_location.species_features.iterdir():
            if t.suffix == ".json":
                with t.open() as f:
                    data = json.load(f)
                self.features.append(
                    Feature(
                        name=t.stem,
                        keys=data.get("keys", list()),
                        feat_type=FeatureType(data.get("type", "flag")),
                        file_path=t,
                        source=data,
                    )
                )

    def _get_feature_assignments(self) -> None:
        if (self.component_location is None) or (
            self.component_location.species_features_assignments is None
        ):
            print("NO FA")
            return

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

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    # ------------------------------------------------------------

    def _get_pokemon(self) -> None:
        self._get_data_species()

    def _get_data_species(self) -> None:
        if (self.component_location is None) or (
            self.component_location.species is None
        ):
            return

        for t in self.component_location.species.rglob("*.json"):
            try:
                try:
                    with t.open() as f:
                        data = json.load(f)
                except UnicodeDecodeError as _:
                    continue
                pok = Pokemon(
                    internal_name=t.stem,
                    name=data["name"],
                    dex_id=data["nationalPokedexNumber"],
                    features=data.get("features", list()),
                )

                pok.forms.append(
                    PokemonForm(
                        name="base_form",
                        species=bcfo(file_path=t, source=data),
                    )
                )

                forms: list = data.get("forms", list())
                for i_form in forms:
                    pok.forms.append(
                        PokemonForm(
                            name=i_form["name"],
                            aspect=(i_form.get("aspects", list())),
                            species=bcfo(file_path=t, source=i_form),
                        )
                    )

                self.pokemon[pok.internal_name] = pok
            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

    def _get_data_spawn(self) -> None:
        if (self.component_location is None) or (
            self.component_location.spawn_pool_world is None
        ):
            return

        for t in self.component_location.spawn_pool_world.rglob("*.json"):
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


class Menu:
    def __init__(self):
        working_dir: str = ""

    def __start(self):
        dir_name = filedialog.askdirectory()


if __name__ == "__main__":
    working_dir = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/cobblemon-main"
    )

    # working_dir = working_dir / "common" / "src" / "main" / "resources"

    p2 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/AlolaMons_v1.3.zip"
    )

    p3 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cobblemon-fabric-1.5.2+1.20.1.jar"
    )

    from glob import glob

    # print(working_dir)

    p = Pack(folder_location=working_dir)
    # p = Pack(zip_location=p2)

    p._run()
    from pprint import pprint

    for i in p.pokemon.values():
        print(i)
    print(len(p.pokemon.values()))
    # print(p.pokemon["tauros"])
    print(p.pokemon["vikavolt"].forms[0])
    pprint(p.features)
    # pprint(p.feature_assignments)
