from typing import Any


class PoserResolver:
    @staticmethod
    def _navigate_poser_entry(
        poser_entry: dict, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        for t in ["quirks", "animations"]:
            existing_set.update(
                PoserResolver._parse_poser_animation_entry(poser_entry.get(t, None))
            )

        return existing_set

    @staticmethod
    def _parse_poser_animation_entry(
        poser_entry: Any, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        if isinstance(poser_entry, str):
            existing_set.add(
                PoserResolver._parse_poser_animation_line(poser_line=poser_entry)
            )
        elif isinstance(poser_entry, list):
            existing_set.update(
                PoserResolver._parse_poser_animation_list(poser_entry=poser_entry)
            )
        elif isinstance(poser_entry, dict):
            existing_set.update(
                PoserResolver._parse_poser_animation_dict(poser_entry=poser_entry)
            )

        return existing_set

    @staticmethod
    def _parse_poser_animation_list(
        poser_entry: list, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        for pl in poser_entry:
            existing_set.update(PoserResolver._parse_poser_animation_entry(pl))

        return existing_set

    @staticmethod
    def _parse_poser_animation_dict(
        poser_entry: dict, existing_set: set[tuple[str, str]] | None = None
    ) -> set[tuple[str, str]]:
        if existing_set is None:
            existing_set: set[tuple[str, str]] = set()

        if "animations" in poser_entry:
            existing_set.update(
                PoserResolver._parse_poser_animation_entry(
                    poser_entry=poser_entry["animations"]
                )
            )
            del poser_entry["animations"]

        for move, pl in poser_entry.items():
            existing_set.update(PoserResolver._parse_poser_animation_entry(pl))

        return existing_set

    @staticmethod
    def _parse_poser_animation_line(poser_line: str | None) -> tuple[str, str]:
        if not poser_line:
            return ("", "")

        try:
            for stw in ["q.bedrock", "q.bedrock_quirk", "bedrock"]:
                if poser_line.startswith(stw):
                    return PoserResolver._extract_poser_animation_line(
                        poser_line=poser_line
                    )
        except:
            pass
        return ("", "")

    @staticmethod
    def _extract_poser_animation_line(poser_line: str) -> tuple[str, str]:
        poser_line = PoserResolver._extract_parentheses(poser_line=poser_line)
        parts = poser_line.split(",")
        name = parts[0].strip(" ''").strip('"')
        move = parts[1]
        if move.startswith("q."):
            move = PoserResolver._extract_parentheses(move)
        move = move.strip(" ''").strip('"')
        return (name, move)
        "" "faint" ""

    @staticmethod
    def _extract_parentheses(poser_line: str) -> str:
        parts = poser_line.split("(")
        poser_line = "(".join(parts[1:]) if len(parts) > 2 else parts[1]
        parts = poser_line.split(")")
        poser_line = ")".join(parts[:-1]) if len(parts) > 2 else parts[0]
        return poser_line
