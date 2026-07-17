#!/usr/bin/python3
from elc_ng import (
    ELC, QueryCommand, Action, AddActionsCommand,
    AnimationCommand, StartSeriesCommand
)
import time

elc = ELC(0x187c, 0x0550)
print("elc:", elc)

with elc:
    print("version:", elc.execute(QueryCommand("version")))
    print("platform:", elc.execute(QueryCommand("platform")))
    print("animation_count:", elc.execute(QueryCommand("animation_count")))

    anim_id = 0x0001

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
    print(elc.execute(StartSeriesCommand([1], loop=1)))

    time.sleep(5)
