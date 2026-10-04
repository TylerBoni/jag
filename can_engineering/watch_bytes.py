#!/usr/bin/env python3
"""Coolant plug/unplug finder — stable byte diffs only (filters bus noise).

Your earlier run ranked vanishing garbage IDs (0x805, 0xC0B, …). Those are
slcan/noise, not the sensor. This version only compares IDs that:
  - are standard 11-bit (0x000–0x7FF)
  - appear in BOTH captures with enough frames
  - have a byte whose median actually moved (counters ignored)

  python watch_bytes.py --unplug
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import defaultdict

import can

from can_bus import DEFAULT_BITRATE, open_bus

# Always-noisy body/cluster frames (not coolant)
NOISE_IDS = {
    0x217,  # battery / charge toggles
    0x257,  # RTC counter
    0x280,  # steering
    0x293,  # rolling
    0x255,  # bit7 toggle
    0x337,  # doors
    0x380,  # checksum soup
    0x397,
    0x3B9,  # park brake warnings
    0x3F3,  # gear
    0x4FF,  # clock counter
    0x4FD,
}


def median(xs: list[int]) -> float:
    s = sorted(xs)
    n = len(s)
    if not n:
        return 0.0
    m = n // 2
    return float(s[m]) if n % 2 else (s[m - 1] + s[m]) / 2.0


def looks_like_counter(samples: list[int]) -> bool:
    if len(samples) < 20:
        return False
    steps = checked = 0
    for a, b in zip(samples, samples[1:]):
        if a == b:
            continue
        checked += 1
        d = (b - a) & 0xFF
        if d in (1, 255) or d in (8, 248):  # +1/-1 or +8 staircases
            steps += 1
    return checked >= 12 and steps / checked >= 0.55


def is_standard_id(arb: int) -> bool:
    return 0 <= arb <= 0x7FF


def capture(bus, seconds: float) -> tuple[dict[int, dict[int, list[int]]], dict[int, int]]:
    """Returns (arb -> byte -> samples), (arb -> frame count)."""
    end = time.monotonic() + seconds
    by: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[int, int] = defaultdict(int)
    frames = 0
    junk = 0
    while time.monotonic() < end:
        try:
            msg = bus.recv(timeout=0.2)
        except (ValueError, OSError, IndexError, can.CanError):
            junk += 1
            continue
        if msg is None or msg.is_error_frame or msg.is_remote_frame:
            continue
        arb = msg.arbitration_id
        if msg.is_extended_id or not is_standard_id(arb):
            junk += 1
            continue
        if arb in NOISE_IDS:
            continue
        frames += 1
        counts[arb] += 1
        for i, b in enumerate(bytes(msg.data)):
            by[arb][i].append(b)
    print(f"  {frames} frames, {len(by)} IDs (skipped {junk} junk/noise)")
    return by, counts


def unplug_diff(bus, seconds: float, min_frames: int) -> None:
    print(
        "Stable unplug diff — ignores vanish/appear noise & counters.\n"
        "Keep ignition ON, don't touch anything except the coolant sensor.\n"
    )
    input(f"Sensor PLUGGED — Enter to capture ({seconds:.0f}s)…")
    a, ca = capture(bus, seconds)

    print("\n>>> Change the coolant sensor (unplug OR plug), wait 2s.")
    input(f"Enter for second capture ({seconds:.0f}s)…")
    b, cb = capture(bus, seconds)

    rows = []
    common = set(a) & set(b)
    only_a = set(a) - set(b)
    only_b = set(b) - set(a)
    print(f"\nIDs in both={len(common)}  only-A={len(only_a)}  only-B={len(only_b)}")

    for arb in sorted(common):
        if ca[arb] < min_frames or cb[arb] < min_frames:
            continue
        for bi in range(8):
            sa, sb = a[arb].get(bi, []), b[arb].get(bi, [])
            if len(sa) < min_frames or len(sb) < min_frames:
                continue
            if looks_like_counter(sa) or looks_like_counter(sb):
                continue
            # Must be relatively stable within each window
            if (max(sa) - min(sa)) > 25 and len(set(sa)) > 8:
                continue
            if (max(sb) - min(sb)) > 25 and len(set(sb)) > 8:
                continue
            ma, mb = median(sa), median(sb)
            d = abs(mb - ma)
            if d < 4:
                continue
            rows.append((d, arb, bi, ma, mb, ca[arb], cb[arb]))

    rows.sort(key=lambda r: r[0], reverse=True)
    print("\nStable byte changes (likely sensor-related):")
    if not rows:
        print(
            "  None. Coolant may not be on this HS tap / ECM not broadcasting,\n"
            "  or the sensor isn't reflected on CAN (local ECM only)."
        )
        # Show if any ECM-ish IDs present
        for arb in (0x295, 0x4D5, 0x0D9, 0x3D3):
            n1, n2 = ca.get(arb, 0), cb.get(arb, 0)
            print(f"  0x{arb:03X}: plugged n={n1}  unplugged n={n2}")
        return

    print(f"{'#':>3}  {'ID':>6}  {'b':>2}  {'Δ':>4}  {'A→B raw':>12}  {'as°C+60':>12}  n")
    for i, (d, arb, bi, ma, mb, na, nb) in enumerate(rows[:25], 1):
        print(
            f"{i:3d}  0x{arb:03X}  {bi:2d}  {d:4.0f}  "
            f"{ma:5.0f}→{mb:<5.0f}  {ma-60:5.0f}→{mb-60:<5.0f}  {na}/{nb}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description="Stable coolant plug/unplug byte finder")
    p.add_argument("--channel")
    p.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    p.add_argument("--unplug", action="store_true", default=True)
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--min-frames", type=int, default=30)
    args = p.parse_args()

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    try:
        unplug_diff(bus, args.seconds, args.min_frames)
        return 0
    finally:
        bus.shutdown()


if __name__ == "__main__":
    sys.exit(main())
