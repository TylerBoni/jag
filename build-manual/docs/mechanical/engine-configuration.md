# L92 engine configuration — Section 1

> **Evidence:** documented interview, five questions completed 2026-11-21. The documented build configuration is authoritative; installation and operational verification are tracked separately. See [Evidence ledger](../../EVIDENCE.md) and [open issues](../../ISSUES.md).

## Build stage and CAD-based mounting

- **Vehicle:** 2015 Jaguar F-Type base (X152), originally AJ126 supercharged V6 and Jaguar ZF8.
- **Donor engine:** 2007 GMC Yukon Denali GM L92 6.2L V8 (previously documented acquisition cost $1,300 and approximately 272,000 donor miles).
- **Installation:** L92 remains **outside the Jaguar**. Do not describe as engine-swapped, test-fitted or road-tested.
- **Mount design:** Project includes **3D-scanning the engine compartment**, positioning a modeled LS engine within the scan, designing custom engine mounts in CAD, and having the mounts **laser-cut and bent**. The mounts have been fabricated; their physical fit and loading **not yet demonstrated**. Collect scan export, LS reference model, CAD files, dimensional drawing, material, thickness, fastener and tolerance records and test-fit photographs.

## Internal engine configuration

| Item | Build configuration | Verification gap |
| --- | --- | --- |
| Cylinder heads | Original factory L92 | Casting IDs/inspection not recorded |
| Pistons | Original factory L92 | No measurement or part identification |
| Connecting rods | Original factory L92 | No part inspection recorded |
| Crankshaft | Original factory L92 | No casting/part inspection recorded |
| Compression ratio | Intended factory-internals configuration | Exact ratio not measured or asserted |
| Camshaft | **Richard Holdener Performance (RHP) Truck Plus** | Actual cam PN and cam card missing; installed state not explicitly confirmed |
| Valve springs | RHP springs supplied with cam | Spring PN, specifications and installed setup/height missing |
| Lifters | Unknown | Original vs replacement and part IDs open |
| Timing set | Replaced | Make/model, gears, chain and alignment verification open |
| VVT delete | Generic Michigan Motorsports kit | Contents, PN, assembly procedure and ECU VVT settings open |

**Status:** Build configuration established. Installation, dimensional verification, and functional testing are tracked individually.

## Induction, fueling and ignition

| Component | Build configuration | Verification gap |
| --- | --- | --- |
| Intake manifold | Factory L92 truck manifold | Casting or GM PN unknown |
| Electronic throttle body | Factory L92 | PN and ETC sweep verification unknown |
| Fuel injectors | Original L92 | PN, flow data, electrical characteristics and service state unknown |
| Ignition coils | Original L92 | PN and coil/plug wiring audit unknown |

Previous project discussions described Jaguar intake plumbing and MAF arrangement; **do not confuse proposed Jaguar intake piping with a confirmed replacement of the stock L92 intake manifold**.

## Accessories, hydraulics and front drive

| Component | Build configuration | Evidence and open work |
| --- | --- | --- |
| Water pump | Corvette configuration | Earlier conversation mentions 2004 Corvette application; current answer only confirms "Corvette". Exact PN and physical installation unknown |
| Crankshaft balancer | Corvette configuration | Exact PN, pulley offset, bolt procedure, belt alignment and fit unknown |
| Alternator | **Jaguar alternator**, adapted to **ICT Billet low-mount bracket** using custom adapter | Make/PN, bracket PN, adapter CAD/fasteners, electrical excitation and charging test unknown |
| A/C compressor | **Factory Denali A/C compressor retained** (configuration correction, supersedes earlier Jaguar selection) | Exact compressor PN, condition, physically mounted status, line adaptation and cooling operation not verified |
| A/C bracket | ICT Billet bracket for Denali A/C compressor | Specific bracket PN, fit, pulley plane and installed state unknown |
| Power steering pump | **G8 pump**, **ICT Billet bracket** | Exact pump/bracket PN and operating pressure/flow unverified |
| Power steering reservoir | Jaguar reservoir retained; return hose trimmed | Routing, support, capacity, leak/heat evaluation outstanding |
| High-pressure PS line | Jaguar banjo end cut off; tube flared and adapted for **-6 AN** connection to G8 pump | **Safety critical:** exact flare standard/seat, adapter fitting, tube material, hose pressure rating, pressure relief behavior and leak test not verified |

**Do not assume the Jaguar high-pressure line's new flare is compatible with a standard 37° AN seat merely because a -6 AN fitting was used.** A documented pressure-rated connection and professional inspection are required prior to operation.

## Acquisition / verification TODO

1. Photograph each component label and casting number, and record exact vendor PN and purchase invoice.
2. Provide engine-bay 3D scan, CAD engine model source, mount DXFs, bend drawing, material thickness, and mount fasteners.
3. Confirm timing set, cam card, RHP spring details and Michigan Motorsports delete kit.
4. Identify factory Denali A/C compressor PN, ICT bracket PNs and physical installation status, then verify alignment and refrigerant-line compatibility.
5. Confirm which accessory parts are physically mounted on the standalone engine, versus purchased or intended.
6. Document balancer/pulley plane and belt lengths with measured coordinates.
7. Validate steering-line flare type, pressure requirements and fitting compatibility before pressurization.

For information status, see [evidence](../../EVIDENCE.md). No motor-mount, accessory or steering design has passed in-vehicle validation under this section.
