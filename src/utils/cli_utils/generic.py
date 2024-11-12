from typing import Literal

from constants.text_constants import HelperText, TextSymbols
from utils.cli_utils.keypress import _keypress, clear, keypress
from utils.text_utils import bcolors, c_text


def bool_square(inp: bool = False) -> str:
    return TextSymbols.square_f if inp else TextSymbols.square_e


def line_header(text: str = "") -> None:
    print(f"\n#{'='*25}\n#  {text}\n#{'='*25}\n")


def pack_name_choice(text: str = ""):
    print(c_text(f"={'-'*15}", color=bcolors.WARNING))
    print(f"Selected: [{text}]")
    print(c_text(f"={'-'*15}", color=bcolors.WARNING))
    print("=" * 25)


_help_menu_index = {
    "General Operation": HelperText.GENERIC_HELP,
    "Output": HelperText.OUTPUT_HELP,
    "Pack View": [HelperText.PACK_VIEW_HELP, HelperText.PACK_VIEW_HELP_2],
    "Pack Choices": [HelperText.PACK_CHOICES, HelperText.PACK_CHOICES_2],
    "Load Order": HelperText.LOAD_ORDER,
    "Settings": HelperText.SETTINGS_HELP,
}


def display_help_menu():
    while True:
        clear()
        print("\n".join([f"{i+1}. {v}" for i, v in enumerate(_help_menu_index.keys())]))

        _inp = keypress("\nPress Num[#]: Display help option, [ESC/Enter]:Return ")

        if _inp in ["enter", "esc"]:
            clear()
            return
        try:
            _inp = int(_inp)
        except Exception:
            continue
        if _inp > 0 and _inp <= len(_help_menu_index.keys()):
            displa_text_and_wait_for_enter(
                _help_menu_index[list(_help_menu_index.keys())[_inp - 1]]
            )


def displa_text_and_wait_for_enter(text: str | list[str]) -> None:
    if isinstance(text, str):
        text = [text]
    for _t in range(len(text)):
        clear()
        print(text[_t])
        _label: Literal["retutn"] | Literal["continue"] = (
            "retutn" if (_t == (len(text) - 1)) else "continue"
        )
        print(f"\n\n{'-'*35}\nPress [ESC/Enter] to {_label}..")
        while True:
            _inp = _keypress()
            if _inp in ["enter", "esc"]:
                break
