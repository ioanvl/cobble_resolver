from typing import Literal

from classes.pokemon_form import PokemonForm


class DualChoise_Simple:
    @staticmethod
    def _dual_choice_mod_and_remodel(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G"]] | tuple[None, None]:
        if (pok_mod.has_spawn() and pok_mod.has_species_data()) and (
            (not pok_other.has_spawn())
            and (not pok_other.has_species_data())
            and pok_other.is_graphically_complete()
        ):
            return (pok_other.parent_pack.name, "G")
        return (None, None)

    @staticmethod
    def _dual_choice_mod_and_pack_addition(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G2"]] | tuple[None, None]:
        if (not pok_mod.has_graphics()) and pok_other.is_graphically_complete():
            return (pok_other.parent_pack.name, "G2")
        return (None, None)

    @staticmethod
    def _dual_choice_mod_remodel(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5c-R"]] | tuple[None, None]:
        if pok_mod.is_complete() and (
            (not pok_other.has_spawn())
            and (not pok_other.has_sp_data() and pok_other.is_graphically_complete())
        ):
            return (pok_other.parent_pack.name, "G5c-R")
        return (None, None)

    @staticmethod
    def _dual_choice_card(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD"]] | tuple[None, None]:
        if (
            pok_mod.is_complete()
            and pok_mod.parent_pack.is_base
            and (not pok_other.has_spawn())
            and (not pok_other.has_sp_data())
            and (not pok_other.is_graphically_complete())
        ):
            return (pok_mod.parent_pack.name, "CARD")
        return (None, None)

    @staticmethod
    def _dual_choice_card_2(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD2"]] | tuple[None, None]:
        if (
            pok_mod.parent_pack.is_base
            and (not pok_mod.has_spawn())
            and (not pok_mod.has_graphics())
            and (pok_other.comp_stamp[4:] == [True, False, False, True, True])
        ):
            return (pok_other.parent_pack.name, "CARD2")
        return (None, None)

    @staticmethod
    def _dual_choice_card_3(
        self, pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["CARD3"]] | tuple[None, None]:
        if (
            pok_mod.parent_pack.is_base
            and (pok_mod.is_graphically_complete())
            and (not pok_other.has_spawn())
            and (not pok_other.has_sp_data())
            and (pok_other.comp_stamp[4:] == [True, False, False, True, True])
        ):
            return (pok_mod.parent_pack.name, "CARD3")
        return (None, None)


class DualChoise_Risky:
    @staticmethod
    def _dual_choice_mod_and_species(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G3-R"]] | tuple[None, None]:
        if pok_other.is_species():
            return (pok_other.parent_pack.name, "G3-R")

        return (None, None)

    @staticmethod
    def _dual_choice_mod_w_g_and_spawn(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G4-R"]] | tuple[None, None]:
        if (
            (pok_mod.is_graphically_complete() and pok_other.is_graphically_complete())
            and (pok_mod.has_sp_data() and (not pok_other.has_sp_data()))
            and ((not pok_mod.has_spawn()) and pok_other.has_spawn())
        ):
            return (pok_other.parent_pack.name, "G4-R")

        return (None, None)

    @staticmethod
    def _dual_choice_mod_and_req_pack(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5-R"]] | tuple[None, None]:
        if pok_mod.is_complete() and (
            (not pok_other.has_graphics()) and (pok_other.is_requested())
        ):
            return (pok_other.parent_pack.name, "G5-R")
        return (None, None)

    @staticmethod
    def _dual_choice_mod_and_req_pack_2(
        pok_mod: PokemonForm, pok_other: PokemonForm
    ) -> tuple[str, Literal["G5b-R"]] | tuple[None, None]:
        if pok_mod.is_complete() and (
            (pok_other.has_graphics())
            and (pok_other.is_requested())
            and pok_other.has_spawn()
            and (not pok_other.has_sp_data())
        ):
            return (pok_other.parent_pack.name, "G5b-R")
        return (None, None)
