# Jaguar F-Type LS Swap

A build guide for putting a **GM L92 6.2L V8 into a 2015 Jaguar F-Type**, retaining the Jaguar ZF8 automatic.

I'm documenting the parts, CAD work, fabrication, electronics and testing as I go. The engine is still out of the car, so this is a work-in-progress build, not a finished swap recipe.

## Build guide

- [Engine setup](docs/mechanical/engine-configuration.md)
- [Engine packaging, oil and cooling](docs/mechanical/engine-and-packaging.md)
- [Wiring](docs/electrical/interfaces.md)
- [CAN bus](docs/can/protocol-and-experiments.md)
- [GM E38 tuning](docs/ecu/e38-calibration.md)
- [Fabrication](docs/fabrication/fabrication.md)
- [Parts and costs](PARTS.md)
- [Testing](docs/testing/validation-plan.md)

## Reverse-engineering code

The [GitHub repository](https://github.com/TylerBoni/jag) has the [CAN scripts](https://github.com/TylerBoni/jag/tree/master/can_engineering), [STM32 CAN Triple project](https://github.com/TylerBoni/jag/tree/master/CAN_Triple) and [fuel pump controller](https://github.com/TylerBoni/jag/tree/master/fuel_pump_controller).

!!! warning "Work in progress"
    Some systems are still being developed. Don't treat experimental wiring, CAN messages or starter controls as finished procedures. Verify the safety interlocks before running or driving the car.

[Open problems](ISSUES.md) · [Test notes](EVIDENCE.md) · [Changelog](CHANGELOG.md)
