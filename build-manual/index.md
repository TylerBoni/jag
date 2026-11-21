# Jaguar F-Type L92 Swap

**2015 Jaguar F-Type (X152) · GM L92 6.2L V8 · GM E38 ECM · Jaguar ZF8 retained as project intent**

This is a version-controlled, evidence-based engineering manual for the Jaguar F-Type LS swap. It is not a validated complete conversion recipe. All unverified connections, control messages and safety checks remain clearly identified.

!!! warning "Experimental powertrain integration"
    Do not use unverified wiring diagrams, CAN messages or starting procedures on a road-going vehicle. Starter interlocks, Park/Neutral detection, braking, throttle plausibility, engine shutdown and driveline torque coordination require formal verification.

## Start here

- [Build overview, evidence rules and scope](README.md)
- [What has actually been observed](EVIDENCE.md)
- [Outstanding safety and engineering work](ISSUES.md)
- [Engine and packaging](docs/mechanical/engine-and-packaging.md)
- [Jaguar ↔ GM electrical interfaces](docs/electrical/interfaces.md)
- [CAN replay experiments](docs/can/protocol-and-experiments.md)
- [Parts and costs](PARTS.md)
- [Testing and validation gates](docs/testing/validation-plan.md)

## Existing engineering source code

The [jag repository](https://github.com/TylerBoni/jag) also contains [CAN engineering tools](https://github.com/TylerBoni/jag/tree/master/can_engineering), [STM32 CAN Triple firmware](https://github.com/TylerBoni/jag/tree/master/CAN_Triple) and a [fuel pump controller](https://github.com/TylerBoni/jag/tree/master/fuel_pump_controller). Their presence does not imply validated road-ready vehicle software.

## Evidence labels

| Classification | Interpretation |
| --- | --- |
| **TESTED** | Specific observable result with setup and limitations; historical reports are explicitly marked reported |
| **INSTALLED** | Present physically, but not yet validated |
| **RESEARCH** | Externally sourced finding requiring independent verification |
| **EXPERIMENTAL** | Proposed or investigated behavior without confirmed end-to-end result |
| **OPEN** | Unknown measurement, wire, calibration or unresolved system issue |

Use [the changelog](CHANGELOG.md) to follow technical changes. Each confirmed discovery should update the affected subsystem, evidence ledger and open-issues register.
