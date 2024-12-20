from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvolutionEntry:
    from_pokemon: str
    to_pokemon: str
    file_path: Path
    is_addition: bool = False

    def __eq__(self, value: "EvolutionEntry") -> bool:
        return (
            (self.from_pokemon == value.from_pokemon)
            and (self.to_pokemon == value.to_pokemon)
            and (self.file_path == value.file_path)
            and (self.is_addition == value.is_addition)
        )

    def __hash__(self) -> int:
        return hash(
            (self.from_pokemon, self.to_pokemon, self.file_path, self.is_addition)
        )


@dataclass
class EvolutionCollection:
    evolutions: set[EvolutionEntry] = field(default_factory=set)

    def get_evolutions(
        self, source: str | None = None, result: str | None = None
    ) -> list[EvolutionEntry]:
        res: list[EvolutionEntry] = (
            list()
        )  # TODO make it a set and add hashes to the entries
        if source:
            res.extend(
                [
                    ev
                    for ev in self.evolutions
                    if (
                        (ev.from_pokemon == source)
                        or (ev.from_pokemon.startswith(f"{source}_"))
                    )
                ]
            )
        if result:
            res.extend(
                [
                    ev
                    for ev in self.evolutions
                    if (
                        (ev.to_pokemon == result)
                        or (ev.to_pokemon.startswith(f"{result}_"))
                    )
                ]
            )
        return res

    def get_evolution_names(
        self, source: str | None = None, result: str | None = None
    ) -> set[str]:
        res: set[str] = set()
        if source:
            res.update(
                [
                    ev.to_pokemon
                    for ev in self.evolutions
                    if (
                        (ev.from_pokemon == source)
                        or (ev.from_pokemon.startswith(f"{source}_"))
                    )
                ]
            )
        if result:
            res.update(
                [
                    ev.from_pokemon
                    for ev in self.evolutions
                    if (
                        (ev.to_pokemon == result)
                        or (ev.to_pokemon.startswith(f"{result}_"))
                    )
                ]
            )
        return res

    def add(self, ev: EvolutionEntry) -> None:
        self.evolutions.add(ev)
        if (ev.from_pokemon is None) or (ev.to_pokemon is None):
            pass

    def remove(self, ev: EvolutionEntry) -> None:
        self.evolutions.remove(ev)
