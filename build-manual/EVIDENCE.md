# Evidence ledger

Builder-specified configuration is authoritative. Mark an assertion **UNCONFIRMED** when it is inferred rather than supplied or measured. Record actual test outcomes separately from configuration. Preserve safety-critical test evidence.

| ID | Classification | Finding | Notes |
| --- | --- | --- | --- |
| E-001 | TESTED | Jaguar accelerator pedal worked with GM E38 | Exact E38 and Jaguar pin assignments, APP channels, sweep voltages, plausibility response missing |
| E-002 | TESTED | Starter-only cranking without plugs produced ~20 psi indicated oil pressure | Instrument, cranking RPM, oil temperature, remote oil filter routing and hot pressure unknown |
| E-003 | TESTED | Grounding orange/black wire changed E38 start-related behavior; one CAN signal was sufficient in the observed test | Identify connector/cavity and electrical function; isolate effect of CAN message and independent PRNDL interlock |
| E-004 | TESTED (transmit interface log) | `replay_cold_start.py` selected 56 frames of CAN ID `0x1F1`; board said `REPLAY DONE sent=56 drop=0` | No demonstration of receiving-module acceptance, actual payload, timings, or cranking action |
| E-005 | TESTED (bench) | Donor fuel-system bench recorded 57.9 psi | Test geometry and applicability to installed fuel system unknown |
| E-006 | RESEARCH | E38 X1 cavities 27/28 suggested for CAN | Check exact ECM service/OS and harness drawings before connection |
| E-007 | EXPERIMENTAL | CAN IDs `0x1E1`, `0x199`, `0xD0` considered for cruise/torque/throttle | Exact payload, scaling, vehicle/bus, checksums and interpretation not established |
| E-008 | DESIGNED / FABRICATED | Engine remains outside Jaguar; 3D bay scan, LS CAD placement and laser-cut/bent custom mounts | In-vehicle fit test not yet documented |
| E-009 | CONFIGURATION | Original L92 heads, pistons, rods, crankshaft, intake, throttle body, injectors and coils | As specified in build interview |
| E-010 | CONFIGURATION | RHP Truck Plus cam and supplied valve springs; replaced timing set; generic Michigan Motorsports VVT delete; lifters unknown | Lifters not specified |
| E-011 | CONFIGURATION | Corvette pump and balancer; Jaguar alternator/ICT adapter; factory Denali A/C compressor with ICT bracket; G8 PS pump/ICT bracket; Jaguar reservoir and modified -6 AN pressure line | High-pressure steering connection requires a safety test |

## Required test entry

```markdown
### E-### — Discovery title
- Date, operator, vehicle state:
- Status: TESTED / INSTALLED / RESEARCH / EXPERIMENTAL / OPEN
- Hardware and connector identifiers:
- Firmware SHA / ECU service number / OS / tune hash:
- Setup, instrumentation, and method:
- Raw capture, trace, photo, drawing, or source:
- Exact observations (separate from interpretation):
- Acceptance criterion, failure outcome, next test:
- Safety concerns:
```
