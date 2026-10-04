#!/usr/bin/env python3
"""Dump HS-CAN frames from a CANable (slcan)."""

from __future__ import annotations

import argparse
import sys
import time

from can_bus import DEFAULT_BITRATE, open_bus


def parse_ids(text: str | None) -> set[int] | None:
    if not text:
        return None
    return {int(p.strip(), 0) for p in text.split(",") if p.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Listen to Jaguar HS-CAN via CANable")
    parser.add_argument("--channel", help="CANable path (or set CANABLE_CHANNEL)")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument("--ids", help="Only show these IDs, e.g. 0x295,0x0D0")
    parser.add_argument("--change-only", action="store_true", help="Print only when payload changes")
    parser.add_argument("--stats", type=float, metavar="SEC", help="Print ID rates every SEC seconds")
    args = parser.parse_args()

    allow = parse_ids(args.ids)
    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    last_data: dict[int, bytes] = {}
    counts: dict[int, int] = {}
    window_start = time.monotonic()

    print("Listening... Ctrl+C to stop")
    try:
        while True:
            msg = bus.recv(timeout=0.5)
            now = time.monotonic()

            if args.stats and now - window_start >= args.stats:
                ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
                total = sum(counts.values())
                print(f"\n--- {args.stats:.0f}s: {total} frames, {len(counts)} IDs ---")
                for arb_id, n in ranked[:25]:
                    hz = n / args.stats
                    print(f"  0x{arb_id:03X}  {n:5d}  ({hz:6.1f} Hz)")
                counts.clear()
                window_start = now

            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            if allow is not None and msg.arbitration_id not in allow:
                continue

            data = bytes(msg.data)
            counts[msg.arbitration_id] = counts.get(msg.arbitration_id, 0) + 1

            if args.change_only:
                prev = last_data.get(msg.arbitration_id)
                last_data[msg.arbitration_id] = data
                if prev == data:
                    continue

            print(
                f"  {msg.timestamp:10.3f}  0x{msg.arbitration_id:03X}  "
                f"[{msg.dlc}]  {data.hex(' ')}"
            )
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    finally:
        bus.shutdown()


if __name__ == "__main__":
    sys.exit(main())
