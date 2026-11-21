# Verification and safety test plan

**No public-road test based only on successful starting.** Move through gates with measured pass/fail, written abort rules and an independent safety observer where appropriate.

| Gate | Required evidence | Stop criteria |
| --- | --- | --- |
| 0. Mechanical inspection | Mount strength, fastener audit, driveline alignment, hot clearances, hoses and heat shields | Structural defect or interference |
| 1. Power OFF | Harness continuity, insulation, fuse sizing, polarity, relay default state, correct CAN termination, fuel line pressure test | Unverified pin or short |
| 2. Ignition ON (no crank) | CAN physical integrity, dual APP curves, brake, independent PRNDL, absence of uncontrolled throttle/starter | Any invalid-state start or throttle action |
| 3. Crank without combustion | Starter enable/abort, timeout, engine-running inhibit, current and voltage, oil pressure | Interlock fault, overcrank, no verified oil-pressure rise |
| 4. First ignition | Fire protection, leaks, wideband, idle, charging, oil pressure, critical DTCs | Fuel/oil leak, pressure loss, runaway or severe misfire |
| 5. Thermal cycle | Cooling purge, fan demands, thermostat operation, oil and coolant temperatures, steering/accessory load | Overheat, belt interference, coolant discharge |
| 6. Controlled low-speed | Brake, ABS/ESC, ZF8 range, torque reduction and safe shifting, emergency shutdown | Unexpected drive torque or invalid range |
| 7. Durability | Hot restart, repeated logs and thermal stability, compliance and independent review | Any reopened critical issue |

## Test record template

```markdown
- Test ID / date / operator / controlled location:
- Vehicle configuration, ECM service/OS/tune hash:
- CAN board, transceiver, firmware SHA and bus bitrate:
- Equipment and calibration dates:
- Safety barriers and prerequisites:
- Procedure and acceptance criteria defined beforehand:
- Actual measured values and raw data paths:
- DTCs and unexpected outcomes:
- Abort condition / response:
- PASS / FAIL / INCONCLUSIVE:
- Follow-up issue and evidence link:
```
