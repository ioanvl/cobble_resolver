from classes.combiner import Combiner
from constants.runtime_const import CrOpType, gcr_settings

if __name__ == "__main__":
    gcr_settings.OP_MODE = CrOpType(1)
    comb = Combiner()
    comb.run()

    _ = input("\n\nPress [Enter] to exit..")
