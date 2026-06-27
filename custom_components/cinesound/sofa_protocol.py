"""Cinesound / YKD BLE protocol: shared by scripts and HA integration.

Ported from com.ykd.zhihuijiaju (utils/CommandUtils, bean/SynData, utils/SynToByte).
Full protocol documented in notes/protocol.md.
"""
from __future__ import annotations
import itertools

SERVICE_UUID = "6e403587-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e403588-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e403589-b5a3-f393-e0a9-e50e24dcca9e"

# PID / ctrlType (packet byte 1)
PID_CTRL = 1          # left-side motor control
PID_GET_STATE = 2
PID_SET_PARA = 3
PID_CTRL_RIGHT = 9    # right-side motor control (same BLE connection)

# CCD_* command codes (ctrlValue, uint16 LE, bytes 2-3)
CMD: dict[str, int] = {
    # motors: stop / generic
    "stop": 0,
    "stop_motor": 1,
    "keep": 3,
    "m_up": 272, "m_down": 273,
    # individual motors
    "m1_stop": 256, "m1_up": 257, "m1_down": 258,
    "m2_stop": 260, "m2_up": 261, "m2_down": 262,
    "m3_stop": 264, "m3_up": 265, "m3_down": 266,
    "m4_stop": 268, "m4_up": 269, "m4_down": 270,
    # memory positions
    "set_ml1": 784, "mov_ml1": 785,
    "set_ml2": 786, "mov_ml2": 787,
    "set_ml3": 788, "mov_ml3": 789,
    # LED lighting
    "led_off": 1280, "led_rgbv": 1281, "led_white": 1282,
    "led_r": 1283, "led_g": 1284, "led_b": 1285,
    "led_rg": 1286, "led_rb": 1287, "led_gb": 1288,
    "led_m1": 1289, "led_m2": 1290, "led_m3": 1291,
    "led_m4": 1292, "led_m5": 1293, "led_m6": 1294,
    "led_save": 1295, "led_breath_off": 1297, "led_breath": 1300,
    # heat
    "heat_off": 28672,
    "heat_1": 28673, "heat_2": 28674, "heat_3": 28675,
    "heat_4": 28676, "heat_5": 28677,
    # audio / Cinesound
    "audio_off": 4096, "audio_pause": 4097, "audio_play": 4098,
    "audio_prev": 4099, "audio_next": 4100,
    "audio_vol_up": 4101, "audio_vol_down": 4102,
    "audio_mute": 4103, "audio_unmute": 4104,
    # storage compartment lid motor (momentary)
    "cup_motor_up": 24728, "cup_motor_down": 24729,
    # cup chiller (624/625 confirmed on ECBLE583)
    "cup_cool_on": 624, "cup_cool_off": 625,
    # lock
    "lock_on": 24737, "lock_off": 24738, "lock_toggle": 24739,
}

_serial_counter = itertools.count(1)


def build_packet(
    ctrl_value: int,
    parameter: int = 0,
    pid: int = PID_CTRL,
    serial: int | None = None,
) -> bytes:
    """Pack an 8-byte LE command packet.

    Byte layout: [serial, pid, ctrlValue(u16 LE), parameter(u32 LE)]
    Write with response=True; characteristic only advertises PROPERTY_WRITE.
    """
    if serial is None:
        serial = next(_serial_counter) & 0xFF
    cv = ctrl_value & 0xFFFF
    p = parameter & 0xFFFFFFFF
    return bytes((
        serial & 0xFF,
        pid & 0xFF,
        cv & 0xFF, (cv >> 8) & 0xFF,
        p & 0xFF, (p >> 8) & 0xFF, (p >> 16) & 0xFF, (p >> 24) & 0xFF,
    ))


def resolve(name_or_code: str | int) -> int:
    if isinstance(name_or_code, int):
        return name_or_code
    s = str(name_or_code).strip()
    return CMD[s] if s in CMD else int(s, 0)
