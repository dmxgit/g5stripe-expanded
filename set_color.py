#!/usr/bin/python3
import sys
from elc_ng import ELC, set_static_color

VID = 0x187c
PID = 0x0550

NAMED = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "off": (0, 0, 0),
    "black": (0, 0, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 128, 0),
    "purple": (128, 0, 255),
}

def usage():
    print("Usage:")
    print("  set_color.py red")
    print("  set_color.py '#00ff00'")
    print("  set_color.py 0 255 0")
    sys.exit(1)

def parse_color(argv):
    if len(argv) == 1:
        s = argv[0].strip().lower()
        if s in NAMED:
            return NAMED[s]
        if s.startswith("#") and len(s) == 7:
            return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
        if s.startswith("0x") and len(s) == 8:
            return (int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
        usage()

    if len(argv) == 3:
        try:
            return tuple(max(0, min(255, int(x))) for x in argv)
        except ValueError:
            usage()

    usage()

def main():
    r, g, b = parse_color(sys.argv[1:])
    elc = ELC(VID, PID)
    set_static_color(elc, r, g, b)
    print(f"Couleur appliquée: rgb({r}, {g}, {b})")

if __name__ == "__main__":
    main()
