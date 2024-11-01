from typing import LiteralString


class TextSymbols:
    square_f: str = "\u25a3"
    square_e: str = "\u25a1"
    check_mark: str = "\u2713"
    left_arrow: str = "\u2190"
    x_symbol: str = "\u0078"
    music_symbol: str = "\u266a"


class HelperText:
    AUTO_MANUAL_CHOISE: LiteralString = (
        f"\n\n{'='*40}\n\n"
        "CONTINUE WITH MANUAL RESOLUTION\n\n"
        "All rules that could be automatically applied are complete.\n\n"
        "The following packs need to be chosen manually\n"
        "On each entry, press the -number- of the pack you want to use"
        f"\n\n{'='*40}\n\n"
    )


class DefaultNames:
    BASE_FORM = "base_form"
    BASE_COBBLE_MOD = "BASE"
