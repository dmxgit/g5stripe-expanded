#!/usr/bin/python3
from elc_ng import (
    ELC, QueryCommand, Action, AddActionsCommand,
    AnimationCommand, StartSeriesCommand
)
import time

elc = ELC(0x187c, 0x0550)
print("elc:", elc)

with elc:
    ver = elc.execute(QueryCommand("version"))
    plat = elc.execute(QueryCommand("platform"))
    info = elc.execute(QueryCommand("animation_count"))

    print("version:", ver)
    print("platform:", plat)
    print("animation_count:", info)

    anim_id = info.last_animation_id + 1
    zones = [1, 2]

    print("anim_id choisi:", anim_id)
    print("zones:", zones)

    print("start_new")
    print(elc.execute(AnimationCommand("start_new", anim_id)))

    print("add red action")
    action = Action("color", 255, 0, 0, duration=5000, tempo=60)
    print(elc.execute(AddActionsCommand([action])))

    print("finish_save")
    print(elc.execute(AnimationCommand("finish_save", anim_id)))

    print("play")
    print(elc.execute(AnimationCommand("play", anim_id)))

    print("start series")
    print(elc.execute(StartSeriesCommand(zones, loop=1)))

    time.sleep(5)
