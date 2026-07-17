from dataclasses import dataclass, field
import struct
import typing

import usb
import usb.util


@dataclass
class Response:
    @classmethod
    def from_bytes(cls, data):
        return cls(data)


@dataclass
class RawResponse(Response):
    raw: bytes


@dataclass
class Command:
    opcode: typing.ClassVar[int] = None
    response_class: typing.ClassVar[Response] = RawResponse

    def header(self):
        return bytes((0x03, self.opcode))

    def payload(self):
        return self.header()

    def as_bytes(self):
        return self.payload().ljust(33, b'\x00')


@dataclass
class CommandWithSubcommand(Command):
    subcommands: typing.ClassVar[dict] = None

    subcommand: str

    def __post_init__(self):
        if self.subcommand and self.subcommand not in self.subcommands:
            raise AttributeError(
                f'Invalid subcommand for {type(self).__name__}. '
                f'Valid choices are: {", ".join(self.subcommands)}.'
            )

    def payload(self):
        return super().payload() + bytes([self.subcommands[self.subcommand]])


@dataclass
class VersionResponse(Response):
    version_info: tuple

    args_struct = struct.Struct('>BBB')

    @classmethod
    def from_bytes(cls, data):
        return cls(cls.args_struct.unpack(data[3:6]))


@dataclass
class PlatformResponse(Response):
    platform_id: int
    zone_count: int

    args_struct = struct.Struct('>HB')

    @classmethod
    def from_bytes(cls, data):
        return cls(*cls.args_struct.unpack(data[3:6]))


@dataclass
class AnimationCountResponse(Response):
    animation_count: int
    last_animation_id: int

    args_struct = struct.Struct('>HH')

    @classmethod
    def from_bytes(cls, data):
        return cls(*cls.args_struct.unpack(data[3:7]))


@dataclass
class QueryCommand(CommandWithSubcommand):
    opcode = 0x20
    subcommands = {
        'version': 0x00,
        'platform': 0x02,
        'animation_count': 0x03,
    }
    response_classes = {
        'version': VersionResponse,
        'platform': PlatformResponse,
        'animation_count': AnimationCountResponse,
    }

    def __post_init__(self):
        super().__post_init__()
        self.response_class = self.response_classes.get(
            self.subcommand,
            Response
        )


@dataclass
class AnimationCommand(CommandWithSubcommand):
    subcommands = {
        'start_new': 0x01,
        'finish_save': 0x02,
        'finish_play': 0x03,
        'remove': 0x04,
        'play': 0x05,
        'set_default': 0x06,
        'set_startup': 0x07,
    }

    animation_id: int

    args_struct = struct.Struct('>HH')

    def __post_init__(self):
        super().__post_init__()
        self.opcode = 0x21 if self.is_power_animation else 0x22

    @property
    def is_power_animation(self):
        return 0x5b <= self.animation_id <= 0x60

    def payload(self):
        return self.header() + self.args_struct.pack(
            self.subcommands[self.subcommand],
            self.animation_id
        )


@dataclass
class StartSeriesCommand(Command):
    opcode = 0x23

    zones: typing.Collection[int]
    loop: bool = 1

    args_struct = struct.Struct('>BH')

    def payload(self):
        zones = self.zones
        return (
            super().payload()
            + self.args_struct.pack(self.loop, len(zones))
            + bytes(zones)
        )


@dataclass
class Action:
    effect: str
    red: int
    green: int
    blue: int
    duration: int = 1000
    tempo: int = 60

    effects: typing.ClassVar[dict] = {
        'color': 0x00,
        'pulse': 0x01,
        'morph': 0x02,
    }

    args_struct = struct.Struct('>BHHBBB')

    def __post_init__(self):
        if self.effect not in self.effects:
            raise AttributeError(
                'Invalid effect. '
                f'Possible choices are: {", ".join(self.effects)}'
            )

    def as_bytes(self):
        return self.args_struct.pack(
            self.effects[self.effect],
            self.duration,
            self.tempo,
            self.red,
            self.green,
            self.blue,
        )


