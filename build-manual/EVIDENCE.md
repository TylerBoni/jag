# Evidence ledger

Prior project chat statements are **reported observations**, not raw evidence. Keep the distinction between what the operator observed and why it may have occurred.

| ID | Classification | Observation | Limits / next evidence |
| --- | --- | --- | --- |
| E-001 | TESTED (reported) | Jaguar accelerator pedal worked with GM E38 | Exact E38 and Jaguar pin assignments, APP channels, sweep voltages, plausibility response missing |
| E-002 | TESTED (reported) | Starter-only cranking without plugs produced ~20 psi indicated oil pressure | Instrument, cranking RPM, oil temperature, remote oil filter routing and hot pressure unknown |
| E-003 | TESTED (reported) | Grounding orange/black wire changed E38 start-related behavior; single CAN signal reportedly sufficient | Identify connector/cavity and electrical function; isolate effect of CAN message and independent PRNDL interlock |
| E-004 | TESTED (transmit interface log) | `replay_cold_start.py` selected 56 frames of CAN ID `0x1F1`; board said `REPLAY DONE sent=56 drop=0` | No demonstration of receiving-module acceptance, actual payload, timings, or cranking action |
| E-005 | TESTED (reported bench) | Donor fuel-system bench reported 57.9 psi | Test geometry and applicability to installed fuel system unknown |
| E-006 | RESEARCH | E38 X1 cavities 27/28 suggested for CAN | Check exact ECM service/OS and harness drawings before connection |
| E-007 | EXPERIMENTAL | CAN IDs `0x1E1`, `0x199`, `0xD0` considered for cruise/torque/throttle | Exact payload, scaling, vehicle/bus, checksums and interpretation not established |

| E-008 | OWNER-REPORTED DESIGN/FABRICATION | Engine remains outside Jaguar; 3D bay scan, LS CAD placement and laser-cut/bent custom mounts | CAD revision, material, dimensions, mounting strength and vehicle test fit absent |
| E-009 | OWNER-REPORTED CONFIGURATION | Original L92 heads, pistons, rods, crankshaft, intake, throttle body, injectors and coils | Parts/castings not independently examined |
| E-010 | OWNER-REPORTED CONFIGURATION | RHP Truck Plus cam and supplied valve springs; replaced timing set; generic Michigan Motorsports VVT delete; lifters unknown | Missing PNs, cam card and photos verifying installation |
| E-011 | OWNER-REPORTED CONFIGURATION | Corvette pump and balancer; Jaguar alternator/ICT adapter; G8 PS pump/ICT bracket; Jaguar reservoir and modified -6 AN pressure line | Hardware ID, installation and pressure testing absent; owner subsequently clarified factory Denali A/C compressor with ICT bracket |

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
