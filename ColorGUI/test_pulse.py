#!/usr/bin/python3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from elc_ng import ELC, AnimationCommand, ZoneSelectCommand, AddActionsCommand, Action, ZONE_ALL

elc = ELC(0x187c, 0x0550)
print("Starting pulse animation on all zones...")

with elc:
    elc.execute(AnimationCommand("config_start", 0))
    elc.execute(ZoneSelectCommand(1, ZONE_ALL))
    elc.execute(AddActionsCommand([
        Action("pulse", 0, 255, 0, duration=3000, tempo=80)
    ]))
    elc.execute(AnimationCommand("config_play", 0))

print("Done.")
