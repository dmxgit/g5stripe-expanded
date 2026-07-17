## Dell / AlienFX controller `187c:0550`

This project built on the work done on humanfx, the C reverse engineered code to access the controller, and g5stripe that was just enough for the coder's needs. All this was made to work on my Dell G5 PC, as it was not at first, and then a small GUI was built on this. The objective attained was to not need to boot windows to adjust the DEL settings on the G5.

Denis Marcoux, June 2026

Validated facts for this controller:

- USB device: `0x187c:0x0550`
- Commands are sent as **33-byte USB control packets**
- Relevant opcodes:
  - `0x21` = animation
  - `0x23` = zone select
  - `0x24` = add action
  - `0x26` = set dim
- Zones:
  - `0x00` = left
  - `0x01` = middle-left
  - `0x02` = middle-right
  - `0x03` = right

### Animation subcommands

- `0x0001` = `config_start`
- `0x0002` = `config_save`
- `0x0003` = `config_play`
- `0x0004` = `remove`
- `0x0005` = `play`
- `0x0006` = `set_default`
- `0x0007` = `set_startup`

### Packet formats

#### Zone selection

```text
03 23 loop zone_count_hi zone_count_lo zones...
```

Example for all 4 zones:

```text
03 23 01 00 04 00 01 02 03
```

#### Add action

```text
03 24 action duration_hi duration_lo tempo_hi tempo_lo R G B
```

For a static color action:

- `action = 0x00`
- `duration = 5000` -> `0x13 0x88`
- `tempo = 60` -> `0x00 0x3c`

Example for solid green:

```text
03 24 00 13 88 00 3c 00 ff 00
```

### Important behavior

A persistent fixed color is **not** obtained by sending a simple RGB packet.

What works is:

1. Remove animation slot `1`
2. Start config on animation slot `1`
3. Select the target zones
4. Add a `color` action
5. `config_play(0)`
6. `config_save(1)`
7. `set_default(1)`

### Minimal working sequence

```text
remove(1)
config_start(1)
zone_select(1, 4, )[1][2][3]
add_action(color, 5000, 60, R, G, B)
config_play(0)
config_save(1)
set_default(1)
```

### Python example

```python
from elc_ng import (
    ELC,
    Action,
    AddActionsCommand,
    AnimationCommand,
    ZoneSelectCommand,
    ZONE_ALL,
)

def set_static_color(elc, r, g, b, animation_id=1):
    with elc:
        elc.execute(AnimationCommand("remove", animation_id))
        elc.execute(AnimationCommand("config_start", animation_id))
        elc.execute(ZoneSelectCommand(1, ZONE_ALL))
        elc.execute(AddActionsCommand([
            Action("color", r, g, b, duration=5000, tempo=60)
        ]))
        elc.execute(AnimationCommand("config_play", 0))
        elc.execute(AnimationCommand("config_save", animation_id))
        elc.execute(AnimationCommand("set_default", animation_id))

elc = ELC(0x187c, 0x0550)
set_static_color(elc, 0, 255, 0)  # solid green
```

### Implementation notes

- In this Python codebase, custom commands must override `payload()`, not `raw()`.
- Explicit zone selection is required before adding the action.
- `config_play(0)` alone is not enough for persistence.
- Persistence comes from `config_save(1)` followed by `set_default(1)`.

### Animation notes

- `pulse` works with a single action/color entry.
- `morph` works more reliably when sent as two successive single-action steps, one for each color, instead of two colors in one command.
- A brief blink may occur when the animation is rebuilt and played; this appears to come from the controller's configuration/play sequence.
