from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from utils.cli_utils.keypress import clear, keypress
from utils.text_utils import bcolors, cprint

DEBUG = False


class CrOpType(Enum):
    PICK = 0
    MERGE = 1


@dataclass
class CRSettings:
    OP_MODE: CrOpType = CrOpType.PICK

    POKEDEX_FIX: bool = True
    EXCLUDE_PSEUDOFORMS: bool = True

    PROCESS_MODS: bool = False

    # COMBINE_EVOLUTIONS: bool = False
    COMBINE_POKEMON_MOVES: bool = False

    KEEP_DUPLICATE_SAS_ON_MOVE: bool = True
    KEEP_DUPLICATE_SPAWNS_ON_MOVE: bool = True

    SPECIES_STRICT_KEY_MATCH: bool = False

    SHOW_WARNING: bool = True


gcr_settings = CRSettings()


def settings_menu(settings: CRSettings) -> Optional[CRSettings]:
    """
    Interactive menu for modifying settings with dependencies.

    Args:
        settings: CRSettings object to modify

    Returns:
        Modified settings object, or None if cancelled
    """
    # Define dependencies and conditions for each setting
    dependencies = {
        "EXCLUDE_PSEUDOFORMS": lambda s: s.POKEDEX_FIX,
        "KEEP_DUPLICATE_SAS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.PICK,
        "KEEP_DUPLICATE_SPAWNS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.PICK,
    }

    working_settings = settings
    selected_index = 0
    settings_list = [attr for attr in vars(working_settings).keys()]

    def get_setting_value(name: str) -> Union[bool, Enum]:
        return getattr(working_settings, name)

    def is_setting_enabled(name: str) -> bool:
        if name not in dependencies:
            return True
        return dependencies[name](working_settings)

    def toggle_setting(name: str):
        current_value = get_setting_value(name)
        if isinstance(current_value, bool):
            setattr(working_settings, name, not current_value)
        elif isinstance(current_value, Enum):
            # For enums, cycle through values
            enum_class = type(current_value)
            current_index = list(enum_class).index(current_value)
            next_index = (current_index + 1) % len(enum_class)
            setattr(working_settings, name, list(enum_class)[next_index])

    while True:
        clear()

        print("=== Settings ===\n")

        for i, setting_name in enumerate(settings_list):
            value = get_setting_value(setting_name)
            enabled = is_setting_enabled(setting_name)

            # Format the setting name for display
            display_name = setting_name.replace("_", " ").title()

            # Format the value for display
            if isinstance(value, bool):
                value_text = "Enabled" if value else "Disabled"
            else:  # Enum
                value_text = value.name

            # Create the full line
            prefix = ">" if i == selected_index else " "
            line = f"{prefix} {display_name}: {value_text}"

            # Apply color based on state
            if not enabled:
                print(cprint(line, color=bcolors.FAIL))
            elif i == selected_index:
                print(cprint(line, color=bcolors.OKCYAN))
            else:
                print(line)

        print("\n\n↑/↓: Navigate | Space: Toggle/Cycle | Enter: Confirm | ESC: Cancel\n")

        key = keypress()

        if key == "esc":
            return None
        elif key == "enter":
            return working_settings
        elif key == "up" and selected_index > 0:
            selected_index -= 1
        elif key == "down" and selected_index < len(settings_list) - 1:
            selected_index += 1
        elif key == "space":
            setting_name = settings_list[selected_index]
            if is_setting_enabled(setting_name):
                toggle_setting(setting_name)


if __name__ == "__main__":
    # Example usage:`
    settings = CRSettings()
    new_settings = settings_menu(settings)
    if new_settings:
        print("Settings updated!")
    else:
        print("Operation cance`lled")
