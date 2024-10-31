from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tkinter import filedialog
from typing import Any, Generator, Iterable, Literal, LiteralString, Optional
import json
from json import JSONDecodeError
import zipfile
import shutil
from utils.cli_utils.keypress import positive_int_choice
from utils.safe_parse_deco import safe_parse_per_file
from utils.cli_utils.keypress import clear_line
from constants.char_constants import TextSymbols
from utils.cli_utils.generic import bool_square, line_header
from utils.directory_utils import clear_empty_dir
from classes.pokemon_form import PokemonForm, ResolverEntry
from classes.pokemon import Pokemon
from classes.pack import Pack
from classes.sounds import SoundEntry, SoundPack
from classes.evolutions import EvolutionEntry, EvolutionCollection
from classes.combiner import Combiner
from classes.base_classes import (
    bcfo,
    FeatureType,
    Feature,
    FeatureAssignment,
    LangEntry,
    LangResultEntry,
)
from constants.runtime_const import DEBUG


# TODO previous choice(s)
# stack and push pop, and move, etc

# TODO ...merging?

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
        # try:
        comb = Combiner()
        comb.run()
        # except Exception as e:
        #     print(f"\n\n{'='*15}\nEXCEPTION\n{'='*15}\n\n")
        #     print(e)
        _ = input("\n\nPress [Enter] to exit..")
    elif RUN_TYPE == 3:
        p = Pack(
            zip_location=Path(
                "F:/Users/Main/Desktop/mc_palette/mod_workshop/resource packs/cobble_2_0/AlolaMons_v1.3.zip",
            )
        )
        p.run()
        p.display()
        p.export(selected=False)
