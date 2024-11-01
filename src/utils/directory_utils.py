from pathlib import Path
import shutil


def clear_empty_dir(
    s_path: Path, verbose: bool = False, items_to_delete: list[str] = list()
):
    temp = [x for x in s_path.iterdir()]
    for item in temp:
        if item.name in items_to_delete:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        if item.is_dir():
            clear_empty_dir(
                s_path=item, verbose=verbose, items_to_delete=items_to_delete
            )
            if not len([x for x in item.rglob("*")]):
                item.rmdir()
