# 2015 Jaguar F-Type — L92 6.2L LS Swap Engineering Manual

> **Status:** Living engineering record, incomplete. Not an approved end-to-end or road-safe conversion procedure.
>
> **Revision:** 0.1.0 · **Baseline:** 2026-11-20

## Scope

2015 Jaguar F-Type base (X152), originally AJ126 3.0L supercharged V6 and ZF 8-speed automatic, converted to GM Gen IV L92 6.2L V8 with GM E38 ECM. Intended to preserve the Jaguar ZF8 and OEM functions where feasible. This manual documents measurements, hardware, reverse engineering, fabrication, calibration, and validation needed for reproducibility.

## Evidence rules

| Tag | Meaning |
| --- | --- |
| **TESTED** | Tested on this project, with exact observed result, setup and limitations; “reported” means source is historical operator account rather than archived raw evidence |
| **INSTALLED** | Physically installed, but not yet validated |
| **RESEARCH** | External reference; link primary source and verify applicability |
| **EXPERIMENTAL** | Working theory or unproven technique; define a falsifiable test |
| **OPEN** | Missing or unresolved information |

A successful bench test is not evidence of road safety. Never infer connector cavities, software versions, wire functions, torque settings, CAN bytes or specifications from engine family or wire color alone.

## Index

- [Evidence ledger](EVIDENCE.md)
- [Parts and costs](PARTS.md)
- [Open issues](ISSUES.md)
- [Changelog](CHANGELOG.md)
- [Engine and packaging](docs/mechanical/engine-and-packaging.md)
- [Electrical interfaces](docs/electrical/interfaces.md)
- [CAN protocol and experiments](docs/can/protocol-and-experiments.md)
- [E38 calibration](docs/ecu/e38-calibration.md)
- [Fabrication](docs/fabrication/fabrication.md)
- [Safety and validation plan](docs/testing/validation-plan.md)

## Existing code in this repository

- [CAN engineering tools](../can_engineering/)
- [STM32 CAN Triple firmware](../CAN_Triple/)
- [Fuel pump controller](../fuel_pump_controller/)

These links point to engineering projects, not necessarily validated in-vehicle production firmware. Record exact git SHA, firmware, wiring and calibration for each reproducible test.

## Known observations — bounded conclusions

1. **TESTED (reported):** Jaguar accelerator pedal functioned with the E38. Dual APP sweep, safety faults, and full harness pin map still OPEN.
2. **TESTED (reported):** Approximately **20 psi** indicated with starter cranking and spark plugs removed. This does **not** prove complete remote filter oil routing, healthy hot oil pressure, or bearing condition.
3. **TESTED (reported):** Grounding an **orange/black wire** enabled some E38 start-related behavior with one transmitted signal. Exact connector/cavity, circuit identity, CAN bytes and interlock logic remain OPEN. **Do not ground unidentified wires.**
4. **TESTED (transmitter log):** A replay sent **56 CAN frames on ID `0x1F1`**, reporting `REPLAY DONE sent=56 drop=0`. This does **not** prove ECM reception or authorization.

## Change workflow

Every significant discovery updates its subsystem file, [EVIDENCE.md](EVIDENCE.md), [ISSUES.md](ISSUES.md) and [CHANGELOG.md](CHANGELOG.md). Store raw logs with timestamp, bitrate, hardware/firmware commit, calibration hash, conditions, observations and pass/fail criteria. Do not upgrade experimental ideas to proven procedures without recorded tests.

## Safety

Powertrain controls must enforce Park/Neutral, brake and starter interlocks, starter crank timeout, engine-running inhibit, throttle plausibility, powertrain torque coordination, fused power feeds, emergency shutoff and fail-off behavior. Validate at power-off and ignition-on before fuel, spark, or road movement. Never drive based on startup alone.
