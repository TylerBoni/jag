"""Drive tach with ECM disconnected: TX 0x295 + 0x4D5 @ fixed rates.

Use when watch.py shows little/no traffic (ECM unplugged).
If watch still shows 0 IDs while this runs, your CANable is alone on the
wire (no ACK) — cluster is not on this tap. Move to cluster HS pins.

The 0x257 paddle-shifter state adjusts the commanded RPM by 1,000 RPM
per press: upshift raises it and downshift lowers it.
"""

from __future__ import annotations

import argparse
import select
import sys
import termios
import time
import tty

import can

from can_bus import open_bus

ID_RPM = 0x295
ID_ECM = 0x4D5
ID_PADDLES = 0x257

PADDLE_OPEN = 224
PADDLE_DOWNSHIFT = 225
PADDLE_UPSHIFT = 228
PADDLE_BOTH = 229
PADDLE_NAMES = {
    PADDLE_OPEN: "open",
    PADDLE_DOWNSHIFT: "downshift",
    PADDLE_UPSHIFT: "upshift",
    PADDLE_BOTH: "both",
}

# Last live ECM-shaped frame from your car (rpm field will be patched)
DEFAULT_TEMPLATE = bytes.fromhex("24 3e b0 11 ff ff 80 00")
# Your live 0x4D5 while ECM was connected
ECM_4D5 = bytes.fromhex("00 00 ff 00 60 f3 00 00")

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


def patch_rpm(template: bytes, rpm: int) -> bytes:
    data = bytearray(template.ljust(8, b"\x00")[:8])
    rpm = max(0, min(int(rpm), 0x1FFF))
    raw = 0x8000 | rpm
    data[6] = (raw >> 8) & 0xFF
    data[7] = raw & 0xFF
    data[5] = (0xFF - data[7]) & 0xFF
    return bytes(data)


def decode_rpm(data: bytes) -> int:
    return ((data[6] << 8) | data[7]) & 0x1FFF if len(data) >= 8 else -1


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


def main() -> None:
    parser = argparse.ArgumentParser(description="TX RPM with ECM gone")
    parser.add_argument("--channel")
    parser.add_argument("--rpm", type=int, default=3000)
    parser.add_argument("--hz", type=float, default=50.0)
    parser.add_argument("--ecm-hz", type=float, default=20.0)
    parser.add_argument("--template", default=DEFAULT_TEMPLATE.hex(" "))
    parser.add_argument("--term-hint", action="store_true", help="Print terminator reminder")
    args = parser.parse_args()

    template = bytes.fromhex(args.template.replace(" ", ""))
    rpm = args.rpm
    bus = open_bus(channel=args.channel, receive_own_messages=True)

    period = 1.0 / args.hz
    ecm_period = 1.0 / args.ecm_hz
    next_rpm = next_ecm = time.monotonic()
    tx_295 = tx_4d5 = rx_any = 0
    win_rx = 0
    win_start = time.monotonic()
    rx_hz = 0.0
    last_rx_id = None
    last_paddle_state = None
    last_draw = 0.0

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd) if sys.stdin.isatty() else None
    sys.stdout.write(CLEAR + HIDE)
    sys.stdout.flush()

    try:
        if old is not None:
            tty.setcbreak(fd)

        while True:
            now = time.monotonic()
            data295 = patch_rpm(template, rpm)

            if now >= next_rpm:
                bus.send(
                    can.Message(arbitration_id=ID_RPM, data=data295, is_extended_id=False)
                )
                tx_295 += 1
                next_rpm = now + period

            if now >= next_ecm:
                bus.send(
                    can.Message(arbitration_id=ID_ECM, data=ECM_4D5, is_extended_id=False)
                )
                tx_4d5 += 1
                next_ecm = now + ecm_period

            msg = bus.recv(timeout=0.0)
            while msg is not None:
                if not msg.is_error_frame and not msg.is_remote_frame:
                    rx_any += 1
                    win_rx += 1
                    last_rx_id = msg.arbitration_id
                    if msg.arbitration_id == ID_PADDLES and len(msg.data) >= 8:
                        paddle_state = msg.data[7]
                        if paddle_state != last_paddle_state:
                            if paddle_state == PADDLE_UPSHIFT:
                                rpm = min(7000, rpm + 1000)
                            elif paddle_state == PADDLE_DOWNSHIFT:
                                rpm = max(0, rpm - 1000)
                        last_paddle_state = paddle_state
                msg = bus.recv(timeout=0.0)

            if now - win_start >= 1.0:
                rx_hz = win_rx / (now - win_start)
                win_rx = 0
                win_start = now

            if sys.stdin.isatty():
                keys = keys_pending()
                if "q" in keys or "\x03" in keys:
                    break
                if "0" in keys:
                    rpm = 0
                if any(k in keys for k in ("+", "=", "k")):
                    rpm = min(7000, rpm + 500)
                if any(k in keys for k in ("-", "_", "j")):
                    rpm = max(0, rpm - 500)

            if now - last_draw >= 0.15:
                if rx_hz < 1:
                    bus_status = (
                        f"{RED}bus silent (0 Hz RX) — no other node ACK / wrong tap / need 120Ω{RESET}"
                    )
                else:
                    bus_status = f"{GREEN}bus alive ~{rx_hz:.0f} Hz RX{RESET}"
                lines = [
                    f"{BOLD}tach (ECM out){RESET}  rpm={rpm}  {bus_status}",
                    f"  TX 0x295 @ {args.hz:.0f} Hz  n={tx_295}  {data295.hex(' ')}  (dec {decode_rpm(data295)})",
                    f"  TX 0x4D5 @ {args.ecm_hz:.0f} Hz  n={tx_4d5}  {ECM_4D5.hex(' ')}",
                    f"  RX frames n={rx_any}  last_id="
                    + (f"0x{last_rx_id:03X}" if last_rx_id is not None else "—"),
                    "  paddles="
                    + (
                        PADDLE_NAMES.get(last_paddle_state, f"unknown ({last_paddle_state})")
                        if last_paddle_state is not None
                        else "not seen"
                    )
                    + "  [upshift +1000 / downshift -1000]",
                    f"{DIM}  [+/k] +500  [-/j] -500  [0]  [q]{RESET}",
                    f"{YELLOW}  Your earlier watch had ONLY ECM-side IDs (no cluster 0x217/0x257).{RESET}",
                    f"{YELLOW}  If bus stays silent or needle dead: tap cluster HS, not ECM stub.{RESET}",
                    CLEAR_EOL,
                ]
                sys.stdout.write(HOME + "\n".join(l + CLEAR_EOL for l in lines))
                sys.stdout.flush()
                last_draw = now

            time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(SHOW + "\n")
        sys.stdout.flush()
        bus.shutdown()


if __name__ == "__main__":
    main()
