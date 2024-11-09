from dataclasses import dataclass
from enum import Enum

DEBUG = False


class CrOpType(Enum):
    PICK = 0
    MERGE = 1


@dataclass
class CRSettings:
    POKEDEX_FIX: bool = True
    OP_MODE: CrOpType = CrOpType.PICK

    PROCESS_MODS: bool = False

    COMBINE_EVOLUTIONS: bool = False
    COMBINE_POKEMON_MOVES: bool = False

    KEEP_DUPLICATE_SAS_ON_MOVE: bool = True
    KEEP_DUPLICATE_SPAWNS_ON_MOVE: bool = True

    SPECIES_STRICT_KEY_MATCH: bool = False


gcr_settings = CRSettings()
