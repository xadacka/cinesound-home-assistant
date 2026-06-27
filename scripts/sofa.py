#!/usr/bin/env python3
"""Interactive control / protocol-validation REPL for the Cinesound sofa.

    python scripts/sofa.py <ADDRESS>          # macOS uses a CoreBluetooth UUID, not a MAC

Connects, subscribes to status notifications (printed as hex), and lets you
fire commands by name or code to discover what each does on YOUR sofa.

REPL commands:
    <name|code> [param]   send one packet (PID=1).  e.g.  m1_up   |  257   |  led_rgbv 255
    r <name|code> [param] send to the RIGHT side (PID=9)
    hold <name|code>      send the move, wait for Enter, then send stop_motor
    move <name> <secs>    send move, repeat every 0.15s for <secs>, then stop (dead-man)
    stop                  send stop_motor (panic)
    raw <hex>             write raw bytes, e.g.  raw 0102010100000000
    list [filter]         list known command names
    quit
"""
import asyncio
import sys
from bleak import BleakClient, BleakScanner

import sofa_protocol as P


def hexs(b: bytes) -> str:
    return b.hex(" ")


def on_notify(_char, data: bytearray):
    print(f"\n<< status: {hexs(bytes(data))}")
    print("> ", end="", flush=True)


async def send(client, name_or_code, param=0, pid=P.PID_CTRL):
    code = P.resolve(name_or_code)
    pkt = P.build_packet(code, param, pid=pid)
    # Characteristic advertises WRITE (with-response) only, not WRITE_NO_RESPONSE.
    # macOS CoreBluetooth silently drops response=False on such characteristics.
    await client.write_gatt_char(P.WRITE_UUID, pkt, response=True)
    print(f">> sent {name_or_code} (code={code}, param={param}, pid={pid}): {hexs(pkt)}")


async def repl(client):
    loop = asyncio.get_event_loop()
    print("\nConnected. Type 'help' for commands, 'stop' to halt, 'quit' to exit.\n")
    while True:
        line = (await loop.run_in_executor(None, input, "> ")).strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                break
            if cmd in ("help", "?"):
                print(__doc__)
            elif cmd == "gatt":
                # Dump every service + characteristic with properties and UUIDs
                print("\n=== GATT services on device ===")
                for svc in client.services:
                    print(f"\nSERVICE {svc.uuid}  handle={svc.handle}")
                    for ch in svc.characteristics:
                        props = ",".join(ch.properties)
                        desc_uuids = [d.uuid for d in ch.descriptors]
                        print(f"  CHAR {ch.uuid}  handle={ch.handle}  props=[{props}]")
                        for d in ch.descriptors:
                            print(f"    DESC {d.uuid}  handle={d.handle}")
                print()
            elif cmd == "poll":
                # Send a get-state request (PID=2) for current status
                code = int(parts[1], 0) if len(parts) > 1 else 0
                pkt = P.build_packet(code, 0, pid=P.PID_GET_STATE, serial=0)
                await client.write_gatt_char(P.WRITE_UUID, pkt, response=False)
                print(f">> poll code={code}: {hexs(pkt)}")
            elif cmd == "read":
                # Read the read/notify characteristic directly
                data = await client.read_gatt_char(P.NOTIFY_UUID)
                print(f"<< read: {hexs(bytes(data))}")
            elif cmd == "wwrite":
                # Same as normal send but write-WITH-response (for diagnosis)
                code = P.resolve(parts[1]) if len(parts) > 1 else 1
                param = int(parts[2], 0) if len(parts) > 2 else 0
                pkt = P.build_packet(code, param)
                await client.write_gatt_char(P.WRITE_UUID, pkt, response=True)
                print(f">> wwrite (with-response) code={code}: {hexs(pkt)}")
            elif cmd == "list":
                filt = parts[1] if len(parts) > 1 else ""
                for k, v in sorted(P.CMD.items(), key=lambda kv: kv[1]):
                    if filt in k:
                        print(f"  {k:<16} {v}")
            elif cmd == "stop":
                await send(client, "stop_motor")
            elif cmd == "raw":
                await client.write_gatt_char(P.WRITE_UUID, bytes.fromhex(parts[1]),
                                             response=True)
                print(f">> raw {parts[1]}")
            elif cmd == "r":
                param = int(parts[2], 0) if len(parts) > 2 else 0
                await send(client, parts[1], param, pid=P.PID_CTRL_RIGHT)
            elif cmd == "hold":
                await send(client, parts[1])
                await loop.run_in_executor(None, input, "   ...holding; Enter to STOP")
                await send(client, "stop_motor")
            elif cmd == "move":
                secs = float(parts[2])
                end = loop.time() + secs
                while loop.time() < end:
                    await send(client, parts[1])
                    await asyncio.sleep(0.15)
                await send(client, "stop_motor")
            else:
                param = int(parts[1], 0) if len(parts) > 1 else 0
                await send(client, cmd, param)
        except Exception as e:  # noqa: BLE001 - REPL, keep going
            print(f"!! {e}")


async def main(address: str):
    print(f"Connecting to {address} ...")
    async with BleakClient(address, timeout=20.0) as client:
        print("Connected:", client.is_connected)
        try:
            await client.start_notify(P.NOTIFY_UUID, on_notify)
            print(f"Subscribed to status notifications ({P.NOTIFY_UUID}).")
        except Exception as e:  # noqa: BLE001
            print(f"(could not subscribe to notifications: {e})")
        await repl(client)
        print("Disconnecting.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/sofa.py <ADDRESS>")
        print("(run scripts/scan.py first to find the address)")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
