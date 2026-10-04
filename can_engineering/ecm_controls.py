"""Shared ECM TX setpoints + frame builders for webapp / emulator."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


OIL_LEVELS = [
    (0, "Normal"),
    (1, "Low"),
    (2, "Critically low"),
    (3, "High"),
]


# Live F-Type 0x4D5 while the ECM is connected. Byte 6 stays 0x00.
LIVE_4D5 = bytes.fromhex("00 00 ff 00 60 f3 00 00")
SWEEP_HOLD_S = 3.0


@dataclass
class EcmControls:
    rpm: int = 800
    coolant_f: float = 190.0
    coolant_raw_255: int = 0x43
    oil_level: int = 0  # 0=Normal … 3=High
    enabled: bool = False
    tx_255_enabled: bool = False
    gauge_byte: int = 0
    gauge_raw: int = 0
    sweep: bool = False
    _counter: int = 0x31
    _sweep_t0: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)
    tx_count: int = 0
    last_error: str | None = None

    def frame_4d5(self) -> bytes:
        data = bytearray(LIVE_4D5)
        data[self.gauge_byte & 7] = self.gauge_raw & 0xFF
        return bytes(data)

    def snapshot(self) -> dict:
        with self.lock:
            frame = self.frame_4d5()
            return {
                "rpm": self.rpm,
                "coolant_f": round(self.coolant_f, 1),
                "coolant_raw_255": self.coolant_raw_255,
                "oil_level": self.oil_level,
                "oil_level_label": dict(OIL_LEVELS).get(self.oil_level, "?"),
                "oil_levels": [{"value": v, "label": lab} for v, lab in OIL_LEVELS],
                "enabled": self.enabled,
                "tx_255_enabled": self.tx_255_enabled,
                "gauge_byte": self.gauge_byte,
                "gauge_raw": self.gauge_raw,
                "sweep": self.sweep,
                "frame_4d5": frame.hex(" "),
                "tx_count": self.tx_count,
                "last_error": self.last_error,
            }

    def advance_sweep(self, now: float) -> None:
        with self.lock:
            if not self.sweep:
                self._sweep_t0 = 0.0
                return
            if self._sweep_t0 == 0.0:
                self._sweep_t0 = now
            step = int((now - self._sweep_t0) / SWEEP_HOLD_S) % 16
            self.gauge_byte = step // 2
            self.gauge_raw = 0xFF if step % 2 else 0x00

    def update(self, **kwargs) -> None:
        with self.lock:
            if "rpm" in kwargs:
                self.rpm = max(0, min(7000, int(kwargs["rpm"])))
            if "coolant_f" in kwargs:
                self.coolant_f = max(-40.0, min(280.0, float(kwargs["coolant_f"])))
            if "coolant_raw_255" in kwargs:
                self.coolant_raw_255 = max(
                    0, min(255, int(kwargs["coolant_raw_255"]))
                )
            if "oil_level" in kwargs:
                self.oil_level = max(0, min(3, int(kwargs["oil_level"])))
            if "enabled" in kwargs:
                self.enabled = bool(kwargs["enabled"])
            if "tx_255_enabled" in kwargs:
                self.tx_255_enabled = bool(kwargs["tx_255_enabled"])
            if "gauge_byte" in kwargs:
                self.gauge_byte = max(0, min(7, int(kwargs["gauge_byte"])))
                self.sweep = False
            if "gauge_raw" in kwargs:
                self.gauge_raw = max(0, min(255, int(kwargs["gauge_raw"])))
                self.sweep = False
            if "sweep" in kwargs:
                self.sweep = bool(kwargs["sweep"])
                self._sweep_t0 = 0.0

    def adjust_rpm(self, delta: int) -> int:
        with self.lock:
            self.rpm = max(0, min(7000, self.rpm + int(delta)))
            return self.rpm


def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def c_to_temp_byte(temp_f: float, offset: int = 60) -> int:
    """Jaguar temp bytes: raw = °C + offset (usually 60)."""
    c = f_to_c(temp_f)
    return max(0, min(255, int(round(c + offset))))


def patch_rpm(data: bytearray, rpm: int) -> None:
    rpm = max(0, min(int(rpm), 0x1FFF))
    raw = 0x8000 | rpm
    data[6] = (raw >> 8) & 0xFF
    data[7] = raw & 0xFF
    data[5] = (0xFF - data[7]) & 0xFF


def patch_oil_level_3f5(data: bytearray, level: int) -> None:
    level &= 3
    data[1] = (data[1] & ~0xC0) | (level << 6)


def build_tx_frames(ctrl: EcmControls) -> list[tuple[int, bytes]]:
    with ctrl.lock:
        rpm = ctrl.rpm
        coolant_raw_255 = ctrl.coolant_raw_255
        oil_level = ctrl.oil_level
        enabled = ctrl.enabled
        sweep = ctrl.sweep
        d4d5 = bytearray(ctrl.frame_4d5())
        ctrl._counter = (ctrl._counter + 1) & 0xFF
        counter = ctrl._counter

    d295 = bytearray.fromhex("24 00 b0 00 ff ff 80 00")
    d295[1] = counter
    d295[3] = (counter - 0x2D) & 0xFF
    patch_rpm(d295, rpm)

    # Only 0x4D5 during the gauge sweep, so the other ECM frames stay the car's.
    if sweep:
        return [(0x4D5, bytes(d4d5))]

    d3f5 = bytearray.fromhex("00 37 00 00 05 46 00 00")
    patch_oil_level_3f5(d3f5, oil_level)

    d4b5 = bytes(8)
    d355 = bytearray.fromhex("32 00 00 00 00 14 00 00")
    d255 = bytearray.fromhex("00 80 00 00 03 00 03 00")
    d255[5] = coolant_raw_255
    d255[7] = coolant_raw_255

    if not enabled:
        return [(0x255, bytes(d255))]

    others = [
        (0x215, bytes.fromhex("43 43 a3 32 7b 32 03 32")),
        (0x255, bytes(d255)),
        (0x315, bytes.fromhex("00 06 50 78 00 93 ff 00")),
        (0x375, bytes.fromhex("00 00 00 00 53 ff 00 40")),
        (0x4C5, bytes.fromhex("00 00 00 00 90 00 4a 13")),
    ]
    return [
        (0x295, bytes(d295)),
        (0x4D5, bytes(d4d5)),
        (0x355, bytes(d355)),
        (0x3F5, bytes(d3f5)),
        (0x4B5, d4b5),
        *others,
    ]
