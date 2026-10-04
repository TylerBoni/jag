#!/usr/bin/env python3
"""Find F-Type tach / RPM candidates on HS-CAN via CANable.

Workflow (car running, OBD-II HS-CAN pins 6/14, 500 kbit/s):
  1. Capture IDLE baseline with foot off throttle.
  2. Capture REV while you blip / hold higher RPM.
  3. Rank CAN IDs whose byte fields move like engine speed.

Related Jaguar HS RPM encodings (not confirmed for X152 F-Type):
  XF facelift: 0x295 bytes 6–7 BE, raw & 0x1FFF
  XF pre-facelift: 0x099 bytes 4–5 BE, raw & ~0xE000
  This repo's tach.py probe: 0x0D0 bytes 4–5 BE, high nibble masked
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from can_bus import DEFAULT_BITRATE, open_bus

# (name, byte_offset, length, big_endian, mask_or_none)
DECODE_CANDIDATES = [
    ("be16@0", 0, 2, True, None),
    ("be16@1", 1, 2, True, None),
    ("be16@2", 2, 2, True, None),
    ("be16@3", 3, 2, True, None),
    ("be16@4", 4, 2, True, None),
    ("be16@5", 5, 2, True, None),
    ("be16@6", 6, 2, True, None),
    ("le16@0", 0, 2, False, None),
    ("le16@1", 1, 2, False, None),
    ("le16@2", 2, 2, False, None),
    ("le16@3", 3, 2, False, None),
    ("le16@4", 4, 2, False, None),
    ("le16@5", 5, 2, False, None),
    ("le16@6", 6, 2, False, None),
    ("be16@4&1FFF", 4, 2, True, 0x1FFF),
    ("be16@6&1FFF", 6, 2, True, 0x1FFF),
    ("be16@4&0FFF", 4, 2, True, 0x0FFF),
    ("be16@6&0FFF", 6, 2, True, 0x0FFF),
]


@dataclass
class FieldStats:
    values: list[int] = field(default_factory=list)

    def add(self, value: int) -> None:
        self.values.append(value)

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.values) if self.values else 0.0

    @property
    def vmin(self) -> int:
        return min(self.values) if self.values else 0

    @property
    def vmax(self) -> int:
        return max(self.values) if self.values else 0

    @property
    def unique(self) -> int:
        return len(set(self.values))


@dataclass
class IdCapture:
    count: int = 0
    last_data: bytes = b""
    fields: dict[str, FieldStats] = field(default_factory=lambda: defaultdict(FieldStats))


def decode_field(data: bytes, offset: int, length: int, big_endian: bool, mask: Optional[int]) -> Optional[int]:
    if offset + length > len(data):
        return None
    chunk = data[offset : offset + length]
    value = int.from_bytes(chunk, "big" if big_endian else "little", signed=False)
    if mask is not None:
        value &= mask
    return value


def capture_window(bus, seconds: float, label: str) -> dict[int, IdCapture]:
    print(f"\n=== {label}: capturing {seconds:.1f}s — keep that RPM steady ===")
    end = time.monotonic() + seconds
    by_id: dict[int, IdCapture] = defaultdict(IdCapture)
    frames = 0

    while time.monotonic() < end:
        msg = bus.recv(timeout=0.2)
        if msg is None or msg.is_error_frame or msg.is_remote_frame:
            continue
        frames += 1
        cap = by_id[msg.arbitration_id]
        cap.count += 1
        data = bytes(msg.data)
        cap.last_data = data
        for name, offset, length, be, mask in DECODE_CANDIDATES:
            value = decode_field(data, offset, length, be, mask)
            if value is not None:
                cap.fields[name].add(value)

    print(f"  got {frames} frames across {len(by_id)} IDs")
    return by_id


def rpmish_score(idle: FieldStats, rev: FieldStats) -> tuple[float, str]:
    """Higher score = more likely engine speed. Returns (score, reason)."""
    if idle.n < 5 or rev.n < 5:
        return 0.0, "too few samples"

    if rev.mean <= idle.mean * 1.05 and rev.mean <= idle.mean + 50:
        return 0.0, "did not rise on rev"

    # Prefer values in a plausible RPM band (idle ~600–1000, rev < ~9000).
    if not (400 <= idle.mean <= 1600):
        # Still allow scaled encodings (e.g. rpm*4) but score lower.
        scale_penalty = 0.35
    else:
        scale_penalty = 1.0

    if rev.vmax > 12000:
        return 0.0, f"rev max {rev.vmax} implausible for raw RPM"

    rise = rev.mean - idle.mean
    if rise < 80:
        return 0.0, "rise too small"

    # Stable at idle, more movement when revving is good.
    idle_spread = idle.vmax - idle.vmin
    rev_spread = rev.vmax - rev.vmin
    stability = 1.0 / (1.0 + idle_spread / 50.0)

    # Prefer integer-ish RPM ranges rather than tiny counters.
    uniqueness = min(idle.unique + rev.unique, 40) / 40.0

    score = rise * scale_penalty * (0.5 + 0.5 * stability) * (0.5 + 0.5 * uniqueness)
    if 500 <= idle.mean <= 1200 and 1500 <= rev.mean <= 7000:
        score *= 1.5
        reason = f"idle≈{idle.mean:.0f} rev≈{rev.mean:.0f} (+{rise:.0f})"
    else:
        reason = f"idle≈{idle.mean:.0f} rev≈{rev.mean:.0f} (+{rise:.0f}, maybe scaled)"

    if rev_spread < 20 and rise > 200:
        score *= 1.1  # held steady higher RPM

    return score, reason


def rank_candidates(idle: dict[int, IdCapture], rev: dict[int, IdCapture], top: int) -> list[tuple]:
    rows = []
    ids = set(idle) | set(rev)
    for arb_id in ids:
        i_cap = idle.get(arb_id)
        r_cap = rev.get(arb_id)
        if not i_cap or not r_cap:
            continue
        for name, _, _, _, _ in DECODE_CANDIDATES:
            i_field = i_cap.fields.get(name)
            r_field = r_cap.fields.get(name)
            if not i_field or not r_field:
                continue
            score, reason = rpmish_score(i_field, r_field)
            if score <= 0:
                continue
            rows.append((score, arb_id, name, reason, i_cap.count, r_cap.count, i_cap.last_data, r_cap.last_data))

    rows.sort(key=lambda r: r[0], reverse=True)
    return rows[:top]


def print_rankings(rows: list[tuple]) -> None:
    if not rows:
        print("\nNo RPM-like candidates. Try a bigger idle→rev gap, longer capture, or check wiring/bitrate.")
        return

    print("\nTop tach candidates (higher score = more RPM-like):")
    print(f"{'#':>3}  {'ID':>6}  {'field':<14}  {'score':>8}  {'idle n':>6}  {'rev n':>6}  note")
    for i, (score, arb_id, name, reason, ic, rc, _, _) in enumerate(rows, 1):
        print(f"{i:3d}  0x{arb_id:03X}  {name:<14}  {score:8.1f}  {ic:6d}  {rc:6d}  {reason}")

    best = rows[0]
    _, arb_id, name, reason, _, _, idle_data, rev_data = best
    print(f"\nBest guess: ID 0x{arb_id:03X} field {name} — {reason}")
    print(f"  last idle data: {idle_data.hex(' ')}")
    print(f"  last rev  data: {rev_data.hex(' ')}")
    print(
        "\nNext: run listen with --id filter, or update tach.py arbitration_id / byte layout to match."
    )


def live_watch(bus, ids: Optional[set[int]], hz: float) -> None:
    """Print changing payloads; highlight IDs that move when you rev."""
    print("\nLive watch — rev the engine and look for IDs that track the tach.")
    print("Ctrl+C to stop.\n")
    last: dict[int, bytes] = {}
    last_print = 0.0
    interval = 1.0 / hz if hz > 0 else 0.0

    try:
        while True:
            msg = bus.recv(timeout=0.5)
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            if ids is not None and msg.arbitration_id not in ids:
                continue
            data = bytes(msg.data)
            prev = last.get(msg.arbitration_id)
            changed = prev is not None and prev != data
            last[msg.arbitration_id] = data
            now = time.monotonic()
            if interval and now - last_print < interval and not changed:
                continue
            if changed or prev is None:
                flag = " *" if changed else "  "
                print(f"{flag} 0x{msg.arbitration_id:03X}  {data.hex(' ')}")
                last_print = now
    except KeyboardInterrupt:
        print("\nStopped.")


def parse_id_list(text: str) -> set[int]:
    out = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        out.add(int(part, 0))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Find Jaguar F-Type tach/RPM on HS-CAN")
    parser.add_argument("--channel", help="CANable path, e.g. /dev/cu.usbmodem...")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument("--idle-seconds", type=float, default=8.0, help="Idle capture length")
    parser.add_argument("--rev-seconds", type=float, default=8.0, help="Rev capture length")
    parser.add_argument("--top", type=int, default=20, help="How many candidates to show")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Skip diff; live-print frames (optionally --ids)",
    )
    parser.add_argument("--ids", help="Comma-separated IDs for --watch, e.g. 0x295,0x0D0")
    parser.add_argument("--watch-hz", type=float, default=20.0, help="Max print rate for --watch")
    args = parser.parse_args()

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    try:
        if args.watch:
            id_set = parse_id_list(args.ids) if args.ids else None
            live_watch(bus, id_set, args.watch_hz)
            return 0

        print(
            "Parked, running, in P/N. Foot OFF throttle for idle capture.\n"
            "Press Enter when idle is stable..."
        )
        input()
        idle = capture_window(bus, args.idle_seconds, "IDLE")

        print(
            "\nNow raise RPM (blip or hold ~2500–4000) and keep it there during capture.\n"
            "Press Enter to start REV capture..."
        )
        input()
        rev = capture_window(bus, args.rev_seconds, "REV")

        rows = rank_candidates(idle, rev, args.top)
        print_rankings(rows)

        if rows:
            print("\nOptional: live-watch the top IDs:")
            uniq = []
            for _, arb_id, *_ in rows:
                if arb_id not in uniq:
                    uniq.append(arb_id)
                if len(uniq) >= 5:
                    break
            id_csv = ",".join(f"0x{i:X}" for i in uniq)
            print(f"  python find_tach.py --watch --ids {id_csv}")
        return 0
    finally:
        bus.shutdown()


if __name__ == "__main__":
    sys.exit(main())
