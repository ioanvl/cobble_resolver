from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, Iterable, Literal, LiteralString, Optional
import json
from json import JSONDecodeError
import zipfile
import shutil
from cli_utils import positive_int_choice

DEBUG = False

square_f = "\u25a3"
square_e = "\u25a1"
check_mark = "\u2713"
clear_line = f"\033[A\r{' '*60}\r"

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


def line_header(text: str = ""):
    print(f"\n#{'='*25}\n#  {text.capitalize()}\n#{'='*25}\n")


def clear_empty_dir(
    s_path: Path, verbose: bool = False, items_to_delete: list[str] = list()
):
    temp = [x for x in s_path.iterdir()]
    for item in temp:
        if item.name in items_to_delete:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        if item.is_dir():
            clear_empty_dir(s_path=item, verbose=verbose)
            if not len([x for x in item.rglob("*")]):
                item.rmdir()


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
    incl_pokemon: list[str]


@dataclass
class LangEntry:
    name: str
    file_path: Path
    source: dict
    incl_pokemon: set[str] = field(default_factory=set)


@dataclass
class LangResultEntry:
    name: str
    data: dict


@dataclass
class SpawnEntry:
    file_path: Path


@dataclass
class ResolverEntry:
    order: int
    own_path: Path | None = None
    models: set[Path] = field(default_factory=set)

    posers: set[Path] = field(default_factory=set)
    animations: set[Path] = field(default_factory=set)

    textures: set[Path] = field(default_factory=set)
    has_shiny: bool = False

    aspects: set[str] = field(default_factory=set)

    requested_animations: dict[str, dict[str, bool]] = field(default_factory=dict)
    # TODO add warning for missing animations

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

    def get_all_paths(self) -> set[Path]:
        res: set[Path] = set()
        res.add(self.own_path)
        for x in [self.models, self.posers, self.animations, self.textures]:
            res.update(x)
        return res


@dataclass
class EvolutionEntry:
    from_pokemon: str
    to_pokemon: str
    file_path: Path
    is_addition: bool = False

    def __eq__(self, value: "EvolutionEntry") -> bool:
        return (
            (self.from_pokemon == value.from_pokemon)
            and (self.to_pokemon == value.to_pokemon)
            and (self.file_path == value.file_path)
            and (self.is_addition == value.is_addition)
        )

    def __hash__(self) -> int:
        return hash(
            (self.from_pokemon, self.to_pokemon, self.file_path, self.is_addition)
        )


@dataclass
class EvolutionCollection:
    evolutions: set[EvolutionEntry] = field(default_factory=set)

    def get_evolutions(
        self, source: str | None = None, result: str | None = None
    ) -> list[EvolutionEntry]:
        res: list[EvolutionEntry] = list()
        if source:
            res.extend(
                [
                    ev
                    for ev in self.evolutions
                    if (
                        (ev.from_pokemon == source)
                        or (ev.from_pokemon.startswith(f"{source}_"))
                    )
                ]
            )
        if result:
            res.extend(
                [
                    ev
                    for ev in self.evolutions
                    if (
                        (ev.to_pokemon == result)
                        or (ev.to_pokemon.startswith(f"{result}_"))
                    )
                ]
            )
        return res

    def add(self, ev: EvolutionEntry) -> None:
        self.evolutions.add(ev)
        if (ev.from_pokemon is None) or (ev.to_pokemon is None):
            pass

    def remove(self, ev: EvolutionEntry) -> None:
        self.evolutions.remove(ev)


# TODO multiple sources on each location
# TODO sounds
# TODO pokedex fix

# TODO previous choice(s)
# stack and push pop, and move, etc

# TODO ...merging?


