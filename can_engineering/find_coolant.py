#!/usr/bin/env python3
"""Find / watch engine coolant temp per hs_bus.dbc.

DBC (facelift XF — best HS map we have for F-Type):
  0x4D5  i_OilTemperature   byte6, phys_C = raw - 60   ← engine temp / cluster gauge
  0x3D3  i_TransmissionOilTemp  °C+40                 ← gearbox oil (NOT coolant)
  0x315  i_AirTemperature   10-bit                    ← ambient
  0x295  RPM only — never coolant
  0x355  engine-temp WARNING bits only (no °C value)

  python find_coolant.py              # decode 0x4D5 + scan other temp-like bytes
  python find_coolant.py --watch      # live 0x4D5 i_OilTemperature
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field

from can_bus import DEFAULT_BITRATE, open_bus
from dbc_decode import default_dbc_path, load_dbc_names

import can

# Always noisy / known-not-coolant (even if not filtering whole DBC)
SKIP_IDS = {
    0x295,  # RPM
    0x255,  # bit7 toggle / alive
    0x293,  # rolling field (Δ8 staircase) — not temp
    0x380,  # checksum/counter noise
    0x3D3,  # transmission oil
    0x3F3,  # gear position
    0x315,  # ambient air
}

# Still show these DBC IDs when filtering "known" traffic (coolant hunt)
KEEP_WHEN_FILTERING = {
    0x4D5,  # i_OilTemperature
}


TEMP_OFFSETS = (40, 60)
COOL_MIN_C = -20.0
COOL_MAX_C = 130.0

# Primary DBC target
ID_ECM_TEMP = 0x4D5
BYTE_OIL_TEMP = 6
OFFSET_OIL_TEMP = 60


@dataclass
class ByteTrack:
    samples: list[int] = field(default_factory=list)
    times: list[float] = field(default_factory=list)

    def add(self, raw: int, t: float) -> None:
        self.samples.append(raw)
        self.times.append(t)

    @property
    def n(self) -> int:
        return len(self.samples)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.samples) if self.samples else 0.0

    @property
    def vmin(self) -> int:
        return min(self.samples) if self.samples else 0

    @property
    def vmax(self) -> int:
        return max(self.samples) if self.samples else 0

    @property
    def unique(self) -> int:
        return len(set(self.samples))

    @property
    def last(self) -> int:
        return self.samples[-1] if self.samples else 0


@dataclass
class IdTrack:
    count: int = 0
    last_data: bytes = b""
    bytes_: dict[int, ByteTrack] = field(default_factory=lambda: defaultdict(ByteTrack))


def as_c(raw: int, offset: int) -> float:
    return float(raw - offset)


def as_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def in_coolant_band(raw: int, offset: int) -> bool:
    c = as_c(raw, offset)
    return COOL_MIN_C <= c <= COOL_MAX_C


def looks_like_counter(samples: list[int]) -> bool:
    if len(samples) < 12:
        return False
    steps = 0
    checked = 0
    for a, b in zip(samples, samples[1:]):
        if a == b:
            continue
        checked += 1
        if (b - a) & 0xFF in (1, 255):
            steps += 1
    return checked >= 8 and steps / checked >= 0.7


def score_byte(track: ByteTrack, offset: int) -> tuple[float, str]:
    if track.n < 8:
        return 0.0, "too few"
    if looks_like_counter(track.samples):
        return 0.0, "rolling counter"
    ok = sum(1 for r in track.samples if in_coolant_band(r, offset))
    if ok / track.n < 0.85:
        return 0.0, "out of band"

    mean_c = as_c(track.mean, offset)
    last_c = as_c(track.last, offset)
    spread = track.vmax - track.vmin
    if track.unique > 40 and spread > 30:
        return 0.0, "looks like counter"

    band = 1.0
    if 0 <= mean_c <= 110:
        band = 1.4
    if 10 <= mean_c <= 50:
        band *= 1.15

    drift_bonus = 1.0 + min(spread, 15) * 0.04
    if spread == 0:
        drift_bonus = 1.05
    if spread > 25:
        drift_bonus *= 0.4

    uniqueness_pen = 1.0
    if track.unique <= 3:
        uniqueness_pen = 1.2
    elif track.unique > 20:
        uniqueness_pen = 0.5

    score = band * drift_bonus * uniqueness_pen * (ok / track.n) * 10.0
    reason = (
        f"≈{mean_c:.0f}°C ({as_f(mean_c):.0f}°F) last={last_c:.0f}°C "
        f"raw={track.last} Δ={spread} uniq={track.unique}"
    )
    return score, reason


def capture(bus, seconds: float) -> dict[int, IdTrack]:
    print(f"Capturing {seconds:.0f}s (no TX)…")
    end = time.monotonic() + seconds
    by_id: dict[int, IdTrack] = defaultdict(IdTrack)
    frames = 0
    t0 = time.monotonic()

    while time.monotonic() < end:
        msg = bus.recv(timeout=0.2)
        if msg is None or msg.is_error_frame or msg.is_remote_frame:
            continue
        if msg.arbitration_id in SKIP_IDS:
            continue
        frames += 1
        t = time.monotonic() - t0
        tr = by_id[msg.arbitration_id]
        tr.count += 1
        data = bytes(msg.data)
        tr.last_data = data
        for i, b in enumerate(data):
            tr.bytes_[i].add(b, t)

    print(f"  {frames} frames, {len(by_id)} IDs")
    return by_id


def rank(by_id: dict[int, IdTrack], top: int) -> list[tuple]:
    rows = []
    for arb_id, tr in by_id.items():
        for bi, bt in tr.bytes_.items():
            for off in TEMP_OFFSETS:
                score, reason = score_byte(bt, off)
                if score <= 0:
                    continue
                if arb_id == ID_ECM_TEMP and bi == BYTE_OIL_TEMP and off == OFFSET_OIL_TEMP:
                    score *= 3.0
                    reason = "DBC i_OilTemperature — " + reason
                rows.append((score, arb_id, bi, off, reason, tr.count, tr.last_data))
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows[:top]


def print_rankings(rows: list[tuple]) -> None:
    if not rows:
        print("\nNo temp-like bytes. Is 0x4D5 on the bus?")
        return
    print("\nCandidates (DBC primary = 0x4D5 byte6 °C+60):")
    print(f"{'#':>3}  {'ID':>6}  {'byte':>4}  {'off':>3}  {'score':>6}  {'n':>6}  note")
    for i, (score, arb_id, bi, off, reason, n, _) in enumerate(rows, 1):
        print(f"{i:3d}  0x{arb_id:03X}  {bi:4d}  +{off:<2}  {score:6.1f}  {n:6d}  {reason}")


def print_dbc_target(by_id: dict[int, IdTrack]) -> None:
    print("\nDBC target 0x4D5 i_OilTemperature (byte6, °C+60):")
    tr = by_id.get(ID_ECM_TEMP)
    if not tr:
        print("  (not seen — ECM not on bus)")
        return
    d = tr.last_data
    print(f"  last: {d.hex(' ')}  n={tr.count}")
    if len(d) > BYTE_OIL_TEMP:
        raw = d[BYTE_OIL_TEMP]
        c = as_c(raw, OFFSET_OIL_TEMP)
        bt = tr.bytes_.get(BYTE_OIL_TEMP)
        spread = (bt.vmax - bt.vmin) if bt else 0
        print(f"  byte6 raw={raw} → {c:.0f}°C / {as_f(c):.0f}°F  Δ={spread}")


def live_watch(bus, seconds: float | None) -> None:
    """Monitor only 0x4D5 with full hs_bus.dbc decode."""
    import tempfile
    from pathlib import Path

    import cantools

    raw_dbc = Path(default_dbc_path()).read_text(encoding="utf-8", errors="replace")
    cleaned = "\n".join(l for l in raw_dbc.splitlines() if not l.strip().startswith("//"))
    with tempfile.NamedTemporaryFile("w", suffix=".dbc", delete=False) as tmp:
        tmp.write(cleaned)
        tmp_path = tmp.name
    db = cantools.database.load_file(tmp_path, strict=False)
    msg_def = db.get_message_by_frame_id(ID_ECM_TEMP)

    print("0x4D5 monitor — hs_bus.dbc c_HS_ECM_ETM_Status")
    print("  signals: i_OilTemperature (byte6, °C=raw-60), oil-level fault, water-in-fuel")
    print("  Ctrl+C to stop.\n")
    print(f"{'':1}{'t':>7}  {'payload':<23}  {'°C':>7}  {'°F':>7}  decoded")

    t0 = time.monotonic()
    end = (t0 + seconds) if seconds else None
    last_data: bytes | None = None
    n = 0
    hz_t = t0
    hz_n = 0
    try:
        while True:
            if end and time.monotonic() >= end:
                break
            try:
                msg = bus.recv(timeout=0.3)
            except (ValueError, OSError, IndexError, can.CanError):
                continue
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            if msg.arbitration_id != ID_ECM_TEMP:
                continue

            data = bytes(msg.data)
            if len(data) < 8:
                data = data + bytes(8 - len(data))
            n += 1
            hz_n += 1
            now = time.monotonic() - t0
            changed = last_data is not None and data != last_data
            if not changed and last_data is not None and n % 20 != 0:
                continue
            last_data = data

            try:
                vals = msg_def.decode(data, decode_choices=True, scaling=True)
            except Exception as exc:
                vals = {}
                print(f"  decode err: {exc}")

            oil_c = float(vals.get("i_OilTemperature", data[6] - 60))
            oil_f = as_f(oil_c)
            parts = []
            for name, val in vals.items():
                if name == "i_OilTemperature":
                    continue
                parts.append(f"{name}={val}")
            extra = "  ".join(parts) if parts else "—"

            rate = ""
            elapsed = time.monotonic() - hz_t
            if elapsed >= 2.0:
                rate = f"  [{hz_n / elapsed:.0f} Hz]"
                hz_t = time.monotonic()
                hz_n = 0

            flag = "*" if changed else " "
            print(
                f"{flag}{now:7.1f}s  {data.hex(' '):<23}  {oil_c:7.1f}  {oil_f:7.1f}  {extra}{rate}"
            )
            if changed or n <= 2:
                print(
                    f"         bytes: "
                    + " ".join(f"[{i}]={data[i]:02X}" for i in range(8))
                )
    except KeyboardInterrupt:
        print("\nStopped.")
    if last_data is None:
        print("No 0x4D5 frames seen.")


def median(xs: list[int]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def unplug_diff(bus, seconds: float) -> None:
    """Baseline → user unplugs coolant sensor → second capture → rank biggest jumps."""
    print(
        "UNPLUG DIFF — find which CAN byte reacts to the coolant sensor.\n"
        "Keep sensor PLUGGED for the first capture.\n"
    )
    input(f"Press Enter to capture PLUGGED baseline ({seconds:.0f}s)…")
    plugged = capture(bus, seconds)

    print(
        "\n>>> Unplug the coolant sensor now. Wait ~2s for ECM to notice,\n"
        "    then press Enter for the UNPLUGGED capture."
    )
    input()
    unplugged = capture(bus, seconds)

    rows: list[tuple] = []
    ids = set(plugged) | set(unplugged)
    for arb_id in ids:
        if arb_id in SKIP_IDS:
            continue
        a = plugged.get(arb_id)
        b = unplugged.get(arb_id)
        if not a or not b:
            # appeared or vanished
            if a and not b:
                rows.append((999.0, arb_id, -1, 0, "ID vanished when unplugged", a.count, 0, a.last_data, b""))
            elif b and not a:
                rows.append((999.0, arb_id, -1, 0, "ID appeared when unplugged", 0, b.count, b"", b.last_data))
            continue
        max_bi = max(max(a.bytes_, default=-1), max(b.bytes_, default=-1))
        for bi in range(max_bi + 1):
            ta = a.bytes_.get(bi)
            tb = b.bytes_.get(bi)
            if not ta or not tb or ta.n < 5 or tb.n < 5:
                continue
            if looks_like_counter(ta.samples) or looks_like_counter(tb.samples):
                continue
            ma, mb = median(ta.samples), median(tb.samples)
            delta = abs(mb - ma)
            if delta < 3:
                continue
            # Prefer DBC field
            boost = 3.0 if arb_id == ID_ECM_TEMP and bi == BYTE_OIL_TEMP else 1.0
            ca = as_c(ma, 60)
            cb = as_c(mb, 60)
            reason = (
                f"raw {ma:.0f}→{mb:.0f} (Δ{delta:.0f})  "
                f"as°C+60: {ca:.0f}→{cb:.0f}°C"
            )
            rows.append(
                (
                    delta * boost,
                    arb_id,
                    bi,
                    60,
                    reason,
                    a.count,
                    b.count,
                    a.last_data,
                    b.last_data,
                )
            )

    rows.sort(key=lambda r: r[0], reverse=True)
    print("\nBiggest changes after unplug:")
    if not rows:
        print("  Nothing moved. ECM may not be on bus, or sensor isn't on this CAN path.")
        print_dbc_target(plugged)
        print_dbc_target(unplugged)
        return

    print(f"{'#':>3}  {'ID':>6}  {'byte':>4}  {'Δraw':>6}  note")
    for i, (score, arb_id, bi, _, reason, na, nb, da, db) in enumerate(rows[:20], 1):
        byte_s = "—" if bi < 0 else f"{bi:4d}"
        print(f"{i:3d}  0x{arb_id:03X}  {byte_s}  {score:6.1f}  {reason}")
        if i <= 5 and da and db:
            print(f"       plugged:   {da.hex(' ')}")
            print(f"       unplugged: {db.hex(' ')}")

    print("\nDBC check:")
    print_dbc_target(plugged)
    print("  after unplug:")
    # reuse printer with unplugged dict
    print_dbc_target(unplugged)


def load_known_dbc_ids() -> dict[int, str]:
    try:
        return load_dbc_names(default_dbc_path())
    except Exception as exc:
        print(f"warn: could not load hs_bus.dbc ({exc})", file=sys.stderr)
        return {}


def live_unplug_watch(bus, filter_dbc: bool = True) -> None:
    """Stream byte jumps; by default hide IDs already in hs_bus.dbc (keep 0x4D5)."""
    known = load_known_dbc_ids()
    hide = set(known) - KEEP_WHEN_FILTERING if filter_dbc else set()
    hide |= SKIP_IDS

    mode = f"hiding {len(hide)} known DBC IDs (keeping 0x4D5)" if filter_dbc else "showing all"
    print(
        f"LIVE UNPLUG WATCH — {mode}\n"
        "Leave sensor plugged until steady, then UNPLUG.\n"
        "* = jump.  [DBC]=0x4D5 temp.  [NEW]=not in hs_bus.dbc.  Ctrl+C to stop.\n"
    )
    last: dict[tuple[int, int], int] = {}
    hist: dict[tuple[int, int], list[int]] = defaultdict(list)
    seen_new: set[int] = set()
    t0 = time.monotonic()
    last_hb = 0.0
    last_stats = 0.0
    saw_4d5 = False
    frames_known = 0
    frames_new = 0
    try:
        while True:
            try:
                msg = bus.recv(timeout=0.3)
            except (ValueError, OSError, can.CanError) as exc:
                print(f"  bus read error (ignored): {exc}")
                continue
            now = time.monotonic() - t0
            if now - last_stats >= 5.0:
                print(
                    f"  {now:6.1f}s  stats: known_frames={frames_known}  "
                    f"new_frames={frames_new}  new_ids={len(seen_new)}"
                    + ("" if saw_4d5 else "  …no 0x4D5 yet…")
                )
                if seen_new:
                    ids = ", ".join(f"0x{i:03X}" for i in sorted(seen_new)[:12])
                    more = "" if len(seen_new) <= 12 else f" +{len(seen_new)-12} more"
                    print(f"           new IDs: {ids}{more}")
                last_stats = now
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            arb = msg.arbitration_id
            if arb in hide:
                frames_known += 1
                continue
            if arb in known and arb not in KEEP_WHEN_FILTERING:
                frames_known += 1
            else:
                frames_new += 1
                if arb not in known:
                    if arb not in seen_new:
                        print(f"  {now:6.1f}s  NEW ID 0x{arb:03X}  {bytes(msg.data).hex(' ')}")
                    seen_new.add(arb)

            data = bytes(msg.data)
            if arb == ID_ECM_TEMP:
                saw_4d5 = True
            for bi, raw in enumerate(data):
                key = (arb, bi)
                h = hist[key]
                h.append(raw)
                if len(h) > 40:
                    del h[:-40]
                if looks_like_counter(h):
                    continue
                prev = last.get(key)
                last[key] = raw
                is_dbc_temp = arb == ID_ECM_TEMP and bi == BYTE_OIL_TEMP
                is_new = arb not in known
                if prev is None:
                    if is_dbc_temp:
                        c = as_c(raw, 60)
                        print(
                            f"  {now:6.1f}s  0x{arb:03X} b{bi}  raw={raw:3d}  "
                            f"{c:5.1f}°C  {as_f(c):5.1f}°F  [DBC]  {data.hex(' ')}"
                        )
                        last_hb = now
                    continue
                delta = abs(raw - prev)
                if is_dbc_temp and now - last_hb >= 2.0:
                    c = as_c(raw, 60)
                    print(
                        f"  {now:6.1f}s  0x{arb:03X} b{bi}  raw={raw:3d}  "
                        f"{c:5.1f}°C  {as_f(c):5.1f}°F  [DBC]  {data.hex(' ')}"
                    )
                    last_hb = now
                if delta < 8 and not (is_dbc_temp and delta >= 1):
                    continue
                c = as_c(raw, 60)
                tag = " [DBC]" if is_dbc_temp else (" [NEW]" if is_new else "")
                print(
                    f"* {now:6.1f}s  0x{arb:03X} b{bi}  {prev:3d}→{raw:3d} (Δ{delta})  "
                    f"{c:5.1f}°C  {as_f(c):5.1f}°F{tag}  {data.hex(' ')}"
                )
    except KeyboardInterrupt:
        print("\nStopped.")
        if seen_new:
            print("Unknown IDs (not in hs_bus.dbc):")
            for i in sorted(seen_new):
                print(f"  0x{i:03X}")


def main() -> int:
    p = argparse.ArgumentParser(description="Find coolant/engine temp (hs_bus.dbc 0x4D5)")
    p.add_argument("--channel")
    p.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    p.add_argument("--seconds", type=float, default=20.0)
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--watch", action="store_true", help="Watch DBC 0x4D5 byte6 only")
    p.add_argument("--watch-seconds", type=float, default=0.0)
    p.add_argument(
        "--unplug",
        action="store_true",
        help="Two-phase plugged→unplugged diff (best for finding the ID)",
    )
    p.add_argument(
        "--live-unplug",
        action="store_true",
        help="Live stream; hide known hs_bus.dbc IDs; unplug mid-run",
    )
    p.add_argument(
        "--all-ids",
        action="store_true",
        help="With --live-unplug, do not hide known DBC IDs",
    )
    args = p.parse_args()

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    try:
        if args.live_unplug:
            live_unplug_watch(bus, filter_dbc=not args.all_ids)
            return 0
        if args.unplug:
            unplug_diff(bus, min(args.seconds, 12.0))
            return 0
        if args.watch:
            secs = args.watch_seconds if args.watch_seconds > 0 else None
            live_watch(bus, secs)
            return 0

        by_id = capture(bus, args.seconds)
        print_dbc_target(by_id)
        rows = rank(by_id, args.top)
        print_rankings(rows)
        return 0
    finally:
        bus.shutdown()


if __name__ == "__main__":
    sys.exit(main())
