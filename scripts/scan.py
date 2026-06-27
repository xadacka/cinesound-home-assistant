#!/usr/bin/env python3
"""Scan for the Cinesound sofa.

The sofa advertises service UUID 6e403587-b5a3-f393-e0a9-e50e24dcca9e.
Run with the sofa powered on and the phone app FULLY CLOSED (BLE allows one
central connection at a time; the app will hold it otherwise).

    python scripts/scan.py
"""
import asyncio
from bleak import BleakScanner

TARGET_SERVICE = "6e403587-b5a3-f393-e0a9-e50e24dcca9e"


async def main(seconds: float = 10.0):
    print(f"Scanning {seconds:.0f}s for BLE devices (looking for service "
          f"{TARGET_SERVICE})...\n")
    found = await BleakScanner.discover(timeout=seconds, return_adv=True)

    matches = []
    rows = []
    for address, (dev, adv) in found.items():
        uuids = [u.lower() for u in (adv.service_uuids or [])]
        is_match = TARGET_SERVICE in uuids
        name = adv.local_name or dev.name or "(no name)"
        rows.append((adv.rssi, address, name, is_match, uuids))
        if is_match:
            matches.append((address, name, adv.rssi))

    rows.sort(key=lambda r: r[0], reverse=True)
    print(f"{'RSSI':>5}  {'ADDRESS':<38}  NAME")
    print("-" * 70)
    for rssi, address, name, is_match, uuids in rows:
        mark = "  <== SOFA" if is_match else ""
        print(f"{rssi:>5}  {address:<38}  {name}{mark}")

    # Show manufacturer data for sofa matches (model-type byte is key)
    if matches:
        print("\n=== Manufacturer-specific data for sofa devices ===")
        for address, (dev, adv) in found.items():
            if TARGET_SERVICE in [u.lower() for u in (adv.service_uuids or [])]:
                mfr = adv.manufacturer_data
                print(f"  {address}  mfr_data={dict(mfr) if mfr else 'none'}")

    print()
    if matches:
        print("MATCH: sofa(s) advertising the target service:")
        for address, name, rssi in matches:
            print(f"  {address}  name={name!r}  rssi={rssi}")
        print("\nNext: python scripts/sofa.py <ADDRESS>")
    else:
        print("No device advertised the target service UUID.")
        print("- Make sure the sofa is powered and the phone app is fully closed.")
        print("- Some units don't advertise the service UUID; look above for a")
        print("  device whose name starts with 'EC' or looks furniture-related,")
        print("  and try: python scripts/sofa.py <ADDRESS>")


if __name__ == "__main__":
    asyncio.run(main())
