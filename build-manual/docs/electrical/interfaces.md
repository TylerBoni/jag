# Wiring and electrical

I'm using a **GM E38 ECM** with the Jaguar wiring and electronics.

## What works so far

| Circuit | Result |
| --- | --- |
| Accelerator pedal | Jaguar pedal works with the E38 |
| Brake signal | Measured about 1.5 V with brake applied and short 12 V pulses at transitions |
| Start-related input | Grounding an orange/black wire changed the E38 starting behavior |
| Fuel pump bench | Measured 57.9 psi using the donor fuel-pump control setup |

The exact start-input connector pin and CAN payload aren't documented yet. **Do not ground a wire just because its color matches.** Identify the circuit and connector cavity first.

## Still working on

- Starter control and Park/Neutral interlock
- Complete Jaguar-to-E38 pin map
- OBD-II wiring
- Jaguar alternator charging control
- Denali A/C compressor control
- Fuel-pump wiring and fail-safe behavior in the car

E38 CAN connections at **X1 pins 27/28** came up during research; those pins are **unconfirmed for this harness** and aren't a wiring instruction.

## Starter safety

Starter operation must be inhibited outside Park/Neutral, stop when the engine is running, and time out if the engine doesn't start. Loss of a required signal must disable cranking.

See the [CAN experiments](../can/protocol-and-experiments.md) and [testing plan](../testing/validation-plan.md).
