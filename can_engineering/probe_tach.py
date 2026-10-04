#!/usr/bin/env python3
"""Probe instrument-cluster tach with no engine / ECM on the bus.

Auto-increments candidate layouts while TX'ing a fixed RPM. Press SPACE when
the needle moves. Use on a powered, awake cluster over HS-CAN @ 500 kbit/s.
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator

import can

from can_bus import DEFAULT_BITRATE, open_bus


def pack_be16(rpm: int, offset: int, mask: int = 0xFFFF, dlc: int = 8) -> bytes:
    raw = rpm & mask
    data = bytearray(dlc)
    data[offset] = (raw >> 8) & 0xFF
    data[offset + 1] = raw & 0xFF
    return bytes(data)


def pack_le16(rpm: int, offset: int, mask: int = 0xFFFF, dlc: int = 8) -> bytes:
    raw = rpm & mask
    data = bytearray(dlc)
    data[offset] = raw & 0xFF
    data[offset + 1] = (raw >> 8) & 0xFF
    return bytes(data)


def pack_xf_295(rpm: int) -> bytes:
    """hs_bus.dbc: raw16 = 0x8000|rpm, byte5 = 0xFF - byte7."""
    rpm = max(0, min(rpm, 0x1FFF))
    raw = 0x8000 | rpm
    data = bytearray(8)
    data[6] = (raw >> 8) & 0xFF
    data[7] = raw & 0xFF
    data[5] = (0xFF - data[7]) & 0xFF
    return bytes(data)


@dataclass(frozen=True)
class Layout:
    name: str
    arb_id: int
    encode: Callable[[int], bytes]
    notes: str = ""


LAYOUTS: list[Layout] = [
    Layout("dbc 0x295 8000|rpm +b5", 0x295, pack_xf_295, "hs_bus.dbc (needs 0x4D5)"),
    Layout("xf-fl 0x295 be16@6 &1FFF", 0x295, lambda r: pack_be16(r, 6, 0x1FFF), "plain 13-bit"),
    Layout("xf-pre 0x099 be16@4 &1FFF", 0x099, lambda r: pack_be16(r, 4, 0x1FFF), "XF pre-facelift"),
    Layout("probe 0x0D0 be16@4 &1FFF", 0x0D0, lambda r: pack_be16(r, 4, 0x1FFF), "old probe"),
    Layout("0x080 be16@4", 0x080, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x080 be16@6", 0x080, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x100 be16@4", 0x100, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x100 be16@6", 0x100, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x110 be16@4", 0x110, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x110 be16@6", 0x110, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x120 be16@4", 0x120, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x120 be16@6", 0x120, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x200 be16@4", 0x200, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x200 be16@6", 0x200, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x201 be16@4", 0x201, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x201 be16@6", 0x201, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x204 be16@4", 0x204, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x204 be16@6", 0x204, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x210 be16@4", 0x210, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x210 be16@6", 0x210, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x290 be16@4", 0x290, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x290 be16@6", 0x290, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x294 be16@4", 0x294, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x294 be16@6", 0x294, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x300 be16@4", 0x300, lambda r: pack_be16(r, 4, 0x1FFF)),
    Layout("0x300 be16@6", 0x300, lambda r: pack_be16(r, 6, 0x1FFF)),
    Layout("0x295 le16@6", 0x295, lambda r: pack_le16(r, 6, 0x1FFF)),
    Layout("0x295 be16@4", 0x295, lambda r: pack_be16(r, 4, 0x1FFF)),
]


@contextmanager
def raw_stdin() -> Iterator[None]:
    if not sys.stdin.isatty():
        yield
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_keys() -> str:
    """Drain pending stdin bytes; return concatenated string (may be empty)."""
    chars: list[str] = []
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            break
        ch = sys.stdin.read(1)
        if not ch:
            break
        chars.append(ch)
    return "".join(chars)


def make_msg(layout: Layout, rpm: int) -> can.Message:
    return can.Message(
        arbitration_id=layout.arb_id,
        data=layout.encode(rpm),
        is_extended_id=False,
    )


# hs_bus.dbc: 0x4D5 ECM presence required for 0x295 RPM trust
ID_ECM = 0x4D5
ECM_4D5_PAYLOAD = bytes.fromhex("02 A7 24 0C 60 F4 92 28")


class EcmCompanion:
    def __init__(self, bus: can.Bus, hz: float = 10.0, enabled: bool = True):
        self.bus = bus
        self.period = 1.0 / hz if hz > 0 else 0.0
        self.enabled = enabled
        self._next = 0.0

    def tick(self) -> None:
        if not self.enabled or self.period <= 0:
            return
        now = time.monotonic()
        if now < self._next:
            return
        self.bus.send(
            can.Message(arbitration_id=ID_ECM, data=ECM_4D5_PAYLOAD, is_extended_id=False)
        )
        self._next = now + self.period


def auto_sweep(
    bus: can.Bus,
    layouts: list[Layout],
    rpm: int,
    dwell: float,
    hz: float,
    lag_slots: int,
    ecm: EcmCompanion,
) -> list[Layout]:
    """Advance layouts automatically; SPACE marks a hit (includes prior slots for lag)."""
    period = 1.0 / hz
    hits: list[Layout] = []
    seen: set[int] = set()  # layout indices already recorded

    print(
        f"\nAuto-sweep @ {rpm} RPM, {dwell:.1f}s per layout, {hz:.0f} Hz TX\n"
        f"  Also TX 0x4D5 ECM presence @ ~10 Hz (hs_bus.dbc requirement for 0x295)\n"
        f"  SPACE  = tach moved (tags current + previous {lag_slots} for reaction lag)\n"
        f"  .      = skip to next immediately\n"
        f"  ,      = go back one\n"
        f"  q      = quit\n"
    )

    idx = 0
    layout = layouts[idx]
    msg = make_msg(layout, rpm)
    slot_until = time.monotonic() + dwell
    print(f"[{idx + 1}/{len(layouts)}] {layout.name}  0x{layout.arb_id:03X}  {msg.data.hex(' ')}")

    with raw_stdin():
        while idx < len(layouts):
            bus.send(msg)
            ecm.tick()
            keys = read_keys()
            now = time.monotonic()

            if "q" in keys or "\x03" in keys:
                print("\nQuit.")
                break

            if " " in keys:
                # Reaction lag: needle may have moved on an earlier slot
                start = max(0, idx - lag_slots)
                window = list(range(start, idx + 1))
                print("\n*** SPACE — possible hit window ***")
                for wi in window:
                    L = layouts[wi]
                    mark = " <- current" if wi == idx else ""
                    print(f"  [{wi + 1}] 0x{L.arb_id:03X}  {L.name}{mark}")
                    if wi not in seen:
                        hits.append(L)
                        seen.add(wi)

                # Hold current so you can verify; SPACE resumes, q quits
                print(
                    f"\nHolding [{idx + 1}] 0x{layout.arb_id:03X} @ {rpm} — "
                    "SPACE=resume sweep, q=quit"
                )
                while True:
                    bus.send(msg)
                    ecm.tick()
                    k2 = read_keys()
                    if "q" in k2 or "\x03" in k2:
                        print("\nQuit.")
                        return hits
                    if " " in k2:
                        print("Resuming sweep…")
                        slot_until = time.monotonic() + dwell
                        break
                    time.sleep(period)
                continue

            if "," in keys and idx > 0:
                idx -= 1
                layout = layouts[idx]
                msg = make_msg(layout, rpm)
                slot_until = now + dwell
                print(
                    f"[{idx + 1}/{len(layouts)}] {layout.name}  "
                    f"0x{layout.arb_id:03X}  {msg.data.hex(' ')}"
                )
                time.sleep(period)
                continue

            if "." in keys or now >= slot_until:
                idx += 1
                if idx >= len(layouts):
                    print("\nFinished all layouts.")
                    break
                layout = layouts[idx]
                msg = make_msg(layout, rpm)
                slot_until = now + dwell
                print(
                    f"[{idx + 1}/{len(layouts)}] {layout.name}  "
                    f"0x{layout.arb_id:03X}  {msg.data.hex(' ')}"
                )

            time.sleep(period)

    return hits


def hold_layout(bus: can.Bus, layout: Layout, rpm: int, hz: float, ecm: EcmCompanion) -> None:
    period = 1.0 / hz
    msg = make_msg(layout, rpm)
    print(f"Holding {layout.name} rpm={rpm}  data={msg.data.hex(' ')} — Ctrl+C stop")
    try:
        while True:
            bus.send(msg)
            ecm.tick()
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nStopped.")


def parse_layout_filter(text: str | None) -> list[Layout]:
    if not text:
        return list(LAYOUTS)
    ids = {int(p.strip(), 0) for p in text.split(",") if p.strip()}
    return [L for L in LAYOUTS if L.arb_id in ids]


def list_layouts() -> None:
    for i, L in enumerate(LAYOUTS, 1):
        note = f" — {L.notes}" if L.notes else ""
        print(f"{i:3d}  0x{L.arb_id:03X}  {L.name}{note}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-increment tach probes; SPACE when needle moves"
    )
    parser.add_argument("--channel")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument("--hz", type=float, default=50.0, help="TX rate")
    parser.add_argument("--rpm", type=int, default=3000, help="Injected RPM during sweep")
    parser.add_argument(
        "--dwell",
        type=float,
        default=1.5,
        help="Seconds per layout before auto-advance (default 1.5)",
    )
    parser.add_argument(
        "--lag",
        type=int,
        default=1,
        help="On SPACE, also tag this many previous layouts (reaction lag)",
    )
    parser.add_argument("--ids", help="Only probe these arbitration IDs")
    parser.add_argument("--list", action="store_true", help="List layouts and exit")
    parser.add_argument("--hold-layout", metavar="N", type=int, help="Hold --rpm on layout index")
    parser.add_argument("--id", type=lambda s: int(s, 0), help="Custom ID hold (with --offset)")
    parser.add_argument("--offset", type=int, default=4, help="Byte offset for custom --id")
    parser.add_argument("--le", action="store_true", help="Little-endian for custom --id")
    parser.add_argument("--mask", type=lambda s: int(s, 0), default=0x1FFF)
    parser.add_argument("--no-4d5", action="store_true", help="Do not TX companion 0x4D5")
    args = parser.parse_args()

    if args.list:
        list_layouts()
        return 0

    layouts = parse_layout_filter(args.ids)

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    ecm = EcmCompanion(bus, enabled=not args.no_4d5)
    try:
        if args.hold_layout is not None:
            hold_layout(bus, LAYOUTS[args.hold_layout - 1], args.rpm, args.hz, ecm)
            return 0

        if args.id is not None:
            enc = (
                (lambda r: pack_le16(r, args.offset, args.mask))
                if args.le
                else (lambda r: pack_be16(r, args.offset, args.mask))
            )
            endian = "le" if args.le else "be"
            layout = Layout(
                f"custom 0x{args.id:03X} {endian}16@{args.offset}",
                args.id,
                enc,
                "CLI custom",
            )
            hold_layout(bus, layout, args.rpm, args.hz, ecm)
            return 0

        hits = auto_sweep(bus, layouts, args.rpm, args.dwell, args.hz, args.lag, ecm)
        print("\n=== Hits ===")
        if not hits:
            print("None marked. Try longer --dwell, or cluster may need wake/keepalive.")
        else:
            for L in hits:
                print(f"  0x{L.arb_id:03X}  {L.name}")
            print(f"\n  python tach.py --rpm {args.rpm}")
            if hits[-1] in LAYOUTS:
                print(f"  python probe_tach.py --hold-layout {LAYOUTS.index(hits[-1]) + 1} --rpm {args.rpm}")
        return 0
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    finally:
        bus.shutdown()


if __name__ == "__main__":
    sys.exit(main())
