#!/usr/bin/python3
from elc_ng import (
    ELC, QueryCommand, Action, AddActionsCommand,
    AnimationCommand, ZoneSelectCommand, ZONE_ALL
)
import time

elc = ELC(0x187c, 0x0550)
print("elc:", elc)

with elc:
    print("animation_count:", elc.execute(QueryCommand("animation_count")))

    anim_id = 1

    print("remove")
    print(elc.execute(AnimationCommand("remove", anim_id)))

    print("config_start")
    print(elc.execute(AnimationCommand("config_start", anim_id)))

    print("zone_select")
    print(elc.execute(ZoneSelectCommand(1, ZONE_ALL)))

    print("add green action")
    print(elc.execute(AddActionsCommand([
        Action("color", 0, 255, 0, duration=5000, tempo=60)
    ])))

    print("config_play(0)")
    print(elc.execute(AnimationCommand("config_play", 0)))

    print("config_save")
    print(elc.execute(AnimationCommand("config_save", anim_id)))

    print("set_default")
    print(elc.execute(AnimationCommand("set_default", anim_id)))

    time.sleep(2)
