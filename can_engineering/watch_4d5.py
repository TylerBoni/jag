#!/usr/bin/env python3
"""Live-watch every byte on 0x4D5 (plug/unplug coolant).

hs_bus.dbc: i_OilTemperature = byte6, °C = raw - 60 — but we print ALL bytes
so F-Type layout differences show up.

  python watch_4d5.py
"""

from __future__ import annotations

import argparse
import sys
import time

import can

from can_bus import DEFAULT_BITRATE, open_bus

ID = 0x4D5


def main() -> int:
    p = argparse.ArgumentParser(description="Watch all bytes on 0x4D5")
    p.add_argument("--channel")
    p.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    p.add_argument(
        "--every",
        action="store_true",
        help="Print every frame (noisy); default = changes only + 2s heartbeat",
    )
    args = p.parse_args()

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    print("0x4D5 — all 8 bytes. Plug/unplug coolant; * = any byte changed.")
    print("Ctrl+C to stop.\n")
    hdr = f"{'':1}{'t':>7}  " + " ".join(f"{'b'+str(i):>4}" for i in range(8)) + "  b6°C"
    print(hdr)
    print(" " * 9 + " ".join(f"{'----':>4}" for _ in range(8)) + "  -----")

    last: bytes | None = None
    t0 = time.monotonic()
    last_print = 0.0
    n = 0
    try:
        while True:
            try:
                msg = bus.recv(timeout=0.3)
            except (ValueError, OSError, IndexError, can.CanError):
                continue
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            if msg.arbitration_id != ID:
                continue

            data = bytes(msg.data)
            if len(data) < 8:
                data = data + bytes(8 - len(data))
            n += 1
            now = time.monotonic() - t0
            changed = last is not None and data != last

            if not args.every and not changed and last is not None:
                if now - last_print < 2.0:
                    continue

            cells = []
            for i in range(8):
                if last is not None and data[i] != last[i]:
                    cells.append(f"*{data[i]:02X}*")
                else:
                    cells.append(f" {data[i]:02X} ")
            c = data[6] - 60
            flag = "*" if changed else " "
            print(f"{flag}{now:7.1f}s  " + " ".join(f"{x:>4}" for x in cells) + f"  {c:4d}°C")
            if changed and last is not None:
                who = [str(i) for i in range(8) if data[i] != last[i]]
                print(f"         changed: byte {', '.join(who)}")
            last = data
            last_print = now
    except KeyboardInterrupt:
        print(f"\nStopped. ({n} frames)")
    finally:
        bus.shutdown()
    if n == 0:
        print("No 0x4D5 seen.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
