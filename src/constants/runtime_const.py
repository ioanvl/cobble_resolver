from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

from utils.cli_utils.keypress import clear, keypress
from utils.text_utils import bcolors, c_text

DEBUG: bool = False


class SettingsMetaType(Enum):
    OFF = 0
    ON = 1


class CrOpType(Enum):
    CHOOSE = 0
    MERGE = 1


@dataclass
class SettingMeta:
    """Metadata for each setting"""

    hidden: bool = False
    after_spacer: bool = False  # Add spacer before this setting


@dataclass
class CRSettings:
    OP_MODE: "CrOpType" = CrOpType.MERGE
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
    AUTO_LOAD_ORDER_MODE: bool = False
    ALTERNATE_ICON: bool = False

    SHOW_ADVANCED_SETTINGS: SettingsMetaType = SettingsMetaType.OFF


SETTINGS_DEPENDENCIES = {
    "EXCLUDE_PSEUDOFORMS": lambda s: s.POKEDEX_FIX,
    "KEEP_DUPLICATE_SAS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.CHOOSE,
    "KEEP_DUPLICATE_SPAWNS_ON_MOVE": lambda s: s.OP_MODE == CrOpType.CHOOSE,
}

SETTINGS_META = {
    # Hidden settings
    "KEEP_DUPLICATE_SAS_ON_MOVE": SettingMeta(hidden=True),
    "KEEP_DUPLICATE_SPAWNS_ON_MOVE": SettingMeta(hidden=True),
    "SPECIES_STRICT_KEY_MATCH": SettingMeta(hidden=True),
    "AUTO_START": SettingMeta(hidden=True),
    # Spacers
    "AUTO_LOAD_ORDER_MODE": SettingMeta(after_spacer=True),
    "POKEDEX_FIX": SettingMeta(after_spacer=True),
    "PROCESS_MODS": SettingMeta(after_spacer=True, hidden=True),
    "COMBINE_POKEMON_MOVES": SettingMeta(after_spacer=True),
    "SHOW_WARNINGS": SettingMeta(after_spacer=True),
    "SHOW_ADVANCED_SETTINGS": SettingMeta(after_spacer=True),
}

SETTINGS_META_ADV = {
    # Hidden settings
    "SPECIES_STRICT_KEY_MATCH": SettingMeta(hidden=True),
    "AUTO_START": SettingMeta(hidden=True),
    # Spacers
    "AUTO_LOAD_ORDER_MODE": SettingMeta(after_spacer=True),
    "POKEDEX_FIX": SettingMeta(after_spacer=True),
    "PROCESS_MODS": SettingMeta(after_spacer=True),
    "COMBINE_POKEMON_MOVES": SettingMeta(after_spacer=True),
    "SHOW_WARNINGS": SettingMeta(after_spacer=True),
    "SHOW_ADVANCED_SETTINGS": SettingMeta(after_spacer=True),
}

_setting_meta_dict = {
    0: SETTINGS_META,
    1: SETTINGS_META_ADV,
}


def settings_menu(
    settings: CRSettings,
    dependencies: Dict = SETTINGS_DEPENDENCIES,
) -> Optional[CRSettings]:
    """
    Interactive menu for modifying settings with dependencies.

    Args:
        settings: CRSettings object to modify
        dependencies: Dictionary of setting dependencies

    Returns:
        Modified settings object, or None if cancelled
    """
    selected_index = 0

    def get_visible_settings() -> List[str]:
        all_settings = [
            attr for attr in vars(settings).keys() if not attr.startswith("_")
        ]
        meta = _setting_meta_dict[settings.SHOW_ADVANCED_SETTINGS.value]
        return [s for s in all_settings if not meta.get(s, SettingMeta()).hidden]

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

        visible_settings = get_visible_settings()
        if selected_index >= len(visible_settings):
            selected_index = 0  # Reset the cursor position

        visible_index = 0
        for setting_name in visible_settings:
            # Add spacer if needed
            meta = _setting_meta_dict[settings.SHOW_ADVANCED_SETTINGS.value]
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

        print("\n\n↑/↓: Navigate | Space: Toggle/Cycle | Enter/ESC: Return \n")

        key = keypress()

        if key == "esc":
            return None
        elif key == "enter":
            return settings
        elif key == "up" and selected_index > 0:
            selected_index -= 1
        elif key == "down" and selected_index < len(visible_settings) - 1:
            selected_index += 1
        elif key == "space":
            toggle_setting(visible_settings[selected_index])


gcr_settings = CRSettings()
