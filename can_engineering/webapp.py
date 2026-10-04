#!/usr/bin/env python3
"""Flask live CAN watch + ECM TX controls (RPM / coolant / oil)."""

from __future__ import annotations

import argparse
import threading
import time

import can
from flask import Flask, jsonify, render_template, request

from can_bus import DEFAULT_BITRATE, open_bus
from can_watch_state import CanWatchState
from dbc_decode import default_dbc_path, load_dbc
from ecm_controls import EcmControls, build_tx_frames

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
STATE = CanWatchState()
CTRL = EcmControls()
DBC = None
BUS = None
BUS_LOCK = threading.Lock()

ID_PADDLES = 0x257
PADDLE_DOWNSHIFT = 225
PADDLE_UPSHIFT = 228


def bus_loop(channel: str | None, bitrate: int) -> None:
    global BUS
    try:
        BUS = open_bus(channel=channel, bitrate=bitrate, receive_own_messages=True)
        STATE.channel = getattr(BUS, "channel_info", "") or str(channel or "")
        STATE.bitrate = bitrate
        STATE.running = True
        STATE.error = None

        next_tx = time.monotonic()
        tx_period = 0.02  # 50 Hz primary cycle
        last_paddle_state = None

        while STATE.running:
            now = time.monotonic()

            if CTRL.sweep:
                CTRL.advance_sweep(now)

            # TX ECM emulation. Sweep runs faster so it beats the ECM's own 0x4D5.
            tx_period = 0.01 if CTRL.sweep else 0.02
            if (CTRL.enabled or CTRL.tx_255_enabled) and now >= next_tx:
                try:
                    frames = build_tx_frames(CTRL)
                    with BUS_LOCK:
                        for arb_id, data in frames:
                            BUS.send(
                                can.Message(
                                    arbitration_id=arb_id,
                                    data=data,
                                    is_extended_id=False,
                                )
                            )
                            STATE.ingest(arb_id, data)
                    with CTRL.lock:
                        CTRL.tx_count += 1
                        CTRL.last_error = None
                except Exception as exc:  # noqa: BLE001
                    with CTRL.lock:
                        CTRL.last_error = str(exc)
                next_tx = now + tx_period

            # RX other traffic
            with BUS_LOCK:
                msg = BUS.recv(timeout=0.01)
            if msg is not None and not msg.is_error_frame and not msg.is_remote_frame:
                data = bytes(msg.data)
                if msg.arbitration_id == ID_PADDLES and len(data) >= 8:
                    paddle_state = data[7]
                    if paddle_state != last_paddle_state:
                        if paddle_state == PADDLE_UPSHIFT:
                            CTRL.adjust_rpm(1000)
                        elif paddle_state == PADDLE_DOWNSHIFT:
                            CTRL.adjust_rpm(-1000)
                    last_paddle_state = paddle_state
                STATE.ingest(msg.arbitration_id, data)

    except Exception as exc:  # noqa: BLE001
        STATE.error = str(exc)
        STATE.running = False
    finally:
        if BUS is not None:
            try:
                BUS.shutdown()
            except Exception:
                pass
            STATE.running = False


@app.get("/")
def index():
    return render_template("watch.html")


@app.get("/api/state")
def api_state():
    snap = STATE.snapshot(DBC)
    snap["controls"] = CTRL.snapshot()
    return jsonify(snap)


@app.post("/api/controls")
def api_controls():
    body = request.get_json(force=True, silent=True) or {}
    CTRL.update(
        **{
            k: body[k]
            for k in (
                "rpm",
                "coolant_f",
                "coolant_raw_255",
                "oil_level",
                "enabled",
                "tx_255_enabled",
                "gauge_byte",
                "gauge_raw",
                "sweep",
            )
            if k in body
        }
    )
    return jsonify(CTRL.snapshot())


def main() -> None:
    global DBC
    parser = argparse.ArgumentParser(description="Flask CAN watch + ECM TX")
    parser.add_argument("--channel")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--dbc", default=str(default_dbc_path()))
    parser.add_argument("--no-tx", action="store_true", help="Listen only")
    args = parser.parse_args()

    if args.no_tx:
        CTRL.enabled = False

    DBC = load_dbc(args.dbc)
    t = threading.Thread(target=bus_loop, args=(args.channel, args.bitrate), daemon=True)
    t.start()
    time.sleep(0.3)
    print(f"Open http://{args.host}:{args.port}/")

    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run(host=args.host, port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
