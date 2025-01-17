import sys

from classes.combiner import Combiner
from constants.runtime_const import CrOpType, gcr_settings

# Check if the major version is 3 and minor version is at least 12
if __name__ == "__main__":
    if sys.version_info < (3, 12):
        _tex = (
            f"System Python version is {sys.version_info.major}."
            f"{sys.version_info.minor}. "
            "\nThis utility was written in Python 3.12, and it is reccomended "
            " you update to that version at minimum."
            "\n\nPress [Enter] to continue.."
        )
        _ = input(_tex)
    gcr_settings.OP_MODE = CrOpType(1)
    try:
        comb = Combiner()
        comb.run()
        _ = input("\n\nPress [Enter] to exit..")
    except Exception as e:
        print("An ERROR occured:")
        print(e)

        _ = input("\n\nPress [Enter] to exit..")
