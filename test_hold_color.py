#!/usr/bin/python3
from elc_ng import ELC, ColorCommand
import time

elc = ELC(0x187c, 0x0550)
print("elc:", elc)

with elc:
    for i in range(50):
        print("tick", i)
        elc.execute(ColorCommand([1], 255, 0, 0))
        time.sleep(0.1)

print("fin")
