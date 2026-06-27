# DFS Aventra Cinesound: BLE protocol (reverse-engineered)

App: `com.ykd.zhihuijiaju` ("Smart furniture", YKD), v1.1 (versionCode 23).
Transport: **Bluetooth LE GATT**. No cloud dependency for control. White-label app
covering dozens of furniture models; all share one BLE command protocol.

## GATT profile

Nordic-UART-style custom service (chip is almost certainly an nRF5x).

| Role | UUID |
|------|------|
| Service | `6e403587-b5a3-f393-e0a9-e50e24dcca9e` |
| Write (commands → sofa) | `6e403588-b5a3-f393-e0a9-e50e24dcca9e` |
| Read/Notify (status ← sofa) | `6e403589-b5a3-f393-e0a9-e50e24dcca9e` |

- The sofa **advertises the service UUID**; scan-filter on it to find the device.
- Some units have a BLE name starting with `EC` (model/serial prefix); not required.

## Connection flow (from ListActivity.mGattCallback)

1. Scan for advertised service `6e403587-…`.
2. `connectGatt`.
3. `discoverServices`.
4. Enable notifications on read char `6e403589-…` (write CCCD `00002902-…` = `0x0100`).
5. Write commands to write char `6e403588-…`.

No password / pairing required for basic control. (There is an optional LOCK / password
feature (`CCD_LOCK_*`, `CCD_pwd_*`), but it is not needed to drive motors/lights/heat.)
`gatt error 133` → just retry connect (app does the same).

## Command packet: 8 bytes, little-endian (bean/SynData + utils/SynToByte)

```
byte 0 : serial     (rolling counter; incremented per distinct command. Value not validated by sofa; any byte works.)
byte 1 : PID/ctrlType
byte 2 : ctrlValue low   (CCD_* code, uint16 LE)
byte 3 : ctrlValue high
byte 4 : parameter b0    (uint32 LE; usually 0)
byte 5 : parameter b1
byte 6 : parameter b2
byte 7 : parameter b3
```

Write with **WRITE_WITH_RESPONSE** (`response=True` in bleak). The Android app sets
`WRITE_TYPE_NO_RESPONSE` but the characteristic only advertises `PROPERTY_WRITE`
(not `PROPERTY_WRITE_NO_RESPONSE`). macOS CoreBluetooth silently drops write-no-response
on such characteristics; Android's BLE stack is lenient. No checksum, no framing.

### PID (byte 1) values
| Name | Value | Use |
|------|-------|-----|
| CPID_ctrl | 1 | normal control (main/left side) |
| CPID_get_state | 2 | request status (param sweep) |
| CPID_set_para | 3 | set parameter / save memory position |
| CPID_get_para | 4 | get parameter |
| CPID_get_ver | 5 | firmware version |
| CPID_ctrl_right | 9 | control RIGHT side (dual-motor sofas) |
| CPID_*2 (113-117) | 0x71+ | secondary controller variants |

`sendCode(code,param)`   → PID=1
`sendCodeRight(code,p)`  → PID=9
`sendCodeset(code,p)`    → PID=3 (save position)
`sendgsCode(code,p)`     → PID=2, serial=0 (poll status)

## Motors: momentary (hold-to-move)

Press button → send move code; **release → send STOP**. While held the app repeats the
move command (`sendCommandWithRetry`, ~200 ms cadence) as a dead-man keepalive.
`CCD_keep = 3` is a generic keepalive ping.

| Action | code | dec |
|--------|------|-----|
| STOP (all motors) | CCDstop_motor | 1 |
| generic up / down | CCD_m_up / CCD_m_down | 272 / 273 |
| motor1 stop/up/down/run | 256 / 257 / 258 / 259 |
| motor2 | 260 / 261 / 262 / 263 |
| motor3 | 264 / 265 / 266 / 267 |
| motor4 | 268 / 269 / 270 / 271 |
| combos m12/m13/m23/m24… | 274–287 (run/back pairs) |

Memory positions: `CCD_set_mlN` (784,786,…) saves, `CCD_mov_mlN` (785,787,…) moves to.
Auto/preset moves: `CCD_def_moveN` 849-863, `CCD_auto_mN` 896-899.

## Lights (LED)

| Action | code | dec |
|--------|------|-----|
| off | CCD_LED_off | 1280 |
| RGBV / white | 1281 / 1282 |
| R/G/B | 1283 / 1284 / 1285 |
| RG/RB/GB | 1286 / 1287 / 1288 |
| presets M1-M6 | 1289–1294 |
| breathing on/off | 1300 / 1297 |
| save / brightness inc | 1295 / 1305-1307 |

(Colour likely passed in `parameter` for RGBV; to confirm empirically.)

