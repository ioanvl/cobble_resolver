import os
import sys

special_keys = {
    "\r": "enter",
    "\t": "tab",
}

win_extras = {"H": "up", "P": "down", "M": "right", "K": "left"}

nix_extras = {
    "[A": "up",
    "[B": "down",
    "[C": "right",
    "[D": "left",
    "[H": "start",
    "[F": "end",
}
nix_extras_2 = {"[2": "ins", "[3": "del", "[5": "pg_up", "[6": "pd_down"}


def keypress():
    try:
        from msvcrt import getch  # try to import Windows version
    except ImportError:
        try:
            import termios
            import tty  # noqa
        except ImportError:
            return ""

        def getch():  # define non-Windows version
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

    x = getch()
    # print(f'debug - {repr(x)}')
    if x in special_keys:
        return special_keys[x]
    try:
        y = x.decode("utf-8")
        if y in special_keys:
            return special_keys[y]
    except:  # noqa
        pass
    if os.name == "nt":
        if x == b"\xe0":
            extra_key = getch()
            try:
                extra_key = extra_key.decode("utf-8")
            except UnicodeDecodeError:
                pass
            if extra_key in win_extras:
                return win_extras[extra_key]
            else:
                return "extra_" + extra_key
        else:
            try:
                return x.decode("utf-8")
            except UnicodeDecodeError:
                return "er"
    else:
        if x in ("\x1b", "\x00"):
            extra_key = getch() + getch()
            if extra_key in nix_extras:
                return nix_extras[extra_key]
            elif extra_key in nix_extras_2:
                _ = getch()
                return nix_extras_2[extra_key]
            else:
                return "extra_" + extra_key
        else:
            return x


def clear():
    if os.name == "nt":
        os.system("cls")
    elif os.name == "posix":
        os.system("clear")


def yn_q(default=None):
    if default is not None:
        try:
            default = str(default)
        except ValueError:
            default = "n"
    if default == "y" or default == "yes":
        default = "y"
        msg = "[y]/n"
    else:
        default = "n"
        msg = "y/[n]"

    while True:
        try:
            x = input(f"{msg}\n")
        except EOFError:
            x = ""
        if x == "y" or x == "Y":
            return True
        elif x == "n" or x == "N":
            return False
        elif x == "":
            if default == "y":
                return True
            elif default == "n":
                return False