@dataclass
class AddActionsCommand(Command):
    opcode = 0x24

    actions: typing.Collection[Action]

    def __post_init__(self):
        if len(self.actions) > 3:
            raise AttributeError("Can't add more than 3 actions at a time.")

    def payload(self):
        return super().payload() + b''.join(
            action.as_bytes() for action in self.actions
        )


@dataclass
class DimCommand(Command):
    opcode = 0x26

    zones: typing.Collection[int]
    level: int

    args_struct = struct.Struct('>BH')

    def payload(self):
        zones = self.zones
        return (
            super().payload()
            + self.args_struct.pack(self.level, len(zones))
            + bytes(zones)
        )


@dataclass
class ColorCommand(Command):
    opcode = 0x27

    zones: typing.Collection[int]
    red: int
    green: int
    blue: int

    args_struct = struct.Struct('>BBBH')

    def payload(self):
        zones = self.zones
        return (
            super().payload()
            + self.args_struct.pack(
                self.red,
                self.green,
                self.blue,
                len(zones),
            ) + bytes(zones)
        )


@dataclass
class ELC:
    vid: int
    pid: int

    usb_device: usb.core.Device = field(init=False, compare=False)
    attached: bool = field(default=False, init=False, compare=False)
    reattach_kernel: bool = field(default=False, init=False, compare=False)
    interface_number: int = field(default=0, init=False, compare=False)

    def __post_init__(self):
        vid, pid = self.vid, self.pid

        results = list(usb.core.find(
            idVendor=vid,
            idProduct=pid,
            find_all=True,
        ))

        if not results:
            raise AttributeError(
                f'USB device with VID:PID {vid}:{pid} not found.'
            )

        if len(results) > 1:
            raise AttributeError(
                f'More than one USB device with VID:PID {vid}:{pid} was found.'
            )

        self.usb_device = results[0]

    def __enter__(self):
        self._attach()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._detach()
        return False

    def _attach(self):
        device = self.usb_device
        intf = self.interface_number
        self.reattach_kernel = False

        try:
            if device.is_kernel_driver_active(intf):
                device.detach_kernel_driver(intf)
                self.reattach_kernel = True
        except (NotImplementedError, usb.core.USBError):
            self.reattach_kernel = False

        default_configuration = device.configurations()[0]
        current_configuration = None

        try:
            current_configuration = device.get_active_configuration()
        except usb.core.USBError:
            pass

        if (
            not current_configuration
            or current_configuration.bConfigurationValue
            != default_configuration.bConfigurationValue
        ):
            device.set_configuration()

        try:
            usb.util.claim_interface(device, intf)
        except usb.core.USBError:
            pass

        self.attached = True

    def _detach(self):
        device = self.usb_device
        intf = self.interface_number

        try:
            usb.util.release_interface(device, intf)
        except usb.core.USBError:
            pass

        usb.util.dispose_resources(device)

        if self.reattach_kernel:
            try:
                device.attach_kernel_driver(intf)
            except usb.core.USBError as e:
                if getattr(e, "errno", None) != 2:
                    raise

        self.attached = False
        self.reattach_kernel = False

    def execute(self, command: Command) -> Response:
        if not self.attached:
            raise ValueError(
                "ELC isn't currently attached to any USB device. "
                'Please use execute() inside a "with your_elc:" block.'
            )

        self.usb_send(command.as_bytes())
        return command.response_class.from_bytes(self.usb_recv())

    def usb_send(self, data):
        self.usb_device.ctrl_transfer(
            usb.TYPE_CLASS | usb.RECIP_INTERFACE | usb.ENDPOINT_OUT,
            usb.REQ_SET_CONFIGURATION,
            0x202,
            0,
            data
        )

    def usb_recv(self):
        return self.usb_device.ctrl_transfer(
            usb.TYPE_CLASS | usb.RECIP_INTERFACE | usb.ENDPOINT_IN,
            usb.REQ_CLEAR_FEATURE,
            0x101,
            0,
            33
        )


