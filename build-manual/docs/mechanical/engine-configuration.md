# L92 engine configuration — Section 1

Configuration established from the five-question build interview on 2026-11-21. Statements supplied by the builder are documented as build facts. An item is marked **UNCONFIRMED** only when the documentation adds an inference or lacks a specific answer.

## Engine and mounting

- **Vehicle:** 2015 Jaguar F-Type base (X152), originally AJ126 3.0L supercharged V6 with Jaguar ZF8 automatic.
- **Donor:** 2007 GMC Yukon Denali, L92 6.2L Gen IV V8, acquired for $1,300, approximately 272,000 miles.
- **Current stage:** L92 is **outside the Jaguar**.
- **Engine bay:** 3D scanned, with an LS engine modeled in the scanned engine compartment.
- **Motor mounts:** Custom designed in CAD, laser-cut and bent.

## Engine internals and valvetrain

| Component | Build specification |
| --- | --- |
| Cylinder heads | Original factory L92 |
| Pistons | Original factory L92 |
| Connecting rods | Original factory L92 |
| Crankshaft | Original factory L92 |
| Camshaft | Richard Holdener Performance (RHP) Truck Plus |
| Valve springs | RHP springs supplied with the camshaft |
| Lifters | Unknown |
| Timing set | Replaced |
| VVT delete | Generic Michigan Motorsports kit |

**UNCONFIRMED:** Compression ratio has not been specified. Stock L92 internals alone do not establish that it has been measured. Exact part numbers not supplied are omitted rather than guessed.

## Intake, fuel and ignition

| Component | Build specification |
| --- | --- |
| Intake manifold | Factory L92 truck |
| Throttle body | Factory L92 |
| Fuel injectors | Original L92 |
| Ignition coils | Original L92 |

Intake manifold and intake *ducting* are distinct systems. Jaguar intake ducting was discussed separately; it does not change the documented factory L92 intake manifold.

## Accessories and steering

| Component | Build specification |
| --- | --- |
| Water pump | Corvette |
| Crankshaft balancer | Corvette |
| Alternator | Jaguar alternator, custom adapter to ICT Billet low-mount bracket |
| A/C compressor | Factory Denali compressor |
| A/C bracket | ICT Billet |
| Power steering pump | G8 pump, ICT Billet bracket |
| Power steering reservoir | Jaguar reservoir |
| Power steering return line | Jaguar return line trimmed |
| Power steering high-pressure line | Jaguar banjo end cut off, line flared for -6 AN fitting to G8 pump |

**UNCONFIRMED:** A previous conversation mentioned a *2004 Corvette* water-pump application, but the final interview specified only Corvette. No specific pump or balancer part number is asserted.

### Safety-critical integration

The high-pressure steering line uses a modified flare connection. Before pressurizing it, confirm that the flare geometry, mating fitting, line and hose pressure ratings are compatible. A -6 AN nominal size alone does not establish an acceptable connection. Steering pressure/leak testing belongs in the [validation plan](../testing/validation-plan.md).

## Related documentation

- [Engine and packaging](engine-and-packaging.md)
- [Fabrication register](../fabrication/fabrication.md)
- [Parts and costs](../../PARTS.md)
- [Open engineering issues](../../ISSUES.md)
