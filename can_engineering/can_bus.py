"""Shared CANable / slcan helpers for Jaguar HS-CAN work."""

from __future__ import annotations

import glob
import os
from typing import Optional

import can

DEFAULT_BITRATE = 500_000
DEFAULT_INTERFACE = "slcan"


def list_candidate_channels() -> list[str]:
    """Return likely CANable serial device paths on macOS/Linux."""
    patterns = [
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/cu.usbserial*",
        "/dev/ttyACM*",
        "/dev/ttyUSB*",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(sorted(glob.glob(pattern)))
    # Prefer cu.* over tty.* on macOS (non-blocking open).
    cu = [p for p in found if "/cu." in p]
    tty = [p for p in found if p not in cu]
    return cu + tty


def resolve_channel(channel: Optional[str] = None) -> str:
    if channel:
        if not os.path.exists(channel):
            raise FileNotFoundError(f"CAN channel not found: {channel}")
        return channel

    env = os.environ.get("CANABLE_CHANNEL")
    if env:
        if not os.path.exists(env):
            raise FileNotFoundError(f"CANABLE_CHANNEL not found: {env}")
        return env

    candidates = list_candidate_channels()
    if not candidates:
        raise FileNotFoundError(
            "No CANable serial device found. Plug it in, or pass --channel /dev/cu.usbmodem..."
        )
    if len(candidates) > 1:
        print("Multiple serial devices found; using the first:")
        for i, path in enumerate(candidates):
            mark = " <-" if i == 0 else ""
            print(f"  {path}{mark}")
    return candidates[0]


def open_bus(
    channel: Optional[str] = None,
    bitrate: int = DEFAULT_BITRATE,
    receive_own_messages: bool = False,
) -> can.Bus:
    resolved = resolve_channel(channel)
    print(f"Opening {DEFAULT_INTERFACE} on {resolved} @ {bitrate} bit/s")
    return can.Bus(
        interface=DEFAULT_INTERFACE,
        channel=resolved,
        bitrate=bitrate,
        receive_own_messages=receive_own_messages,
    )