# ---- Dell / AlienFX helpers aligned with humanfx (USB 187c:0550) ----

ZONE_LEFT = 0x00
ZONE_MIDDLE_LEFT = 0x01
ZONE_MIDDLE_RIGHT = 0x02
ZONE_RIGHT = 0x03
ZONE_ALL = [ZONE_LEFT, ZONE_MIDDLE_LEFT, ZONE_MIDDLE_RIGHT, ZONE_RIGHT]


class ZoneSelectCommand(Command):
    command = 0x23

    def __init__(self, loop, zones):
        self.loop = int(loop) & 0xFF
        self.zones = [int(z) & 0xFF for z in zones]

    def raw(self):
        count = len(self.zones)
        return bytes([
            0x03,
            self.command,
            self.loop,
            (count >> 8) & 0xFF,
            count & 0xFF,
            *self.zones,
        ])


class SetDimCommand(Command):
    command = 0x26

    def __init__(self, dim, zones):
        self.dim = int(dim) & 0xFF
        self.zones = [int(z) & 0xFF for z in zones]

    def raw(self):
        count = len(self.zones)
        return bytes([
            0x03,
            self.command,
            self.dim,
            (count >> 8) & 0xFF,
            count & 0xFF,
            *self.zones,
        ])


class Action:
    TYPES = {
        "color": 0x00,
        "pulse": 0x01,
        "morph": 0x02,
    }

    def __init__(self, kind, r, g, b, duration=5000, tempo=60):
        if kind not in self.TYPES:
            raise ValueError(f"Unknown action kind: {kind}")
        self.kind = kind
        self.action = self.TYPES[kind]
        self.r = int(r) & 0xFF
        self.g = int(g) & 0xFF
        self.b = int(b) & 0xFF
        self.duration = int(duration) & 0xFFFF
        self.tempo = int(tempo) & 0xFFFF

    def raw(self):
        return bytes([
            0x03,
            0x24,
            self.action & 0xFF,
            (self.duration >> 8) & 0xFF,
            self.duration & 0xFF,
            (self.tempo >> 8) & 0xFF,
            self.tempo & 0xFF,
            self.r,
            self.g,
            self.b,
        ])


class AddActionsCommand(Command):
    def __init__(self, actions):
        self.actions = list(actions)
        if len(self.actions) != 1:
            raise ValueError("This implementation currently sends exactly one action per command")

    def raw(self):
        return self.actions[0].raw()


class AnimationCommand(Command):
    command = 0x21

    SUBCOMMANDS = {
        "start_new": 0x0001,
        "config_start": 0x0001,

        "finish_save": 0x0002,
        "config_save": 0x0002,
        "save": 0x0002,

        "config_play": 0x0003,

        "remove": 0x0004,

        "play": 0x0005,
        "animation_play": 0x0005,

        "set_default": 0x0006,
        "set_startup": 0x0007,
    }

    def __init__(self, op, animation_id):
        if op not in self.SUBCOMMANDS:
            raise ValueError(f"Unknown animation op: {op}")
        self.op = op
        self.subcommand = self.SUBCOMMANDS[op]
        self.animation_id = int(animation_id) & 0xFFFF

    def raw(self):
        return bytes([
            0x03,
            self.command,
            (self.subcommand >> 8) & 0xFF,
            self.subcommand & 0xFF,
            (self.animation_id >> 8) & 0xFF,
            self.animation_id & 0xFF,
        ])

# ---- FIX v2: classes compatibles avec la base Command existante ----

ZONE_LEFT = 0x00
ZONE_MIDDLE_LEFT = 0x01
ZONE_MIDDLE_RIGHT = 0x02
ZONE_RIGHT = 0x03
ZONE_ALL = [ZONE_LEFT, ZONE_MIDDLE_LEFT, ZONE_MIDDLE_RIGHT, ZONE_RIGHT]


