from dataclasses import dataclass
from enum import Enum
from typing import Any

square_f = "\u25A3"
square_e = "\u25A1"


def bool_square(inp: bool = False) -> str:
    return square_f if inp else square_e


@dataclass
class bco:
    pass


class bcfo(bco):
    file_path: str
    source: dict


class FeatureType(Enum):
    FLAG = 1
    CHOICE = 2


class Feature(bcfo):
    name: str
    keys: list[str]
    feat_type: FeatureType


class PokemonForm(bco):
    aspect: str | None

    name: str
    dex_id: int

    # looks
    animation: bcfo | None
    model: bcfo | None
    poser: bcfo | None
    resolver: bcfo | None

    texture: str | None
    texture_shiny: str | None
    textures_extra: list[str]

    # data
    species: bcfo | None
    species_additions: bcfo | None

    spawn_pool: bcfo | None

    def __repr__(self) -> str:
        s: str = f"{' '*(3 if self.aspect is not None else 0)}|"
        ret: str = f"{s} #{self.dex_id} {self.name}"
        ret += f"\n{s} "
        ret += f"DATA: Spawn:{self.__square_atr(self.spawn_pool)} "
        ret += f"S:{self.__square_atr(self.species)}/{self.__square_atr(self.species_additions)}:SA "

        ret += f"\n{s} "

        ret += f"LOOKS: Anim:{self.__square_atr(self.animation)} "
        ret += f"Mod:{self.__square_atr(self.model)} "
        ret += f"Pos:{self.__square_atr(self.poser)} "
        ret += f"Res:{self.__square_atr(self.resolver)} "
        ret += f"  T:{self.__square_atr(self.texture)} "
        ret += f"Ts:{self.__square_atr(self.texture_shiny)} "
        ret += (
            f"Tx:{'|' * len(self.textures_extra)}" if len(self.textures_extra) else ""
        )
        return ret

    def __square_atr(val: Any) -> str:
        return bool_square(val is not None)


class Pokemon:
    name: str
    dex_id: int

    features: list[Feature]
    forms: list[PokemonForm]

    def __repr__(self) -> str:
        ret: str = ""
        for f in self.forms:
            ret += repr(f)
            ret += "\n"
        return ret


class Pack:
    def __init__(
        self,
        zip_location: str | None = None,
        folder_location: str | None = None,
    ) -> None:
        self.zip_location = zip_location
        self.folder_location = folder_location

        self.name: str

        self.pokemon: list[Pokemon] = []
        self.features: list[Feature] = []
