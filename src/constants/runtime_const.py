from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

from utils.cli_utils.keypress import clear, keypress
from utils.text_utils import bcolors, c_text

DEBUG: bool = False


@dataclass
class SettingMeta:
    """Metadata for each setting"""

    hidden: bool = False
    after_spacer: bool = False  # Add spacer before this setting


class CrOpType(Enum):
    PICK = 0
    MERGE = 1


@dataclass
class CRSettings:
    OP_MODE: CrOpType = CrOpType.MERGE
    KEEP_DUPLICATE_SAS_ON_MOVE: bool = True
    KEEP_DUPLICATE_SPAWNS_ON_MOVE: bool = True

    POKEDEX_FIX: bool = True
    EXCLUDE_PSEUDOFORMS: bool = True

    PROCESS_MODS: bool = False

    COMBINE_POKEMON_MOVES: bool = True

    SPECIES_STRICT_KEY_MATCH: bool = False
    SHOW_WARNINGS: bool = True
    SHOW_HELPER_TEXT: bool = True

    AUTO_START: bool = False


SETTINGS_DEPENDENCIES = {
    "EXCLUDE_PSEUDOFORMS": lambda s: s.POKEDEX_FIX,
    "KEEP_DUPLICATE_SAS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.PICK,
    "KEEP_DUPLICATE_SPAWNS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.PICK,
}

SETTINGS_META = {
    # Hidden settings
    "SPECIES_STRICT_KEY_MATCH": SettingMeta(hidden=True),
    "AUTO_START": SettingMeta(hidden=True),
    # "SHOW_WARNING": SettingMeta(hidden=True),
    # Spacers
    "POKEDEX_FIX": SettingMeta(after_spacer=True),
    "PROCESS_MODS": SettingMeta(after_spacer=True, hidden=True),
    "COMBINE_POKEMON_MOVES": SettingMeta(after_spacer=True),
}

SETTINGS_META_ADV = {
    # Hidden settings
    "SPECIES_STRICT_KEY_MATCH": SettingMeta(hidden=True),
    "AUTO_START": SettingMeta(hidden=True),
    # "SHOW_WARNING": SettingMeta(hidden=True),
    # Spacers
    "POKEDEX_FIX": SettingMeta(after_spacer=True),
    "PROCESS_MODS": SettingMeta(after_spacer=True),
    "COMBINE_POKEMON_MOVES": SettingMeta(after_spacer=True),
}


def settings_menu(
    settings: CRSettings,
    show_hidden: bool = False,
    dependencies: Dict = SETTINGS_DEPENDENCIES,
    meta: Dict = SETTINGS_META,
) -> Optional[CRSettings]:
    """
    Interactive menu for modifying settings with dependencies.

    Args:
        settings: CRSettings object to modify
        show_hidden: Whether to show hidden settings
        dependencies: Dictionary of setting dependencies
        meta: Dictionary of setting metadata

    Returns:
        Modified settings object, or None if cancelled
    """
    selected_index = 0

    def get_visible_settings() -> List[str]:
        all_settings = [
            attr for attr in vars(settings).keys() if not attr.startswith("_")
        ]
        if show_hidden:
            return all_settings
        return [s for s in all_settings if not meta.get(s, SettingMeta()).hidden]

    settings_list = get_visible_settings()

    def get_setting_value(name: str) -> Union[bool, Enum]:
        return getattr(settings, name)

    def is_setting_enabled(name: str) -> bool:
        if name not in dependencies:
            return True
        return dependencies[name](settings)

    def toggle_setting(name: str):
        current_value = get_setting_value(name)
        if isinstance(current_value, bool):
            setattr(settings, name, not current_value)
        elif isinstance(current_value, Enum):
            enum_class = type(current_value)
            current_index = list(enum_class).index(current_value)
            next_index = (current_index + 1) % len(enum_class)
            setattr(settings, name, list(enum_class)[next_index])

    while True:
        clear()

        print("=== Settings ===\n")

        visible_index = 0
        for setting_name in settings_list:
            # Add spacer if needed
            if meta.get(setting_name, SettingMeta()).after_spacer:
                print("")

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
            prefix = ">" if visible_index == selected_index else " "
            line = f"{prefix} {display_name}: {value_text}"

            # Apply color based on state
            if not enabled:
                print(c_text(line, color=bcolors.FAIL))
            elif visible_index == selected_index:
                print(c_text(line, color=bcolors.OKCYAN))
            else:
                print(line)

            visible_index += 1

        print("\n\n↑/↓: Navigate | Space: Toggle/Cycle | Enter: Confirm | ESC: Cancel\n")

        key = keypress()

        if key == "esc":
            return None
        elif key == "enter":
            return settings
        elif key == "up" and selected_index > 0:
            selected_index -= 1
        elif key == "down" and selected_index < len(settings_list) - 1:
            selected_index += 1
        elif key == "space":
            setting_name = settings_list[selected_index]
            if is_setting_enabled(setting_name):
                toggle_setting(setting_name)


gcr_settings = CRSettings()
