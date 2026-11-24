# Wiring and electrical

I'm using a **GM E38 ECM** with the Jaguar wiring and electronics.

## What works so far

| Circuit | Result |
| --- | --- |
| Accelerator pedal | Jaguar pedal works with the E38 |
| Brake signal | Measured about 1.5 V with brake applied and short 12 V pulses at transitions |
| Park/Neutral input | Grounding the orange/black wire at GM E38 pin 1 enabled starter relay operation during the crank-request test |
| Fuel pump bench | Measured 57.9 psi using the donor fuel-pump control setup |

On the donor harness, the orange/black wire at E38 pin 1 normally goes to the park switch. I grounded it during the test. The installed wiring will use a Park/Neutral switch to ground the input only in Park or Neutral. The E38 connector designation and exact CAN payload still need to be recorded.

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

- Install and test the Park/Neutral switch and starter interlock
- Complete Jaguar-to-E38 pin map
- OBD-II wiring
- Jaguar alternator charging control
- Denali A/C compressor control
- Fuel-pump wiring and fail-safe behavior in the car

E38 CAN connections at **X1 pins 27/28** came up during research; those pins are **unconfirmed for this harness** and aren't a wiring instruction.

## Starter safety

Starter operation must be inhibited outside Park/Neutral, stop when the engine is running, and time out if the engine doesn't start. Loss of a required signal must disable cranking.

See the [CAN experiments](../can/protocol-and-experiments.md) and [testing plan](../testing/validation-plan.md).