## Heat

| Action | code | dec |
|--------|------|-----|
| off | CCD_heat_off | 28672 |
| level 1-5 | 28673–28677 |
| custom | 28688 |

## Audio / "Cinesound" (likely relevant for this model)

`CCD_audio_*` 4096-4133: off 4096, pause 4097, start/play 4098, prev 4099, next 4100,
vol+ 4101, vol- 4102, mute 4103/unmute 4104, reset 4105. Bass/treble: CCB_BASS_UP/DOWN
4192/4193, CCB_HIGH_UP/DOWN 4194/4195.

## Other subsystems (present in protocol; may not exist on this sofa)
Gasbag/airbag 544-599, knead/massage 640-667, swing/rock 552-622, fan 28720-28723,
cooling 28704-28706, cup heater/cooler, drying rack 28928+, somatosensory 28708+.

## Status frames (notify, read char)
8-byte frames; app parses byte1 as pId and bytes 2-3 as a value, dispatches via
`BluetoothDataManager`. Used for position/temperature/state feedback. Not required for
open-loop control; decode later for HA sensors.

## Physical motor mapping: DFS Aventra Cinesound (empirically verified)

Two BLE controllers, each managing one seat.

### Controller 1: LEFT seat (`CFD459FB-343A-3C44-92F7-12AB706A0348`, name ECBLE583)
| Motor | up command | down command | Physical action |
|-------|-----------|--------------|-----------------|
| m1 | CCD_m1_up (257) | CCD_m1_down (258) | Main recline + footrest (mechanically linked) |
| m2 | CCD_m2_up (261) | CCD_m2_down (262) | Lumbar support (out toward sitter / in) |
| m3 | CCD_m3_up (265) | CCD_m3_down (266) | Headrest (in toward sitter / out) |
| m4 | n/a | n/a | Not connected on this unit |

### Controller 2: RIGHT seat (`F669CE71-43E6-98A0-D92A-3E0372726772`, name ECBLE583)
| Motor | up command | down command | Physical action |
|-------|-----------|--------------|-----------------|
| m1 | CCD_m1_up (257) | CCD_m1_down (258) | Main recline + footrest (assumed symmetric) |
| m2 | CCD_m2_up (261) | CCD_m2_down (262) | Lumbar support (assumed symmetric) |
| m3 | CCD_m3_up (265) | CCD_m3_down (266) | Headrest (assumed symmetric) |
| m4 | n/a | n/a | Assumed not connected |

All motor commands use PID=1 (CPID_ctrl), momentary hold pattern (repeat ~200ms, send stop on release).
Stop command: CCDstop_motor (1).

### Single BLE module: two addresses in scan
Both scan entries (`CFD459FB…` and `F669CE71…`) are the same physical device.
The sofa has ONE BLE controller advertising on two channels. Connect to either address.

### Right seat: same connection, PID=9 (CPID_ctrl_right)
Right-seat motors use the same BLE connection as left but with PID=9 instead of PID=1.
Commands `sendCode()` → PID=1 (left), `sendCodeRight()` → PID=9 (right).
Motor mapping assumed symmetric: m1=recline/footrest, m2=lumbar, m3=headrest.

### Accessories (verified on F669CE71 / same device)
| Feature | On command | Off command | Notes |
|---------|-----------|-------------|-------|
| LED | led_rgbv (1281) | led_off (1280) | ✓ works |
| Heat | heat_1 (28673) | heat_off (28672) | ✓ works |
| Audio play/pause | audio_play (4098) | audio_pause (4097) | ✓ works |
| Audio volume | audio_vol_up (4101) | audio_vol_down (4102) | ✓ works |
| Cup chiller | cup_cool_on (624) | cup_cool_off (625) | ✓ works (not 576/577) |
| Storage lid | cup_motor_up (24728) | cup_motor_down (24729) | ✓ momentary hold |
| Music vibration | audio_massage1_start (4115) | audio_massage1_stop (4114) | ✓ works (the _all_ variants 4112/4113 are unresponsive) |

Note: `cup_cold_on/off` (576/577) do not work; those codes overlap with airbag commands
for other sofa models. The correct cup chiller codes are `cup_cool_on/off` (624/625).

## Reverse-engineering source map (decompiled/)
- `utils/CommandUtils.java`: all CCD_* codes + sendCode helpers (**master reference**)
- `bean/SynData.java` + `utils/SynToByte.java`: 8-byte packing
- `utils/OrderUtil.java`: per-model up/down/stop button groupings
- `base/BaseActivity.java:330 writeData()`: the GATT write
- `normalActivity/ListActivity.java`: scan filter + connect + notify setup + status parse
- `sofaControlActivity/*`: one Activity per physical button layout
