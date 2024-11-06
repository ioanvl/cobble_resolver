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

    MERGE_MOVES: bool = False


gcr_settings = CRSettings()