@dataclass
class PokemonForm:
    name: str | None = None

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
            ret += f"{s} {self.name if self.name else self.aspects}\n"
        ret += f"{s} "
        ret += f"DATA: Spawn:{bool_square(len(self.spawn_pool))} | "
        ret += f"S:{self.__square_atr(self.species)}"
        ret += f"/{self.__square_atr(self.species_additions)}:SA "

        if self.name == "base_form" and (self.parent_pokemon is not None):
            if self.parent_pokemon.sa_transfers_received:
                ret += " +SA"

            if self.parent_pokemon.requested:
                ret += " +Req"
                if req_diff := (
                    self.parent_pokemon.requested
                    - self.parent_pokemon.request_transfered
                ):
                    ret += f"[{req_diff}]"
                else:
                    ret += f"[{check_mark}]"

        ret += f"\n{s} {'-' * 10}"
        return ret

    @property
    def comp_stamp(self) -> list[bool]:
        res = list()
        res.append(self.has_spawn())
        res.append(self.has_species_data())
        res.append(self.species_additions is not None)
        x = bool(len(self.resolver_assignments))
        res.append(x)
        if x:
            r: list[bool] = list(self._get_resolvers().values())[0].comp_stamp
            res.extend(r)

        else:
            res.extend([False, False, False, False, False])

        return res

    def get_all_paths(self) -> list[Path]:
        res: set[Path] = set()
        for x in [self.species, self.species_additions]:
            if x:
                res.add(x.file_path)
        for s in self.spawn_pool:
            res.add(s)
        if self.parent_pokemon:
            for i in self.resolver_assignments:
                res.update(self.parent_pokemon.resolvers[i].get_all_paths())
        return list(res)

    def is_complete(self) -> bool:
        return (
            self.has_spawn()
            and self.has_species_data()
            and self.is_graphically_complete()
        )

    def is_addition(self, only: bool = True) -> bool:
        stamp = self.comp_stamp
        flag2 = (sum(stamp) == 1) if only else (not stamp[1])
        return stamp[2] and flag2

    def is_species(self, only: bool = True) -> bool:
        stamp = self.comp_stamp
        flag2 = (sum(stamp) == 1) if only else (not stamp[2])
        return stamp[1] and flag2

    def is_data(self) -> bool:
        stamp = self.comp_stamp
        return stamp[1] and stamp[2] and (sum(stamp) == 2)

    def has_spawn(self) -> bool:
        return bool(len(self.spawn_pool))

    def has_species_data(self) -> bool:
        return self.species is not None

    def has_addition_data(self) -> bool:
        return self.species_additions is not None

    def has_sp_data(self) -> bool:
        return self.has_species_data() or self.has_addition_data()

    def is_graphically_complete(self) -> bool:
        stamp = self.comp_stamp
        return stamp[3] and stamp[4] and stamp[6] and stamp[7] and stamp[8]

    def has_graphics(self) -> bool:
        stamp: list[bool] = self.comp_stamp
        if stamp[3]:
            if any(stamp[4:]):
                return True
        return False

    def _get_resolvers(self) -> dict[int, ResolverEntry]:
        if self.parent_pack is None:
            return {}
        return {r: self.parent_pokemon.resolvers[r] for r in self.resolver_assignments}

    def is_requested(self) -> bool:
        if self.parent_pokemon:
            return bool(
                self.parent_pokemon.requested
                and (
                    self.parent_pokemon.requested
                    - self.parent_pokemon.request_transfered
                )
            )
        return False

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

    requested: int = 0
    request_transfered: int = 0

    sa_transfers_received: set[Path] = field(default_factory=set)

    evo_to: int = 0
    evo_from: int = 0

    def select(self) -> None:
        if not self.parent_pack:
            return  # means the pack hasnt been processed
        self.selected = True
        # self._mark_requests()

    def _mark_requests(self) -> None:
        evo_requests: list[EvolutionEntry] = (
            self.parent_pack.registered_evolutions.get_evolutions(
                result=self.internal_name
            )
        )

        for entry in evo_requests:
            if entry.is_addition:
                self.sa_transfers_received.add(entry.file_path)

            pre_evolution = entry.from_pokemon
            pre_evolution = pre_evolution.split("_")[0]

            if pre_evolution in self.parent_pack.pokemon:
                self.parent_pack.pokemon[pre_evolution].requested += 1
                if entry.is_addition:
                    self.parent_pack.pokemon[pre_evolution].request_transfered += 1

    def _is_requested(self) -> bool:
        return bool(self.requested - self.request_transfered)

    def get_all_export_paths(self):
        res: set[Path] = set()
        for form in self.forms.values():
            res.update(form.get_all_paths())
        res.update(self.sa_transfers_received)
        for fa in self.parent_pack.feature_assignments:
            if self.internal_name in fa.incl_pokemon:
                res.add(fa.file_path)
        return list(res)

    def get_all_paths(self) -> set[Path]:
        res: set[Path] = set()
        res.update(self.get_all_export_paths())
        for r in self.resolvers.values():
            res.update(r.get_all_paths())
        return res

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
    home_location: Path | None = None

    resolvers: set[Path] = field(default_factory=set)
    models: set[Path] = field(default_factory=set)
    textures: Path | None = None
    animations: set[Path] = field(default_factory=set)
    posers: set[Path] = field(default_factory=set)

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
            bool(self.resolvers)
            or bool(self.models)
            or bool(self.animations)
            or bool(self.posers)
            or (self.textures is not None)
            or (self.lang is not None)
            or (self.species is not None)
            or (self.species_additions is not None)
            or (self.spawn_pool_world is not None)
            or (self.species_features is not None)
            or (self.species_features_assignments is not None)
        )

    def _delete_registered_paths(self) -> None:
        for x in [
            self.lang,
            self.textures,
            self.species,
            self.species_additions,
            self.spawn_pool_world,
            self.species_features,
            self.species_features_assignments,
        ]:
            if x and x.exists() and x.is_dir():
                shutil.rmtree(x)
        for y in [
            self.animations,  #
            self.models,  #
            self.posers,  #
            self.resolvers,  #
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

        self.lang_entries: list[LangEntry] = list()
        self.registered_evolutions: EvolutionCollection = EvolutionCollection()

        self.is_base: bool = False
        self.is_mod: bool = False

        self.verbose: bool = False

    def run(self) -> None:
        self._prepare()
        self._process()

    # ============================================================

    def get_all_paths(self) -> None:
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

        _overall_set = self.get_all_paths()

        # -----------------------------------------
        path_set: set[Path] = set()
        delete_set: set[Path] = set()
        mflag = self.is_base or self.is_mod
        if (not mflag) or (mflag and export_mods):
            for pok in self.pokemon.values():
                if pok.selected or (not selected):
                    path_set.update(pok.get_all_export_paths())
                else:
                    delete_set.update(pok.get_all_export_paths())
            # for fa in self.feature_assignments:  #TODO....maybe?
            #     path_set.add(fa.file_path)

        delete_set = delete_set.difference(path_set)
        c = 0
        for p in path_set:
            if p:
                np = output_path / p.relative_to(self.folder_location)
                np.parent.mkdir(parents=True, exist_ok=True)

                shutil.move(p, np)
                c += 1
        # -----------------------------------------
        if not export_path:
            self._export_langs()

        # -----------------------------------------
        del_flag = False
        try:
            for p in delete_set:
                if p:
                    p.unlink()

            self.component_location._delete_registered_paths()
            clear_empty_dir(
                s_path=self.folder_location, items_to_delete=["_MACOSX", ".DS_Store"]
            )
            del_flag = True
        except PermissionError:
            print(f"Could not delete unused files for {self.name}")
            if move_leftovers:
                print(".Partial pack will not be produced")
            del_flag = False
        # -----------------------------------------
        # for p_i in ["pack.png", "pack.mcmeta"]:
        #     if (p := (self.folder_location / p_i)).exists():
        #         p.unlink()

        if isinstance(move_leftovers, Path) and del_flag:
            if len(
                [
                    i
                    for i in self.folder_location.rglob("*")
                    if not str(i).endswith(("pack.mcmeta", "pack.png"))
                ]
            ):
                self._move_leftovers(export_path=move_leftovers)

        outp = f"{c} files moved "
        if d := (len(path_set) - c):
            outp += f"- {d} missed "
        outp += f"| {self.name}"
        print(outp)

    def _move_leftovers(self, export_path: Path) -> None:
        shutil.make_archive(
            f"{str((export_path / self.name))} - CORE_Edit",
            format="zip",
            root_dir=str(self.folder_location),
        )

    def _export_langs(self, export_path: Path) -> None:
        langs = self._get_lang_export()
        l_path = export_path / "assets" / "cobblemon" / "lang"
        l_path.mkdir(parents=True, exist_ok=True)
        for l_entry in langs:
            (l_path / f"{l_entry.name}").write_text(json.dumps(l_entry.data))

    def _get_lang_export(self) -> list[LangResultEntry]:
        selected = [p for p in self.pokemon if self.pokemon[p].selected]
        not_selected = [p for p in self.pokemon if (not self.pokemon[p].selected)]

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

    # ============================================================

    def _prepare(self) -> None:
        self._folder_setup()
        self._unpack()
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
            return

        if self.zip_location is not None:
            if self._extraction_path is None:
                self._extraction_path = self.zip_location.parent / ".temp"
            self.folder_location = self._extraction_path / self.zip_location.stem
            self.folder_location.mkdir(parents=True, exist_ok=True)

    def _unpack(self) -> None:
        if self.zip_location is None:
            return
        print(f"Unpacking {self.zip_location.name}")
        with zipfile.ZipFile(str(self.zip_location), "r") as zip_ref:
            zip_ref.extractall(self.folder_location)
        print(f"\033[A\r{' '*40}\r", end="")

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
            except:
                pass

    def _get_paths(self) -> None:
        val = PackLocations()
        if self.name.startswith("Genomo"):
            pass
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
                if (tmpast / "lang").exists():
                    val.lang = tmpast / "lang"
                if (tmpast / "textures" / "pokemon").exists():
                    val.textures = tmpast / "textures" / "pokemon"

        for data_candidate in [
            "data/cobblemon",
            "data",
        ]:
            data_flag = False
            if (temp_data := self.folder_location / data_candidate).exists():
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
        print(f"Processing.. {self.name}")
        self._get_features()
        self._get_pokemon()
        self._get_lang()

        self._stamp_forms()

        for p in self.pokemon.values():
            p._mark_requests()

        if not self.verbose:
            print(clear_line, end="")
            print(f"[{check_mark}] {self.name}")

    # ------------------------------------------------------------

    def _get_features(self) -> None:  # STEP 0
        if (self.component_location is None) or (
            self.component_location.species_features is None
        ):
            if self.verbose:
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

        if not self.verbose:
            print(clear_line, end="")

    def _get_feature_assignments(self) -> None:  # STEP 0b #TODO?
        if (self.component_location is None) or (
            self.component_location.species_features_assignments is None
        ):
            if self.verbose:
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
                    FeatureAssignment(
                        file_path=t,
                        source=data,
                        name=t.stem,
                        incl_pokemon=data.get("pokemon", list()),
                    )
                )

                # ---------------
                # process?
                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e
        if not self.verbose:
            print(clear_line, end="")

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
                except (UnicodeDecodeError, JSONDecodeError) as _:
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

    def _get_data_species(self) -> None:  # STEP 1
        """parse through species files"""
        if (self.component_location is None) or (
            self.component_location.species is None
        ):
            if self.verbose:
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
                self._register_evolutions(
                    data=data, name=pok.internal_name, file_path=t
                )

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e

        if not self.verbose:
            print(clear_line, end="")

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

    def _get_data_species_additions(self) -> None:  # STEP 1b
        if (self.component_location is None) or (
            self.component_location.species_additions is None
        ):
            if self.verbose:
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

                self._register_evolutions(
                    data=data, name=target, file_path=t, is_addition=True
                )

                # ---------------

            except Exception as e:
                print(f"\n\n{t}\n\n")
                raise e
        if not self.verbose:
            print(clear_line, end="")

    def _get_data_spawn(self) -> None:  # STEP 1c
        if (self.component_location is None) or (
            self.component_location.spawn_pool_world is None
        ):
            if self.verbose:
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

                    aspect = ""
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

                        # for form in self.pokemon[pok_name].forms.values():
                        #     if aspect in form.aspects:
                        #         form.spawn_pool.append(in_spawn_file)
                        #         form.spawn_pool = list(set(form.spawn_pool))
                        #         flag = True

                    if aspect:  # if you found an aspect, match it or create
                        flag = False
                        for form in self.pokemon[pok_name].forms.values():
                            if aspect in form.aspects:
                                form.spawn_pool.append(in_spawn_file)
                                form.spawn_pool = list(set(form.spawn_pool))
                                flag = True
                        if not flag:
                            new_form = PokemonForm(name=f"--{aspect}")
                            new_form.spawn_pool.append(in_spawn_file)
                            self.pokemon[pok_name].forms[new_form.name] = new_form

                    else:  # else add to primary
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
        if not self.verbose:
            print(clear_line, end="")

    # ------------------------------------------------------------

    def _get_looks_resolvers(self) -> None:  # STEP 2
        """STEP 2 - parse through resolvers"""
        if (self.component_location is None) or (not self.component_location.resolvers):
            if self.verbose:
                print("-- No Resolver Data")
            return
        print("-- Parsing Resolver Data")

        for t_set in self.component_location.posers:
            for t in t_set.rglob("*.json"):
                self.component_location.posers_dict[t.stem] = t

        for t_set in self.component_location.models:
            for t in t_set.rglob("*.json"):
                self.component_location.models_dict[t.stem] = t

        if self.component_location.textures:
            for t in self.component_location.textures.rglob("*.png"):
                self.component_location.textures_dict[t.stem] = t

        for t_set in self.component_location.resolvers:
            for t in t_set.rglob("*.json"):
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
                            min(min(list(self.pokemon[pok_name].resolvers.keys())), 0)
                            - 1
                        )

                    new_resolver_entry = ResolverEntry(order=order, own_path=t)
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
                        self.pokemon[pok_name].forms[
                            "base_form"
                        ].resolver_assignments.add(order)

                    self.pokemon[pok_name].resolvers[order] = new_resolver_entry

                    # ---------------

                except Exception as e:
                    print(f"\n\n{t}\n\n")
                    raise e
        if not self.verbose:
            print(clear_line, end="")

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

    def _get_looks_animations(self) -> None:  # STEP 3
        if (self.component_location is None) or (
            not self.component_location.animations
        ):
            if self.verbose:
                print("-- No Animations")
            return
        print("-- Parsing Animations")

        for t_e in self.component_location.animations:
            for t in t_e.rglob("*.json"):
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
        if not self.verbose:
            print(clear_line, end="")

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

    def _assign_evo_score(self):
        for entry in self.registered_evolutions.evolutions:
            if (x := self._cleanup_evo_name(entry.to_pokemon)) in self.pokemon:
                self.pokemon[x].evo_to += 1

            if (x := self._cleanup_evo_name(entry.from_pokemon)) in self.pokemon:
                self.pokemon[x].evo_from += 1

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
        print(
            f"\nPokemon: {len(self.pokemon)}  Forms: {sum([len(p.forms) for p in self.pokemon.values()])}"
        )


