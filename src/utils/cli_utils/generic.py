from constants.text_constants import TextSymbols


def bool_square(inp: bool = False) -> str:
    return TextSymbols.square_f if inp else TextSymbols.square_e


def line_header(text: str = "") -> None:
    print(f"\n#{'='*25}\n#  {text}\n#{'='*25}\n")
