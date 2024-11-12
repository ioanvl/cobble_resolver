from typing import LiteralString

from constants.runtime_const import CrOpType
from utils.text_utils import bcolors, c_text


class TextSymbols:
    square_f: str = "\u25a3"
    square_e: str = "\u25a1"
    check_mark: str = "\u2713"
    left_arrow: str = "\u2190"
    x_symbol: str = "\u0078"
    music_symbol: str = "\u266a"


class DefaultNames:
    BASE_FORM = "base_form"
    BASE_COBBLE_MOD = "BASE"
    FINAL_PACK_NAME = "CobbleResolver_Pack"
    REMAINDER_PACK_PREFIX = "[CE]"
    ICON_NAME = "pack_icon"
    ALT_ICON = "alt_pack_icon"


class HelperText:
    AUTO_MANUAL_CHOISE: LiteralString = (
        f"\n\n{'='*40}\n\n"
        "CONTINUE WITH MANUAL RESOLUTION\n\n"
        "All rules that could be automatically applied are complete.\n\n"
        "The following entities need to be chosen manually\n"
        "On each entry, press the -number- of the pack you want to use"
        f"\n\n{'='*40}\n\n"
    )
    GENERIC_HELP = (
        "This utility reads addon packs made for Cobblemon and helps merge them "
        "avoiding graphical conflicts."
        "\n\n - Select a folder containing your addon packs."
        "\n - The Program will read all the pokemon contained in the packs "
        "and you will be able to choose between packs if theres is a conflict."
        "\n - The final packs will be in the output folder that is "
        "automatically created."
        "\n\nUse the packs from the Output folder and do NOT use the original ones you "
        "used for combining in your game."
        f"\n\n!! - It is {c_text("highly reccomended", bcolors.BOLD)} "
        "(though not necessary) to include the main \"Cobblemon\" mod, and any other "
        f"{c_text("mods (not packs)", bcolors.UNDERLINE)} that add pokemon "
        "(such as Megamons, etc..)"
        " - They greatly help in the processing/resolution later. Their files will "
        "NOT be included in the final pack"
    )

    OUTPUT_HELP = (
        f'In the output folder you will find a "{DefaultNames.FINAL_PACK_NAME}"'
        "zip. That contains all the pokemon for your game."
        "\nYou should include this "
        'in the "datapacks" folder of your save AND the "resourcepacks" '
        "folder of your game."
        "\n\nYou might also find a few more zips depending on the addon packs "
        "you combined."
        "\n\nThese will have a prefix like:"
        f"\n{DefaultNames.REMAINDER_PACK_PREFIX}[R]_some_addon_name.."
        f"\n{DefaultNames.REMAINDER_PACK_PREFIX}[D]_some_other_addon_name.."
        f"\n{DefaultNames.REMAINDER_PACK_PREFIX}[RD]_another_addon_name.."
        "\n\nSuch packs will be there if any of the packs you combined had "
        "extra things other than pokemon, like structures, items, loot tables etc. "
        f"{c_text("You need these packs too.", color=bcolors.UNDERLINE)}"
        "\n\nIf the prefix has an [R] you need that pack in your "
        f"{c_text("resourcepacks", bcolors.UNDERLINE)}, if [D], then you need it "
        f"in your {c_text("datapacks", bcolors.UNDERLINE)}, "
        f"if [RD] then in {c_text("both", bcolors.UNDERLINE)}"
    )

    PACK_VIEW_HELP = (
        'When choosing between conflicting packs, a "Pack/Pokemon view" '
        "will be shown, like the one bellow, with an entry for every pack that "
        "has the Pokemon."
        "\n\n▣/□ : Exists/doesnt exist - the entries bellow are just examples."
        "\n\n#549 - Lilligant"
        "\n[num#]. [addon_pack_name]    ← Name of the addon pack"
        "\n| DATA: Spawn:▣ | S:▣/□:SA | ♪:▣     ← Basic form"
        "\n| M:▣ | P:□ A:▣ | T:▣ Ts:▣"
        "\n| ----------"
        "\n   | Hisui                             ← Additional forms"
        "\n   | DATA: Spawn:▣ | S:▣/□:SA | ♪:▣"
        "\n   | M:▣ | P:□ A:□ | T:▣ Ts:▣"
        "\n   | ----------"
        "\n\nEach form shows info about the data/graphics it contains, e.g:"
        "\n\n| Hisui   ← Form name (if it cannot be determined you "
        "will see the aspect --name)"
        "\n   | DATA: Spawn:▣ | S:▣/□:SA | ♪:▣      ← Data Entry"
        "\n   | M:▣ | P:□ A:□ | T:▣ Ts:▣          ← Graphics Entry"
        "\n\nSome mons might have multiple graphics entries in a single form, "
        "if they have different graphics for male/female, for example."
    )
    PACK_VIEW_HELP_2 = (
        "The data and graphics lines contain information wether specific "
        "'parts' are added by the pack in question."
        "\n\n         Species file     Species Additions"
        "\n                    ↓     ↓"
        f"\n{c_text("| DATA: Spawn:▣ | S:▣/□:SA | ♪:▣", bcolors.BOLD)}"
        "\n                                ↑"
        "\n                   Constains Music files"
        "\n\n  Model          Basic & Shiny Textures"
        "\n    ↓               ↓    ↓"
        f"\n{c_text("| M:▣ | P:□ A:□ | T:▣ Ts:▣", bcolors.BOLD)}"
        # "\n| M:▣ | P:□ A:□ | T:▣ Ts:▣"
        "\n          ↑   ↑"
        "\n  Anim.Data & FIles"
    )

    PACK_CHOICES = (
        f"While going through the packs either in {CrOpType.CHOOSE.name} "
        f" or {CrOpType.MERGE.name} mode, when there is a conflict you will "
        "see a view containing entries for every pack that adds this pokemon."
        f"\n\nIn those options there might be a "
        f"{c_text(DefaultNames.BASE_COBBLE_MOD, bcolors.UNDERLINE)} option"
        " or others underlined. These are from the base mod or other mods respectivelly."
        "\nIf you choose one of these underlined ones, it is essentially like picking "
        '"no choise" as no files from these will be included in the final pack.'
    )

    PACK_CHOICES_2 = (
        "The view will look  something like this:"
        # 379 - Registeel
        "\n\n1. [pack_a_name]"
        "\n| DATA: Spawn:▣ | S:□/□:SA"
        "\n| M:▣ | P:▣ A:▣ | T:▣ Ts:▣"
        "\n| ----------"
        f"\n{c_text("2. BASE", bcolors.UNDERLINE)}"
        "\n| DATA: Spawn:□ | S:▣/□:SA"
        "\n| M:▣ | P:▣ A:▣ | T:▣ Ts:▣"
        "\n| ----------"
        "\n3. [pack_b_name]"
        "\n| DATA: Spawn:□ | S:▣/□:SA"
        "\n| M:▣ | P:▣ A:▣ | T:▣ Ts:▣"
        "\n| ----------"
        "\n\nYou will have to press the number of the corresponding pack "
        "you want to choose"
        f"\n\nIn {CrOpType.MERGE.name} mode some entries will also be colored"
        f"\n\n{c_text("GREEN", bcolors.OKGREEN)}: means that the "
        f"{c_text("data", bcolors.BOLD)} contained in the pack for this entry "
        "have been merged without conflicts. "
        f"{c_text("Wether you select it or not", bcolors.BOLD)} all that data will"
        "be included in the final pack."
        f"\n\n{c_text("BLUE", bcolors.OKCYAN)}: means that some data were conflicting "
        "(different packs add different things in the same value - usually "
        "graphics, hitboxes etc.). The pack you select will apply its own values "
        "and later we aldo anything else from other packs that can be added without "
        "conflicts."
        "\n\nThis aproach tries to 'include everyhting' while breaking nothing."
    )

    LOAD_ORDER = (
        "You can assign an order for the packs loaded. This will mainly affect the "
        "order in which the are shown, to help in the manual step."
        "\n\nIf AUTO_LOAD_ORDER_MODE if turned on in the settings, then this order "
        "will be applied in conflicts choosing the first pack in the order."
    )

    SETTINGS_HELP = (
        "- Op Mode:"
        f"\n     - {CrOpType.CHOOSE.name}: Files are exclusivelly chosen from one pack, "
        "including spawns, data and graphics."
        f"\n     - {CrOpType.MERGE.name}: Files are merged from all packs included. "
        "Spawns, evolutions, moves (if enabled in settings) and other data "
        "will be merged into a final output pokemon."
        "When there is a graphics conflict you must choose which version to use."
        "\n\n- Pokedex Fix: will include all pokemon added in the Pokedex (currently "
        "functional with the CobbleDex mod)."
        "\n- Exclude Pseudoforms: Some packs add multiple 'versions' of the same "
        "Pokemon. This will try to detect them and exclude them from the Dex."
        "\n\n- Advanced - Process Mods: will include files from mods (not packs "
        " and not the base cobblemon mod) in the final output pack. DO NOT use this "
        "unless you know what you're doing."
    )