class ZoneSelectCommand(Command):
    opcode = 0x23

    def __init__(self, loop, zones):
        self.loop = int(loop) & 0xFF
        self.zones = [int(z) & 0xFF for z in zones]

    def payload(self):
        count = len(self.zones)
        return bytes([
            0x03,
            self.opcode,
            self.loop,
            (count >> 8) & 0xFF,
            count & 0xFF,
            *self.zones,
        ])


class SetDimCommand(Command):
    opcode = 0x26

    def __init__(self, dim, zones):
        self.dim = int(dim) & 0xFF
        self.zones = [int(z) & 0xFF for z in zones]

    def payload(self):
        count = len(self.zones)
        return bytes([
            0x03,
            self.opcode,
            self.dim,
            (count >> 8) & 0xFF,
            count & 0xFF,
            *self.zones,
        ])


class Action:
    TYPES = {
        "color": 0x00,
        "pulse": 0x01,
        "morph": 0x02,
    }

    def __init__(self, kind, r, g, b, duration=5000, tempo=60):
        if kind not in self.TYPES:
            raise ValueError(f"Unknown action kind: {kind}")
        self.kind = kind
        self.action = self.TYPES[kind]
        self.r = int(r) & 0xFF
        self.g = int(g) & 0xFF
        self.b = int(b) & 0xFF
        self.duration = int(duration) & 0xFFFF
        self.tempo = int(tempo) & 0xFFFF

    def as_payload(self):
        return bytes([
            0x03,
            0x24,
            self.action & 0xFF,
            (self.duration >> 8) & 0xFF,
            self.duration & 0xFF,
            (self.tempo >> 8) & 0xFF,
            self.tempo & 0xFF,
            self.r,
            self.g,
            self.b,
        ])


class AddActionsCommand(Command):
    opcode = 0x24

    def __init__(self, actions):
        self.actions = list(actions)
        if len(self.actions) != 1:
            raise ValueError("This implementation currently sends exactly one action per command")

    def payload(self):
        return self.actions[0].as_payload()


class AnimationCommand(Command):
    opcode = 0x21

    SUBCOMMANDS = {
        "start_new": 0x0001,
        "config_start": 0x0001,

        "finish_save": 0x0002,
        "config_save": 0x0002,
        "save": 0x0002,

        "config_play": 0x0003,

        "remove": 0x0004,

        "play": 0x0005,
        "animation_play": 0x0005,

        "set_default": 0x0006,
        "set_startup": 0x0007,
    }

    def __init__(self, op, animation_id):
        if op not in self.SUBCOMMANDS:
            raise ValueError(f"Unknown animation op: {op}")
        self.op = op
        self.subcommand = self.SUBCOMMANDS[op]
        self.animation_id = int(animation_id) & 0xFFFF

    def payload(self):
        return bytes([
            0x03,
            self.opcode,
            (self.subcommand >> 8) & 0xFF,
            self.subcommand & 0xFF,
            (self.animation_id >> 8) & 0xFF,
            self.animation_id & 0xFF,
        ])

def _clamp_u8(v):
    v = int(v)
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v


def set_brightness(elc, brightness, zones=None):
    if zones is None:
        zones = ZONE_ALL

    brightness = max(0, min(100, int(brightness)))
    dim = 100 - brightness

    with elc:
        elc.execute(SetDimCommand(dim, zones))

    return brightness

def set_static_color(elc, r, g, b, animation_id=1, zones=None, duration=5000, tempo=60):
    if zones is None:
        zones = ZONE_ALL

    r = _clamp_u8(r)
    g = _clamp_u8(g)
    b = _clamp_u8(b)

    with elc:
        elc.execute(AnimationCommand("remove", animation_id))
        elc.execute(AnimationCommand("config_start", animation_id))
        elc.execute(ZoneSelectCommand(1, zones))
        elc.execute(AddActionsCommand([
            Action("color", r, g, b, duration=duration, tempo=tempo)
        ]))
        elc.execute(AnimationCommand("config_play", 0))
        elc.execute(AnimationCommand("config_save", animation_id))
        elc.execute(AnimationCommand("set_default", animation_id))

    return (r, g, b)
