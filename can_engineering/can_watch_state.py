"""Thread-safe live CAN frame table for watch UI / Flask."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdState:
    count: int = 0
    data: bytes = b""
    last_ts: float = 0.0
    changed_at: float = 0.0
    window_count: int = 0


@dataclass
class CanWatchState:
    ids: dict[int, IdState] = field(default_factory=dict)
    total: int = 0
    window_start: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)
    error: str | None = None
    channel: str = ""
    bitrate: int = 0
    running: bool = False

    def ingest(self, arb_id: int, data: bytes) -> None:
        now = time.monotonic()
        with self.lock:
            st = self.ids.get(arb_id)
            if st is None:
                st = IdState()
                self.ids[arb_id] = st
            if data != st.data:
                st.changed_at = now
            st.data = data
            st.count += 1
            st.window_count += 1
            st.last_ts = now
            self.total += 1
            if now - self.window_start >= 1.0:
                for s in self.ids.values():
                    s.window_count = 0
                self.window_start = now

    def snapshot(self, dbc: Any) -> dict:
        now = time.monotonic()
        titles = dbc.titles() if dbc is not None else {}
        with self.lock:
            elapsed = max(now - self.window_start, 1e-6)
            rows = []
            for arb_id, st in sorted(self.ids.items()):
                age = now - st.last_ts
                hz = st.window_count / elapsed
                fresh = (now - st.changed_at) < 0.8
                signals = dbc.decode(arb_id, st.data) if dbc is not None else []
                title = titles.get(arb_id, f"Message 0x{arb_id:03X}")
                row = {
                    "id": arb_id,
                    "id_hex": f"0x{arb_id:03X}",
                    "name": title,
                    "data": list(st.data),
                    "count": st.count,
                    "hz": round(hz, 1),
                    "age": round(age, 2),
                    "fresh": fresh,
                    "signals": signals,
                    "has_decode": bool(signals),
                }
                for sig in signals:
                    if "rpm" in sig["label"].lower() and sig.get("phys") is not None:
                        row["rpm"] = int(round(sig["phys"]))
                        break
                rows.append(row)
            rx_4d5 = None
            for row in rows:
                if row["id"] == 0x4D5:
                    rx_4d5 = row["data"]
                    break
            return {
                "ok": self.error is None,
                "error": self.error,
                "channel": self.channel,
                "bitrate": self.bitrate,
                "running": self.running,
                "total": self.total,
                "id_count": len(rows),
                "rows": rows,
                "rx_4d5": rx_4d5,
                "ts": time.time(),
            }
