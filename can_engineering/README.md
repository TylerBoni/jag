# Jaguar F-Type (2015 / X152) — HS-CAN tach (engine out)

Locate / drive the instrument-cluster tach over **HS-CAN** with a **CANable**, when the engine/ECM is **not** in the car.

Without an ECM there is no real RPM traffic to sniff. Discovery is **inject candidate frames and watch the needle**.

## Hardware

| Item | Notes |
|------|--------|
| Interface | CANable (slcan) |
| Bus | HS-CAN @ **500 kbit/s** |
| Tap | OBD-II **6 = CAN-H**, **14 = CAN-L**, or cluster HS pins |
| Cluster | Powered + awake (ignition / keepalives as needed) |

If gauges are dark or frozen, RPM TX alone will not move the tach — wake/power first.

## Setup

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
ls /dev/cu.usbmodem*
export CANABLE_CHANNEL=/dev/cu.usbmodemXXXXXXXX   # optional
```

## Emulate ECM (unplugged)

Replay your captured ECM HS set with rpm “running”:

```bash
# Cluster powered. If bus was silent after unplug, try CANable 120Ω ON.
python emulate_ecm.py --rpm 800 --listen
```

`+`/`-` rpm, `i` = 800, `r` = 3000, `q` quit.  
11 IDs from your watch (`0x295`, `0x4D5`, faults, …). Not a full ZF torque stack — first check tach/warnings. RX ~0 ⇒ wrong tap or no ACK peer.

## Find tach (auto sweep)

```bash
python probe_tach.py
```

Auto-advances layouts (~1.5s each) at 3000 RPM. **SPACE** when the needle moves (also tags the previous layout for reaction lag). **`.`** skip ahead, **`,`** back, **q** quit.

```bash
python probe_tach.py --dwell 1.0 --rpm 4000
python probe_tach.py --list
python probe_tach.py --id 0x295 --offset 6 --rpm 4000
```

## Live gauge UI

```bash
pip install -r requirements.txt
python webapp.py
```

Open http://127.0.0.1:5050/ — live IDs with per-byte bars (DBC names). Uses the CANable exclusively while running.


```bash
python listen.py
python listen.py --stats 5
```

Live table (unique IDs + latest value, updates in place):

```bash
python watch.py
```

Yellow flash = payload just changed. Keys: `i` sort by ID, `r` rate, `c` count, `a` age, `m` recently changed, `q` quit.

`find_tach.py` (idle vs rev diff) needs a **running engine** — skip it until the powertrain is back in.

## Related encodings (unconfirmed for F-Type)

| Source | ID | Layout |
|--------|-----|--------|
| XF facelift | `0x295` | bytes 6–7 BE, `raw & 0x1FFF` |
| XF pre-facelift | `0x099` | bytes 4–5 BE, masked |
| `tach.py` default | `0x0D0` | bytes 4–5 BE, masked |

## Scripts

| File | Role |
|------|------|
| `can_bus.py` | CANable open / auto-detect |
| `probe_tach.py` | Inject layouts, watch needle (**use this**) |
| `tach.py` | Hold one ID/RPM |
| `listen.py` | Dump bus traffic (stream) |
| `watch.py` | Live unique-ID table (latest values) |
| `find_tach.py` | Idle/rev sniffer (engine installed) |

## Safety

TX is required for engine-out probing. Prefer a bench cluster or isolated HS segment. Wrong wake/config traffic can confuse modules — use at your own risk.
