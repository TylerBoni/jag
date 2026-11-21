# GM E38 ECU calibration

## Current state

- ECM family: GM E38; exact service number, operating system, VIN, tune source and checksums **OPEN**.
- Engine: donor L92 Gen IV 6.2L. Discussed changes include VVT delete, cam swap, intake MAF placement and wideband.
- VATS disabling reported in earlier project discussions; verify current calibration readback.
- Fueling without stock MAF or oxygen sensors has been proposed; it is **not** documented here as running, validated or acceptable for road use.
- Transmission torque communication and starting handshake require separate evidence.

## Calibration register

| Item | Recorded value | Classification |
| --- | --- | --- |
| ECM hardware/service PN | Unknown | OPEN |
| ECU OS / calibration IDs | Unknown | OPEN |
| Stock binary and SHA256 hash | Not archived | OPEN |
| VATS state | Reported disabled | Reported; confirm readback |
| Camshaft / VVT delete | Under development | OPEN |
| Injector PN and flow/offset data | Unknown | OPEN |
| MAF/VE/speed density strategy | Under consideration | EXPERIMENTAL |
| O2 and wideband hardware/calibration | Not documented | OPEN |
| Fuel, spark, knock, torque and temp logs | Not archived | OPEN |

## Validation

Before enabling sustained running, validate crank/cam sync, fuel pressure and regulator behavior, oil pressure, injector/coil power, sensor plausibility, commanded/actual throttle and load calculations. Record idle and transient AFR, trims if applicable, knock, cooling, DTCs and transmission torque messages, using a verified wideband. Test failures and rollback logic must be documented. Save original calibration and hashes before changes.
