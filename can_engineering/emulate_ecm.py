#!/usr/bin/env python3
"""Emulate disconnected Jag ECM on HS-CAN from a live capture baseline.

Replays the ECM-side IDs you saw in watch.py, with RPM > 0 so the car
looks "running". Requires another node on the bus to ACK (cluster powered)
and usually the CANable 120Ω if the ECM was providing termination.

This is NOT a complete TCM torque handshake — it's the ECM broadcast set
from your tap. Good first test for cluster/warnings; ZF may need more.
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass, field

import can

from can_bus import open_bus

# Baselines from your F-Type watch (ECM connected, engine out / rpm=0).
# Rates are approximate from that capture.


@dataclass
class TxFrame:
    arb_id: int
    name: str
    data: bytearray
    period: float  # seconds
    next_due: float = 0.0
    count: int = 0


def patch_rpm(data: bytearray, rpm: int) -> None:
    rpm = max(0, min(int(rpm), 0x1FFF))
    raw = 0x8000 | rpm
    data[6] = (raw >> 8) & 0xFF
    data[7] = raw & 0xFF
    data[5] = (0xFF - data[7]) & 0xFF


def tick_295_counters(data: bytearray) -> None:
    """Your capture: byte1 rolls; byte3 ≈ byte1 - 0x2D."""
    b1 = (data[1] + 1) & 0xFF
    data[1] = b1
    data[3] = (b1 - 0x2D) & 0xFF


def build_schedule(rpm: int) -> list[TxFrame]:
    # period = 1/Hz from your ~watch rates
    frames = [
        TxFrame(0x215, "ChargingSystemFault", bytearray.fromhex("43 43 a3 32 7b 32 03 32"), 1 / 66),
        TxFrame(0x255, "0x255", bytearray.fromhex("00 80 00 00 03 43 03 43"), 1 / 66),
        TxFrame(0x295, "ECM_RPM", bytearray.fromhex("24 31 b0 04 ff ff 80 00"), 1 / 50),
        TxFrame(0x2B5, "ThrottlePosition", bytearray.fromhex("c8 00 02 00 24 00 00 00"), 1 / 50),
        TxFrame(0x315, "AirTemperature", bytearray.fromhex("00 06 50 78 00 93 ff 00"), 1 / 50),
        TxFrame(0x355, "EngTempWarn", bytearray.fromhex("32 00 00 00 00 14 00 00"), 1 / 20),
        TxFrame(0x375, "0x375", bytearray.fromhex("00 00 00 00 53 ff 00 40"), 1 / 66),
        TxFrame(0x3F5, "ECM_Faults", bytearray.fromhex("00 37 00 00 05 46 00 04"), 1 / 5),
        TxFrame(0x4B5, "ASL_Faults", bytearray.fromhex("01 00 00 00 00 00 00 00"), 1 / 10),
        TxFrame(0x4C5, "0x4C5", bytearray.fromhex("00 00 00 00 90 00 4a 13"), 1 / 20),
        TxFrame(0x4D5, "ECM_ETM_Status", bytearray.fromhex("00 00 ff 00 60 f3 00 00"), 1 / 20),
    ]
    for f in frames:
        if f.arb_id == 0x295:
            patch_rpm(f.data, rpm)
    return frames


def keys_pending() -> str:
    out: list[str] = []
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            break
        ch = sys.stdin.read(1)
        if ch:
            out.append(ch)
    return "".join(out)


CSI = "\033["
HIDE, SHOW = f"{CSI}?25l", f"{CSI}?25h"
HOME, CLEAR, CLEAR_EOL = f"{CSI}H", f"{CSI}2J", f"{CSI}K"
BOLD, DIM, GREEN, YELLOW, RED, RESET = (
    f"{CSI}1m",
    f"{CSI}2m",
    f"{CSI}32m",
    f"{CSI}33m",
    f"{CSI}31m",
    f"{CSI}0m",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emulate ECM HS-CAN broadcasts")
    parser.add_argument("--channel")
    parser.add_argument("--rpm", type=int, default=800, help="Default idle-ish (use >375)")
    parser.add_argument("--listen", action="store_true", help="Also count RX (bus alive check)")
    args = parser.parse_args()

    rpm = args.rpm
    frames = build_schedule(rpm)
    bus = open_bus(channel=args.channel, receive_own_messages=True)

    now = time.monotonic()
    for f in frames:
        f.next_due = now

    rx_n = 0
    win_rx = win_tx = 0
    win_start = now
    rx_hz = tx_hz = 0.0
    last_draw = 0.0
    err_n = 0

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd) if sys.stdin.isatty() else None
    sys.stdout.write(CLEAR + HIDE)
    sys.stdout.flush()

    try:
        if old is not None:
            tty.setcbreak(fd)

        while True:
            now = time.monotonic()

            for f in frames:
                if now < f.next_due:
                    continue
                if f.arb_id == 0x295:
                    tick_295_counters(f.data)
                    patch_rpm(f.data, rpm)
                try:
                    bus.send(
                        can.Message(
                            arbitration_id=f.arb_id,
                            data=bytes(f.data),
                            is_extended_id=False,
                        )
                    )
                    f.count += 1
                    win_tx += 1
                except can.CanError:
                    err_n += 1
                f.next_due = now + f.period

            if args.listen:
                msg = bus.recv(timeout=0.0)
                while msg is not None:
                    if msg.is_error_frame:
                        err_n += 1
                    elif not msg.is_remote_frame:
                        rx_n += 1
                        win_rx += 1
                    msg = bus.recv(timeout=0.0)

            if now - win_start >= 1.0:
                elapsed = now - win_start
                rx_hz = win_rx / elapsed
                tx_hz = win_tx / elapsed
                win_rx = win_tx = 0
                win_start = now

            if sys.stdin.isatty():
                keys = keys_pending()
                if "q" in keys or "\x03" in keys:
                    break
                if "0" in keys:
                    rpm = 0
                if any(k in keys for k in ("+", "=", "k")):
                    rpm = min(7000, rpm + 100)
                if any(k in keys for k in ("-", "_", "j")):
                    rpm = max(0, rpm - 100)
                if "i" in keys:
                    rpm = 800
                if "r" in keys:
                    rpm = 3000

            if now - last_draw >= 0.2:
                alive = (
                    f"{GREEN}RX ~{rx_hz:.0f} Hz (bus has peers){RESET}"
                    if rx_hz > 1
                    else f"{RED}little/no RX — need cluster on bus + maybe 120Ω{RESET}"
                )
                rpm_f = next(f for f in frames if f.arb_id == 0x295)
                lines = [
                    f"{BOLD}ECM emulator{RESET}  rpm={rpm}  TX ~{tx_hz:.0f} Hz  errs={err_n}  {alive}",
                    f"  0x295 {bytes(rpm_f.data).hex(' ')}",
                    f"{DIM}  [+/k] +100 rpm  [-/j] -100  [i]idle800  [r]3000  [0]zero  [q]quit{RESET}",
                    f"{YELLOW}  Emulates your captured ECM set only — ZF may need more frames.{RESET}",
                    "",
                    f"{DIM}  {'ID':>5}  {'name':<22}  {'n':>8}  Hz{RESET}",
                ]
                for f in frames:
                    hz = 1.0 / f.period
                    lines.append(
                        f"  0x{f.arb_id:03X}  {f.name:<22}  {f.count:8d}  {hz:4.0f}"
                    )
                lines.append(CLEAR_EOL)
                sys.stdout.write(HOME + "\n".join(l + CLEAR_EOL for l in lines))
                sys.stdout.flush()
                last_draw = now

            time.sleep(0.0005)

    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(SHOW + "\n")
        sys.stdout.flush()
        bus.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
