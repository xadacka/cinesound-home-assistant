"""Cinesound / YKD 'Smart furniture' BLE protocol.

Ported from decompiled com.ykd.zhihuijiaju (utils/CommandUtils.java,
bean/SynData.java, utils/SynToByte.java). See notes/protocol.md.

Shared by the test scripts and the Home Assistant integration.
"""
from __future__ import annotations
import itertools

# GATT profile -----------------------------------------------------------
SERVICE_UUID = "6e403587-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e403588-b5a3-f393-e0a9-e50e24dcca9e"   # commands -> sofa (write no response)
NOTIFY_UUID = "6e403589-b5a3-f393-e0a9-e50e24dcca9e"   # status <- sofa (notify)

# PID / ctrlType (packet byte 1) ----------------------------------------
PID_CTRL = 1          # normal control (main / left)
PID_GET_STATE = 2     # poll status
PID_SET_PARA = 3      # save parameter / memory position
PID_GET_PARA = 4
PID_GET_VER = 5
PID_CTRL_RIGHT = 9    # control right side (dual-motor)

# CCD_* control codes (ctrlValue, packet bytes 2-3, uint16 LE) -----------
# Names mirror the decompiled constants. Decimal in comments.
CMD = {
    # --- stop / generic motor ---
    "stop": 0,               # CCDstop (everything)
    "stop_motor": 1,         # all motors stop
    "stop_massage": 2,
    "keep": 3,               # keepalive ping
    "m_up": 272,
    "m_down": 273,
    # --- individual motors ---
    "m1_stop": 256, "m1_up": 257, "m1_down": 258, "m1_run": 259,
    "m2_stop": 260, "m2_up": 261, "m2_down": 262, "m2_run": 263,
    "m3_stop": 264, "m3_up": 265, "m3_down": 266, "m3_run": 267,
    "m4_stop": 268, "m4_up": 269, "m4_down": 270, "m4_run": 271,
    # --- motor combos (run / back) ---
    "m12_run": 274, "m12_back": 275, "m13_run": 276, "m13_back": 277,
    "m23_run": 278, "m23_back": 279, "m24_run": 280, "m24_back": 281,
    "m34_run": 282, "m34_back": 283, "m123_run": 284, "m123_back": 285,
    "m134_run": 286, "m134_back": 287,
    # --- save / move-to memory positions ---
    "set_ml1": 784, "mov_ml1": 785, "set_ml2": 786, "mov_ml2": 787,
    "set_ml3": 788, "mov_ml3": 789, "set_ml4": 790, "mov_ml4": 791,
    "set_ml5": 792, "mov_ml5": 793, "set_ml6": 794, "mov_ml6": 795,
    # --- preset / auto moves ---
    "auto_m1": 896, "auto_m2": 897, "auto_m3": 898, "auto_m4": 899,
    # --- LED lighting ---
    "led_off": 1280, "led_rgbv": 1281, "led_white": 1282,
    "led_r": 1283, "led_g": 1284, "led_b": 1285,
    "led_rg": 1286, "led_rb": 1287, "led_gb": 1288,
    "led_m1": 1289, "led_m2": 1290, "led_m3": 1291,
    "led_m4": 1292, "led_m5": 1293, "led_m6": 1294,
    "led_save": 1295, "led_breath_off": 1297, "led_breath": 1300,
    "led_inc1": 1305, "led_inc2": 1306, "led_inc3": 1307,
    # --- heat ---
    "heat_off": 28672, "heat_1": 28673, "heat_2": 28674,
    "heat_3": 28675, "heat_4": 28676, "heat_5": 28677, "heat_custom": 28688,
    # --- audio / Cinesound ---
    "audio_off": 4096, "audio_pause": 4097, "audio_play": 4098,
    "audio_prev": 4099, "audio_next": 4100, "audio_vol_up": 4101,
    "audio_vol_down": 4102, "audio_mute": 4103, "audio_unmute": 4104,
    "audio_reset": 4105,
    "bass_up": 4192, "bass_down": 4193, "high_up": 4194, "high_down": 4195,
    # --- fan / cooling ---
    "fan_off": 28720, "fan_1": 28721, "fan_2": 28722, "fan_3": 28723,
    # --- storage compartment / drinks-holder motor (momentary) ---
    "cup_motor_up": 24728, "cup_motor_down": 24729,
    # --- chilled cup holders ---
    # 576-578 overlap with airbag codes; may be model-dependent.
    # Try cool_* (28704-28706) which are more likely for this sofa.
    "cup_cold_on": 576, "cup_cold_off": 577, "cup_cold_toggle": 578,
    "cup_cool_on": 624, "cup_cool_off": 625,
    # Alternative cool commands (separate subsystem):
    "cool_off": 28704, "cool_start": 28705, "cool_custom": 28706,
    # --- music-synced vibration / audio-reactive massage ---
    "audio_massage_all_stop": 4112, "audio_massage_all_start": 4113,
    "audio_massage1_stop": 4114, "audio_massage1_start": 4115,
    "audio_massage1_1": 4116, "audio_massage1_2": 4117, "audio_massage1_3": 4118,
    "audio_massage2_stop": 4119, "audio_massage2_start": 4120,
    "audio_massage2_1": 4121, "audio_massage2_2": 4122, "audio_massage2_3": 4123,
    # audio-reactive LED
    "audio_led_stop": 4128, "audio_led_start": 4129,
    "audio_led_1": 4130, "audio_led_2": 4131, "audio_led_3": 4132, "audio_led_4": 4133,
    # --- lock ---
    "lock_on": 24737, "lock_off": 24738, "lock_toggle": 24739,
}

_serial_counter = itertools.count(1)


def build_packet(ctrl_value: int, parameter: int = 0,
                 pid: int = PID_CTRL, serial: int | None = None) -> bytes:
    """Build the 8-byte little-endian command packet."""
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


def resolve(name_or_code) -> int:
    """Accept a command name ('m1_up'), decimal ('257') or hex ('0x101')."""
    if isinstance(name_or_code, int):
        return name_or_code
    s = str(name_or_code).strip()
    if s in CMD:
        return CMD[s]
    return int(s, 0)
