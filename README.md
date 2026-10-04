# jag

Automotive reverse-engineering and control work for a **Jaguar F-Type (2015 / X152)**, focused on CAN, cluster emulation, and fuel-system bench hardware.

## Projects

| Path | What it is |
|------|------------|
| [`can_engineering/`](can_engineering/) | Python tools for HS-CAN: ECM emulation, tach probing, bus watch/listen, DBC decode, and a small Flask UI (CANable / slcan) |
| [`CAN_Triple/`](CAN_Triple/) | [CAN Triple](CAN_Triple/README.md) firmware (PlatformIO / STM32) for bridging three CAN 2.0 buses — vendor examples plus `MyProject` |
| [`fuel_pump_controller/`](fuel_pump_controller/) | Arduino Nano bench firmware and wiring for Jaguar fuel pressure / FPDM PWM control |

## Quick start

**CAN tools**

```bash
cd can_engineering
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

See [`can_engineering/README.md`](can_engineering/README.md) for CANable setup, `emulate_ecm.py`, `probe_tach.py`, and `webapp.py`.

**CAN Triple**

Install VS Code + PlatformIO, then open `CAN_Triple/MyProject` (or an example under `CAN_Triple/Examples/`). Details: [`CAN_Triple/README.md`](CAN_Triple/README.md).

**Fuel pump controller**

Flash `fuel_pump_controller/fuel_pump_controller_arduino/` to a Nano. Wiring: [`fuel_pump_controller/SCHEMATIC.md`](fuel_pump_controller/SCHEMATIC.md).

## Notes

- Large capture video and installer binaries are gitignored; keep analysis CSVs/DBCs/docs in-tree.
- TX on vehicle buses can wake or confuse modules — prefer a bench cluster or isolated segment when probing.
