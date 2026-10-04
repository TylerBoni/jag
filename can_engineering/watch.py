#!/usr/bin/env python3
"""Live CAN ID table: unique IDs with latest payload (not a scroll stream)."""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from pathlib import Path

from can_bus import DEFAULT_BITRATE, open_bus
from dbc_names import default_dbc_path, load_dbc_names

CSI = "\033["
HIDE_CURSOR = f"{CSI}?25l"
SHOW_CURSOR = f"{CSI}?25h"
HOME = f"{CSI}H"
CLEAR = f"{CSI}2J"
CLEAR_EOL = f"{CSI}K"
BOLD = f"{CSI}1m"
DIM = f"{CSI}2m"
YELLOW = f"{CSI}33m"
RESET = f"{CSI}0m"

NAME_WIDTH = 28


@dataclass
class IdState:
    count: int = 0
    data: bytes = b""
    dlc: int = 0
    last_ts: float = 0.0
    changed_at: float = 0.0
    window_count: int = 0


@dataclass
class Table:
    ids: dict[int, IdState] = field(default_factory=dict)
    window_start: float = field(default_factory=time.monotonic)
    total: int = 0


def raw_keys_pending() -> str:
    out: list[str] = []
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            break
        ch = sys.stdin.read(1)
        if not ch:
            break
        out.append(ch)
    return "".join(out)


def id_label(arb_id: int, names: dict[int, str]) -> str:
    name = names.get(arb_id, "?")
    if len(name) > NAME_WIDTH:
        name = name[: NAME_WIDTH - 1] + "…"
    return f"{name:<{NAME_WIDTH}}"


def render(
    table: Table, sort: str, flash_s: float, max_rows: int, names: dict[int, str]
) -> str:
    now = time.monotonic()
    elapsed = max(now - table.window_start, 1e-6)
    rows = list(table.ids.items())

    if sort == "id":
        rows.sort(key=lambda kv: kv[0])
    elif sort == "rate":
        rows.sort(key=lambda kv: kv[1].window_count / elapsed, reverse=True)
    elif sort == "count":
        rows.sort(key=lambda kv: kv[1].count, reverse=True)
    elif sort == "age":
        rows.sort(key=lambda kv: kv[1].last_ts, reverse=True)
    else:
        rows.sort(key=lambda kv: kv[1].changed_at, reverse=True)

    total_hz = sum(s.window_count for _, s in rows) / elapsed
    known = sum(1 for i, _ in rows if i in names)
    lines = [
        f"{BOLD}CAN live watch{RESET}  "
        f"{len(rows)} IDs ({known} named)  {table.total} frames  ~{total_hz:.0f} Hz  "
        f"sort={sort}  {DIM}[i]id [r]rate [c]count [a]age [m]changed  [q]quit{RESET}",
        f"{DIM}{'ID':>6}  {'name':<{NAME_WIDTH}}  {'n':>7}  {'Hz':>6}  {'age':>5}  data{RESET}",
    ]

    for arb_id, st in rows[:max_rows]:
        age = now - st.last_ts
        hz = st.window_count / elapsed
        age_s = f"{age:4.1f}s" if age < 99 else "  old"
        hexdata = st.data.hex(" ")
        fresh = (now - st.changed_at) < flash_s
        color = YELLOW if fresh else ""
        lines.append(
            f"{color}0x{arb_id:03X}  {id_label(arb_id, names)}  "
            f"{st.count:7d}  {hz:6.1f}  {age_s}  {hexdata}{RESET}"
        )

    if len(rows) > max_rows:
        lines.append(f"{DIM}… {len(rows) - max_rows} more{RESET}")

    lines.extend([CLEAR_EOL] * 3)
    return HOME + "\n".join(line + CLEAR_EOL for line in lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live unique CAN ID table")
    parser.add_argument("--channel")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument(
        "--sort", choices=("id", "rate", "count", "age", "changed"), default="id"
    )
    parser.add_argument("--flash", type=float, default=0.8)
    parser.add_argument("--refresh", type=float, default=0.1)
    parser.add_argument("--max-rows", type=int, default=40)
    parser.add_argument("--ids", help="Only track these IDs, e.g. 0x295,0x4D5")
    parser.add_argument(
        "--dbc",
        type=Path,
        default=default_dbc_path(),
        help="DBC for ID names (default: hs_bus.dbc)",
    )
    args = parser.parse_args()

    names: dict[int, str] = {}
    if args.dbc.is_file():
        names = load_dbc_names(args.dbc)
    else:
        print(f"No DBC at {args.dbc} — IDs will show as ?", file=sys.stderr)

    allow = None
    if args.ids:
        allow = {int(p.strip(), 0) for p in args.ids.split(",") if p.strip()}

    bus = open_bus(channel=args.channel, bitrate=args.bitrate)
    table = Table()
    sort = args.sort
    last_draw = 0.0
    fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(fd) if sys.stdin.isatty() else None

    sys.stdout.write(CLEAR + HIDE_CURSOR)
    sys.stdout.flush()

    try:
        if old_term is not None:
            tty.setcbreak(fd)

        while True:
            msg = bus.recv(timeout=0.05)
            now = time.monotonic()

            if msg is not None and not msg.is_error_frame and not msg.is_remote_frame:
                if allow is None or msg.arbitration_id in allow:
                    data = bytes(msg.data)
                    st = table.ids.get(msg.arbitration_id)
                    if st is None:
                        st = IdState()
                        table.ids[msg.arbitration_id] = st
                    if data != st.data:
                        st.changed_at = now
                    st.data = data
                    st.dlc = msg.dlc
                    st.count += 1
                    st.window_count += 1
                    st.last_ts = now
                    table.total += 1

            if now - table.window_start >= 1.0:
                for st in table.ids.values():
                    st.window_count = 0
                table.window_start = now

            if sys.stdin.isatty():
                keys = raw_keys_pending()
                if "q" in keys or "\x03" in keys:
                    break
                if "i" in keys:
                    sort = "id"
                if "r" in keys:
                    sort = "rate"
                if "c" in keys:
                    sort = "count"
                if "a" in keys:
                    sort = "age"
                if "m" in keys:
                    sort = "changed"

            if now - last_draw >= args.refresh:
                sys.stdout.write(render(table, sort, args.flash, args.max_rows, names))
                sys.stdout.flush()
                last_draw = now

    except KeyboardInterrupt:
        pass
    finally:
        if old_term is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
        sys.stdout.write(SHOW_CURSOR + "\n")
        sys.stdout.flush()
        bus.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