class Combiner:
    def __init__(self, dir_name: Path | None = None):
        if (not dir_name) or (not dir_name.exists()):
            self.dir_name = Path(filedialog.askdirectory())
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
        except:
            print("Failed preparing output folder")
            exit()

    def export(self) -> None:
        line_header("EXPORTING")
        for pack in self.packs:
            if pack.is_base or (pack.is_mod and (not self._process_mods)):
                continue
            pack.export(
                export_path=self.output_pack_path,
                move_leftovers=self.output_pack_path.parent,
            )

        self._export_langs(folder_path=self.output_pack_path)

        self._write_pack_mcmeta(folder_path=self.output_pack_path)

        try:
            shutil.move(
                Path("pack.png").resolve(), (self.output_pack_path / "pack.png")
            )
        except:
            print("Failed to get icon..")

        self._compress_pack(folder_path=self.output_pack_path)

        try:
            shutil.rmtree(str(self.dir_name / ".temp"))
        except:
            print(" -Could not remove temporary folder")

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
                max([p.pokemon[x].evo_from for p in self.packs if (x in p.pokemon)]),
                max(
                    [
                        (p.pokemon[x].requested - p.pokemon[x].request_transfered)
                        for p in self.packs
                        if (x in p.pokemon)
                    ]
                ),
                (
                    max([p.pokemon[x].evo_to for p in self.packs if (x in p.pokemon)])
                    + max(
                        [p.pokemon[x].evo_from for p in self.packs if (x in p.pokemon)]
                    )
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

    def _dual_choice(self, holder: dict[str, Pokemon]):
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

    def _dual_choice_against_base(self, holder: dict[str, Pokemon]):
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
    ):
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

    def _dual_choice_mod_and_pack(self, holder: dict[str, Pokemon]):
        if (
            sum(
                [
                    (p.parent_pack.is_base or p.parent_pack.is_mod)
                    for p in holder.values()
                ]
            )
            == 1
        ):
            fm = [
                p
                for p in holder.values()
                if (p.parent_pack.is_base or p.parent_pack.is_mod)
            ][0].forms["base_form"]
            fo = [
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
    ) -> tuple[str, Literal["G3-R"]] | tuple[None, None]:
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
    ) -> tuple[str, Literal["G5-R"]] | tuple[None, None]:
        if self._allow_risky_rules:
            if pok_mod.is_complete() and (
                (pok_other.has_graphics())
                and (pok_other.is_requested())
                and pok_other.has_spawn()
                and (not pok_other.has_sp_data())
            ):
                return (pok_other.parent_pack.name, "G5_2-R")
        return (None, None)

    def _dual_choice_mod_remodel(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5-R"]] | tuple[None, None]:
        if pok_mod.is_complete() and (
            (not pok_other.has_spawn())
            and (not pok_other.has_sp_data() and pok_other.is_graphically_complete())
        ):
            return (pok_other.parent_pack.name, "G5-R")
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

    # ------------------------------------------------------------

    def _cleanup(self) -> None:  # TODO
        pass


RUN_TYPE = 2
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
            p.run()
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
    elif RUN_TYPE == 3:
        p = Pack(
            zip_location=Path(
                "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/AlolaMons_v1.3.zip",
            )
        )
        p.run()
        p.display()
        p.export(selected=False)
