from classes.combiner import Combiner
from constants.runtime_const import CrOpType, gcr_settings

if __name__ == "__main__":
    gcr_settings.OP_MODE = CrOpType(1)
    try:
        comb = Combiner()
        comb.run()
    except Exception as e:
        print("An ERROR occured:")
        print(e)

    _ = input("\n\nPress [Enter] to exit..")
