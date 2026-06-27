# cinesound-home-assistant

I recently bought a [DFS Aventra Cinesound sofa](https://www.dfs.ie/aventra/arv12chsp). It has motorised recline, lumbar and headrest adjustment, LED lighting, seat heating, built-in Cinesound speakers, a chilled cup holder, a motorised storage compartment, and vibration in time with music. It comes with an Android/iOS app to control all of this, but there was no Home Assistant integration. So I built one.

This repo documents the reverse-engineering of the official Android app (`com.ykd.zhihuijiaju`) and contains a working local Home Assistant custom integration. Everything runs over Bluetooth LE: no cloud, no account required.

If this saved you some time, feel free to buy me a coffee:

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/florian.ie/)

---

## Installation

### HACS (recommended)

> **Requires [HACS](https://hacs.xyz) to be installed in Home Assistant.**

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=xadacka&repository=cinesound-home-assistant&category=integration)

Or add it manually in HACS:
1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Paste `https://github.com/xadacka/cinesound-home-assistant`, select category **Integration**, click **Add**
3. Search for "Cinesound" and install
4. Restart Home Assistant

### Manual install

```bash
cp -r custom_components/cinesound \
      /path/to/homeassistant/config/custom_components/
```

Restart Home Assistant.

---

## Setup

Make sure your sofa is powered on. Home Assistant will auto-discover it via Bluetooth (it advertises service UUID `6e403587-b5a3-f393-e0a9-e50e24dcca9e`).

When a notification appears, click **Configure**. Or go to **Settings → Devices & Services → Add Integration** and search for **Cinesound**.

> The sofa's Bluetooth name is `ECBLE583`. It appears twice in BLE scans; both entries are the same physical module. Connect to either one.

---

## Entities

All entities appear under a single **DFS Aventra Cinesound** device.

| Entity | Type | Description |
|--------|------|-------------|
| Left / Right Recline | Cover | Main recline + footrest (open = reclined) |
| Left / Right Lumbar | Cover | Lumbar support (open = extended) |
| Left / Right Headrest | Cover | Headrest (open = toward sitter) |
| Storage Compartment | Cover | Motorised drinks compartment lid |
| LED | Light | Ambient lighting with colour wheel + effects |
| Seat Heat | Select | Off / Level 1–5 |
| Audio | Media Player | Play/pause, skip, volume, mute |
| Cup Chiller | Switch | Chilled cup holder |
| Music Vibration | Switch | Vibration motors synced to audio |

**Cover entities** send a single move command (the sofa keeps moving autonomously) and auto-stop after 60 seconds as a safety backstop. Tap **Stop** in HA to halt immediately.

**LED** supports a colour wheel (quantised to Red, Green, Blue, Yellow, Cyan, Magenta, White) plus effects: Rainbow, Breathing, and Modes 1–6.

---

## How it works

The sofa is controlled by the Android app `com.ykd.zhihuijiaju` ("Smart furniture" by YKD, a white-label app covering dozens of furniture models). I decompiled the APK with jadx and found a clean Bluetooth LE GATT protocol: 8-byte little-endian command packets written to a custom service, no cloud dependency, no pairing required.

Full protocol documentation: [notes/protocol.md](notes/protocol.md)

### Repo layout

```
custom_components/cinesound/   ← Home Assistant integration
scripts/                       ← Python test harness (bleak)
  scan.py                      ← Find the sofa over BLE from your Mac
  sofa.py                      ← Interactive REPL to probe commands
  sofa_protocol.py             ← Shared protocol module
notes/protocol.md              ← Reverse-engineered BLE protocol spec
apk/                           ← Downloaded APK (git-ignored)
decompiled/                    ← jadx output (git-ignored)
```

### Test harness (no HA needed)

Requires Python 3.11+ and the sofa's phone app fully closed (BLE allows one connection).

```bash
python3 -m venv .venv && .venv/bin/pip install bleak
.venv/bin/python scripts/scan.py                          # find the sofa
.venv/bin/python scripts/sofa.py <ADDRESS>                # interactive REPL
```

---

## Requirements

- Home Assistant 2024.1+
- A Bluetooth adapter within range of the sofa (or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html))
- The official sofa app closed on your phone while HA is connected

## Compatibility

Reverse-engineered from app version 1.1 (versionCode 23). The protocol is shared across many YKD furniture models so it may work with other sofas using the same app, but only the DFS Aventra Cinesound has been tested.
