#!/usr/bin/python3
from elc_ng import ELC, ColorCommand
import time

elc = ELC(0x187c, 0x0550)
print(f"start {time.time():.6f}", flush=True)

with elc:
    for i in range(20):
        now = time.time()
        print(f"loop {i} {now:.6f}", flush=True)
        elc.execute(ColorCommand([1], 255, 0, 0))
        time.sleep(0.2)

print(f"end {time.time():.6f}", flush=True)
