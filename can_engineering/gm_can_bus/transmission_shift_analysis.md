# Transmission Shift and Torque-Management Analysis

This pass focuses on messages useful for transmission shifting and torque management, using `normal accel`, `wot`, `cruise`, `up-down-manual`, and `prndl` captures.

## Strongest Transmission Message: `0x1F5`

`0x1F5` is the clearest gear/shift-state frame.

### Drive Upshift Pattern

During normal acceleration, the first two bytes follow this pattern:

| Payload prefix | Interpretation |
|---|---|
| `01 01` | steady 1st gear |
| `01 12` | current gear 1, target gear 2, upshift requested/in progress |
| `02 12` | current gear now 2, target still 2, upshift settling |
| `02 02` | steady 2nd gear |
| `02 13` | current gear 2, target gear 3, upshift requested/in progress |
| `03 13` | current gear now 3, target still 3, upshift settling |
| `03 03` | steady 3rd gear |

This repeats through higher gears.

### Decoded Nibbles

| Byte/field | DBC signal | Meaning |
|---|---|---|
| D1 low nibble | `CurrentGear_observed` | current/achieved gear |
| D1 high nibble | `CurrentGearShiftPhase_observed` | shift/torque-management phase marker; `0x2` and `0x4` appear during shifts |
| D2 low nibble | `TargetGear_observed` | target/next gear |
| D2 high nibble | `TargetGearShiftDirection_observed` | `0x1` upshift target, `0x2` downshift target |
| D3 | `TapUpDownModeRaw_observed` | `0x10` in manual/tap mode |
| D4 | `ShiftLeverPosition_observed` | selector/manual gear request |
| D6 | `DriverShiftControlRaw_observed` | `0x02` in manual/tap mode |

### Manual Mode Pattern

`up-down-manual.csv` confirms the same current/target gear encoding while D3 stays `0x10` and D6 stays `0x02`. Downshift examples use D2 high nibble `0x2`, e.g. `06 25` means current gear 6, target gear 5, downshift target.

## Transmission Speed / Ratio Frame: `0x0F9`

`0x0F9` has the repository-listed transmission status contents.

| Field | Confidence | Notes |
|---|---|---|
| D1-D2 big-endian | medium | `TransEstimatedTorqueRatioRaw_observed`; follows gear/range state, not road speed. Examples: `0x07AF` in 1st/drive stationary, `0x00AA` in 6th, `0x7CF0` in reverse, `0x0000` in park/neutral |
| D3 | high raw | usually `0x40`; likely validity/status flags |
| D4-D5 big-endian | high | `TransOutputShaftSpeed_observed`; zero at stationary idle/PRNDL, rises smoothly with vehicle motion, and scales as `0.25 rpm/count`. Raw `6000` is about `1500 rpm`, observed around `40 mph` |
| D6-D7 | medium raw | changes strongly with vehicle motion and shift phase; likely includes status/protection/check bytes |

Torque-ratio scaling is not established yet. Output-shaft speed now uses the observed `0.25 rpm/count` scale; vehicle mph requires final-drive ratio and tire circumference.

## Torque-Management Candidates

The captures show several frames that change strongly during `0x1F5` shift phases. These are candidates for torque-management, torque intervention, or torque-ratio related signals.

| ID | Candidate evidence |
|---:|---|
| `0x199` | Strongest candidate. Public/community decode identifies it as TCM engine torque request; local logs show inactive idle/brake values and request activation/drop during upshift windows. |
| `0x0F9` | Repository-listed as including transmission estimated torque ratio; D4-D7 change strongly between stable gear and shift phases. |
| `0x0C1` / `0x0C5` | High-rate 8-byte frames; many 16-bit fields change around upshift/downshift windows. Likely powertrain torque/engine-management related, but signal identity is not yet proven. |
| `0x1E5` | Changes strongly around PRNDL/manual/shift states and may include brake/torque/request flags; needs more controlled tests. |
| `0x191` | Three repeated 16-bit-like values plus trailing bytes; moves with engine/load and shift phase. Candidate for pedal/throttle/torque/load style data, not labeled yet. |
| `0x19D`, `0x1E9`, `0x3F9`, `0x4D1` | Shift-correlated changes exist, but confidence is lower without known physical references. |

## Recommended Next Captures

For torque management specifically, the most useful next logs would be:

1. Steady 2nd or 3rd gear pull with no shift, then same throttle with a commanded shift.
2. Manual mode hold gear at fixed throttle, then tap shift while holding throttle steady.
3. Tow/haul on/off comparison during the same acceleration profile.
4. Brake-torque or low-speed converter load test if safe: stationary/creep with brake applied and small throttle.
5. Any scanner/PID overlay for engine torque, delivered torque, trans input/output speed, gear command, and torque converter slip.
