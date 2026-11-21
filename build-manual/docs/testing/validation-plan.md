# Testing

These are the checks I want completed as the build progresses. A test passing on the bench isn't the same as the entire vehicle being ready to drive.

| Stage | Check |
| --- | --- |
| Mechanical | Mounts, driveline alignment, clearance, hoses and fasteners |
| Wiring | Polarity, grounds, fuses, insulation, relay states and CAN termination |
| Ignition on | Pedal signals, brake signal, Park/Neutral and starter inhibit |
| Cranking | Oil pressure, starter timeout, engine-running inhibit |
| First start | Fuel and oil leaks, AFR, ignition, charging, ECU faults |
| Warm-up | Cooling system, fan control, steering pressure and belt clearance |
| Low-speed test | Brakes, ABS/ESC, ZF8 range and shift/torque control |
| Road validation | Repeated hot/cold starts, logging and fault recovery |

**Stop testing** for unexpected starter engagement, throttle movement, unintended vehicle motion, fuel/oil leaks, low oil pressure, overheating or loss of steering/brakes.

## Test notes

For each important electrical or CAN test, save:

- Date and engine/vehicle state
- Wiring or connector used
- ECU calibration and firmware version
- Exact commands or CAN data
- Measured result and any error codes

Raw logs and screenshots should accompany any procedure intended for someone else to reproduce.
