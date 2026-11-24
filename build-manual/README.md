# Jaguar F-Type L92 Swap

I'm swapping a GM L92 6.2L V8 into a **2015 Jaguar F-Type V6 (X152)**, keeping the Jaguar ZF8 automatic transmission. This repo documents the parts, fabrication, wiring, CAN bus work and testing as I go.

**Build status:** Engine preparation and integration work are in progress. The L92 is still outside the car.

## Manual

- [Engine configuration](docs/mechanical/engine-configuration.md)
- [Engine packaging, oil and cooling](docs/mechanical/engine-and-packaging.md)
- [Electrical wiring](docs/electrical/interfaces.md)
- [CAN bus](docs/can/protocol-and-experiments.md)
- [GM E38 calibration](docs/ecu/e38-calibration.md)
- [Fabrication](docs/fabrication/fabrication.md)
- [Parts and costs](PARTS.md)
- [Testing](docs/testing/validation-plan.md)
- [Open problems](ISSUES.md)
- [Changelog](CHANGELOG.md)

## Code

This repository also contains the tools I've used for reverse engineering:

- [CAN engineering scripts](https://github.com/TylerBoni/jag/tree/master/can_engineering)
- [STM32 CAN Triple firmware](https://github.com/TylerBoni/jag/tree/master/CAN_Triple)
- [Arduino fuel pump controller](https://github.com/TylerBoni/jag/tree/master/fuel_pump_controller)

## What I've tested

- The Jaguar accelerator pedal works with the GM E38.
- I measured approximately **20 psi oil pressure** while cranking with the spark plugs removed.
- Grounding the orange/black park-switch wire at E38 pin 1 enabled the starter relay during the crank-request test. I’ll wire that input to a Park/Neutral switch for the installed starter interlock.
- My STM32 interface transmitted **56 frames on CAN ID `0x1F1`** with no reported drops. That log confirms transmission, not the E38's response.

These are results of individual tests, not proof that the entire swap is ready to drive.

## Using this guide

Anything described as installed or tested refers to something I've actually completed. Work in progress is identified where it matters. I don't include guessed pinouts, torque specs, CAN payloads or part numbers.

**Safety:** Check starter Park/Neutral interlocks, throttle fault behavior, fuel and oil systems, brakes and transmission control before attempting to drive the car. Never ground an unidentified wire based only on its color.
