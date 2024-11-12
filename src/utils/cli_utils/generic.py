from constants.text_constants import TextSymbols
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
