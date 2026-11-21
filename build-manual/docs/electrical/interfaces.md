# Jaguar and GM E38 electrical interfaces

> **SAFETY CRITICAL:** Wire color alone does not identify a circuit. Verify both connector cavity and conductor continuity with the correct year/trim service documentation before applying 12 V or ground. Protect power feeds and prove fail-off states.

| Interface | Status | Evidence and missing steps |
| --- | --- | --- |
| Jaguar accelerator pedal to E38 | TESTED (reported) | Pedal reportedly works; capture complete pin/cavity map, dual sweep voltages, correlation and failure response |
| Brake | TESTED (reported measurement), signal meaning OPEN | Approximately 1.5 V held when brake applied and 12 V pulses at transitions reported; oscilloscope trace, loads and logic still needed |
| Orange/black wire | TESTED (reported effect), circuit OPEN | Ground changed starting-related behavior; DO NOT infer groundable wire or park input without connector/cavity and electrical identity |
| Starter | EXPERIMENTAL | Jaguar native control vs independent intelligent starter controller; relay polarity, brake/PRNDL, 10–15s timeout and run detection to be specified/tested, not presumed |
| E38 CAN | RESEARCH | X1 cavities 27/28 mentioned; verify exact service ECM and wiring before connection |
| OBD-II | OPEN | Define DLC power, ground, high/low pins, protection and bus arrangement from verified diagrams |
| Alternator | OPEN | Regulator strategy and Jaguar charging/BCM integration |
| A/C | OPEN | Compressor, request logic, pressure switches, fuse size and control strategy |
| Fuel pump | TESTED (reported bench), installed validation OPEN | Bench 57.9 psi reported; see [fuel pump firmware](../../../fuel_pump_controller/) and confirm pinout/current/failsafes |

## Pin map template

| Module | Connector/cavity | Circuit direction | Wire color | Voltage/state/load | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | OPEN |

## Start interlocks

An E38 or external starter controller must refuse crank unless transmission state is independently proven Park/Neutral and other required brake/start conditions are met. Stop on engine-running confirmation, elapsed max crank interval, loss of valid inputs and emergency stop. Validate stuck inputs, shorts to battery/ground and CAN timeout. Never interpret successful starter engagement as an acceptable safety strategy.
