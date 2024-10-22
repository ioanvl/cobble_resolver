from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, LiteralString
import json
from json import JSONDecodeError
import zipfile

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
class ResolverEntry:
    order: int
    textures: set[Path] = field(default_factory=set)
    models: set[Path] = field(default_factory=set)
    posers: set[Path] = field(default_factory=set)
    animations: set[Path] = field(default_factory=set)

    has_shiny: bool = False

    aspects: set[str] = field(default_factory=set)

    requested_animations: set[str] = field(default_factory=set)
    # present_animations: set[str] = field(default_factory=set)

    def __repr__(self) -> str:
        res: str = ""
        res += f"M:{bool_square(len(self.models))} | "

        res += f"P:{bool_square(len(self.posers))} "
        res += f"A:{bool_square(len(self.animations))} | "

        res += f"T:{bool_square(len(self.textures))} "
        res += f"Ts:{bool_square(self.has_shiny)} "

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

        self.present_animations: dict[str, dict[str, set[str]]] = dict()

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
        self._get_data_species()
        self._get_data_species_additions()

        self._get_feature_assignments()

        self._get_data_spawn()

        self._get_looks_resolvers()
        self._get_looks_animations()

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

        for t in self.component_location.posers.rglob("*.json"):
            self.component_location.posers_dict[t.stem] = t

        for t in self.component_location.models.rglob("*.json"):
            self.component_location.models_dict[t.stem] = t

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

    def _resolve_requested_animations(self) -> None:  # TODO
        pass

    def _get_looks_animations(self) -> None:  # STEP 2b
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

    # ============================================================

    def display(self, pagination: int | None = None) -> None:
        for i, p in enumerate(
            sorted(
                self.pokemon.values(),
                key=lambda item: (item.dex_id, item.internal_name),
            )
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
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/Cobble-Remodels_v5.1.zip"
    )

    p5 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/z_AllTheMons-Release4-Version55.zip"
    )

    p6 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/pokeinsanoV1.7.zip"
    )

    p7 = Path(
        "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/MegamonsFabric-1.2.1.jar"
    )

    p = Pack(folder_location=working_dir)
    # p = Pack(zip_location=p6)

    p._run()
    from pprint import pprint

    p.display()

    # print(p.pokemon["eiscue"].forms["base_form"].resolver_assignments)

    print(len(p.pokemon.values()))
    # print(p.pokemon["tauros"])
    # print(p.pokemon["vikavolt"].forms[0])
    pprint(list(p.features.values()))
    # pprint(p.feature_assignments)
