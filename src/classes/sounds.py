from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional

from classes.base_classes import bcfo

if TYPE_CHECKING:
    from classes.pack import Pack


@dataclass
class SoundEntry:
    internal_name: str
    moves: dict[str, set[Path]] = field(default_factory=dict)
    _unassigned_files: set[Path] = field(default_factory=set)
    data: dict[str, dict] = field(default_factory=dict)

    def get_all_files(self) -> set[Path]:
        res: set[Path] = set()
        res.update(self._unassigned_files)
        for m in self.moves.values():
            res.update(m)
        return res

    def has_files(self) -> bool:
        return bool(self._unassigned_files) or bool(self.moves)

    def __contains__(self, item) -> bool:
        return (item in self.get_all_files()) or (item in self.moves.keys())


@dataclass
class SoundPack:
    assignment: bcfo | None = None
    entries: dict[str, SoundEntry] = field(default_factory=dict)

    _loose_files: set[Path] = field(default_factory=set)

    _base_folder: Path | None = None
    _parent_pack: Optional["Pack"] = None

    def process(self) -> None:
        self._process_assignment()
        self._process_remaining_loose_files()

    def _process_assignment(self) -> None:
        if not self.assignment:
            return
        try:
            with self.assignment.file_path.open() as f:
                data: dict[str, dict] = json.load(f)
        except Exception:
            return

        for key in data.keys():
            key_parts = key.split(".")

            move_name = None
            if len(key_parts) == 1:
                pok_name = key_parts[0]
            else:
                if key_parts[0] != "pokemon":
                    continue
                try:
                    pok_name = key_parts[1]
                    move_name = key_parts[2]
                except Exception:
                    continue

            if pok_name not in self:
                self.entries[pok_name] = SoundEntry(internal_name=pok_name)

            se: SoundEntry = self.entries[pok_name]
            if move_name:
                if move_name not in se:
                    se.moves[move_name] = set()

            sounds_data_entry = data[key]
            se.data[key] = sounds_data_entry

            for s_file_e in sounds_data_entry.get("sounds", list()):
                if isinstance(s_file_e, dict):
                    s_file_e = s_file_e["name"]
                parts: list[str] = s_file_e.split("/")
                if not parts[-1].endswith(".ogg"):
                    parts[-1] = f"{parts[-1]}.ogg"

                if (x := (self._base_folder / ("/".join(parts[1:])))).exists():
                    if move_name:
                        se.moves[move_name].add(x)
                    else:
                        se._unassigned_files.add(x)
                    if x in self._loose_files:
                        self._loose_files.remove(x)

    def _process_remaining_loose_files(self) -> None:
        lpcp = self._loose_files.copy()
        for item in lpcp:
            pok_name = (item.parent).name

            parts = (item.stem).split("_")
            if pok_name == "pokemon":
                pok_name = parts[0]

            move_name = ""
            if len(parts) > 1:
                move_name = parts[1]

            if pok_name not in self:
                self.entries[pok_name] = SoundEntry(internal_name=pok_name)

            se: SoundEntry = self.entries[pok_name]
            if move_name:
                if move_name not in se:
                    se.moves[move_name] = set()

            if move_name:
                se.moves[move_name].add(item)
            else:
                se._unassigned_files.add(item)
            self._loose_files.remove(item)

    def __contains__(self, pokemon: str) -> bool:
        return pokemon in self.entries.keys()

    def __iter__(self) -> Generator[SoundEntry, Any, None]:
        for mon in self.entries.values():
            yield mon

    def get_all_files(self) -> set[Path]:
        res: set[Path] = set()
        if self.assignment:
            res.add(self.assignment.file_path)
        res.update(self._loose_files)
        for en in self.entries.values():
            res.update(en.get_all_files())
        return res
