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

## Accelerator pedal wiring

The Jaguar accelerator pedal worked with the GM E38 in my test. This is the wire color map from my wiring notes for the 2015 F-Type and 2007 Yukon Denali donor harness.

| Circuit | Jaguar wire | GM wire |
| --- | --- | --- |
| APP 1 5 V reference | Green/Orange | White/Black |
| APP 1 signal | Yellow/Orange | Dark Blue |
| APP 1 low reference | Violet/Green | Brown |
| APP 2 5 V reference | Blue/Gray | Tan |
| APP 2 signal | Blue/White | Light Blue |
| APP 2 low reference | Yellow | Purple |

Connector cavity assignments still need verification. Before splicing, confirm each circuit against the connector diagrams for both harnesses. With the engine off, log both APP channels through a full pedal sweep before enabling throttle operation.

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
