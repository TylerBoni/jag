# Jaguar XF X250 ↔ GM E38 ECM CAN Translation

This is the working bridge document for translating between the Jaguar HS-CAN side (`hs_bus.dbc`) and the GM E38/GMLAN side (`gm_can_bus/07_denali_l92.dbc`).

The practical goal is:

1. Keep the GM E38 ECM happy enough to run the engine, cruise control, and GM torque-management logic.
2. Feed the Jaguar cluster/body side enough ECM/TCM-style information to keep the car usable and suppress avoidable warnings.
3. Translate Jaguar driver inputs, especially cruise and shift/manual inputs, into GM messages where the E38 expects BCM/TCM-originated traffic.

## Architecture

```text
Jaguar HS-CAN                       Bridge                       GM high-speed CAN / GMLAN
------------                       ------                       -----------------------
Jag cruise buttons 0x217  ----->  cruise mapper  ------------>  GM cruise switch 0x1E1
Jag speed / wheel speed    ----->  speed mapper   ------------>  GM TCM speed 0x0F9
Jag selector / paddles     ----->  shift mapper   ------------>  GM gear state 0x1F5
Non-GM TCM shift state     ----->  TM mapper      ------------>  GM torque request 0x199
GM E38 RPM / status        ----->  cluster mapper ------------>  Jag RPM/status frames
```

The GM E38 should be treated as the engine controller and cruise controller. The bridge does **not** send a target cruise speed. It sends button state and believable speed/state data; the E38 captures current speed when `SET` is pressed.

## Priority Message Set

### Jaguar → GM E38

| Function | Jaguar source | GM destination | Status |
|---|---|---|---|
| Cruise buttons | `0x217` `c_CruiseButtons` | `0x1E1` `CruiseSwitchStatus_observed` | high confidence |
| Vehicle speed | Jaguar ABS/speed candidate | `0x0F9` `TransOutputShaftSpeed_observed` | mapping known, source selection still open |
| Brake state | Jaguar brake/ABS/physical input | `0x0C9` brake state or hardwired ECM input | open; critical for cruise cancel |
| Selector range | Jaguar gear selector / non-GM TCM | `0x1F5` `ShiftLeverPosition_observed` | high confidence on GM side |
| Current/target gear | non-GM TCM | `0x1F5` gear/target/phase fields | high confidence on GM side |
| Torque management | non-GM TCM | `0x199` torque request | strong but protection/check value unresolved |
| Power mode / wake | Jaguar ignition/power state | `0x1F1` power mode candidate | raw/provisional |

### GM E38 → Jaguar

| Function | GM source | Jaguar destination | Status |
|---|---|---|---|
| Engine RPM | `0x0C9` `EngineSpeed_observed` | `0x295` `c_RPM_Raw` | high confidence both sides |
| Accelerator/throttle | `0x0C9` accelerator position | `0x2B5` throttle candidate | Jaguar side inferred |
| Engine presence/status | GM ECM running state | `0x4D5` ECM ETM/status | Jaguar required for RPM trust |
| Engine faults / MIL | GM DTC/MIL source TBD | `0x3F5` / `0x4B5` | open |
| Engine temperature | GM coolant temp source TBD | `0x4D5` / `0x355` | Jaguar destination partly known, GM source open |

## Cruise Translation

Jaguar cruise buttons are on `0x217`:

| Jaguar `c_CruiseButtons` | Meaning | GM `0x1E1` status |
|---:|---|---:|
| `0x00` | normal / no button | `0x40` if cruise master is on, else `0x00` |
| `0x20` | set/plus on Jaguar side | `0x54` or `0x68` depending button interpretation |
| `0x04` | minus | `0x54` |
| `0x40` | resume | `0x68` |
| `0x02` | cancel | `0xC0` |

GM `0x1E1` packet construction:

```text
D1 = status
D2 = (-status - (D3 & 0x03)) & 0xFF
D3 bits 0-1 = rolling counter 0..3
D3 bit 2 = optional key/cold-start mode bit; do not include in protection formula
```

Confirmed GM status values:

| GM status | Meaning |
|---:|---|
| `0x00` | cruise off completely |
| `0x40` | cruise on, no buttons pressed |
| `0x54` | negative/set button down |
| `0x68` | plus/resume button down |
| `0xC0` | cancel button down |

Open implementation decision: Jaguar combines some button semantics differently than GM. If the Jaguar stalk/button only reports `Set_Plus` as `0x20`, the bridge may need context:

- First press after cruise-on: send GM `SET` (`0x54`) to capture speed.
- Later increment press: send GM `PLUS/RESUME` (`0x68`) if the driver intent is speed increase.

## Vehicle Speed Translation

GM E38 cruise and diagnostics need believable vehicle/transmission speed. In the 2007 GM logs, the best decoded source is TCM frame `0x0F9`:

```text
GM 0x0F9 D4-D5 big-endian raw = transmission output shaft speed / 0.25 rpm
GM output shaft rpm = raw * 0.25
```

User observation: GM raw `6000` is about `40 mph`, so decoded output shaft speed is about `1500 rpm`.

Bridge formula if starting from vehicle speed:

```text
wheel_rpm = mph * 1056 / tire_circumference_inches
output_shaft_rpm = wheel_rpm * final_drive_ratio
gm_raw = round(output_shaft_rpm / 0.25)
```

Equivalent:

```text
gm_raw = round(mph * 1056 * final_drive_ratio / tire_circumference_inches / 0.25)
```

Jaguar speed candidates:

| Jaguar frame | Signal | Notes |
|---|---|---|
| `0x20B` | `i_VehicleSpeed` | D6-D7 big-endian speed candidate; current DBC says `0.01 km/h`, but bench comments indicate X250 display encoding needed special calibration. |
| `0x24B` / `0x294` | individual wheel speeds | inferred/cross-platform candidates; useful if ABS source is available. |

For the bridge, the safest first source is the non-GM TCM or a direct VSS/driveshaft speed measurement, then synthesize GM `0x0F9`. If the Jaguar ABS remains present and trusted, use its vehicle/wheel speed only after validating scale against GPS or the GM `0x0F9` raw values.

## Gear / Range Translation

GM `0x1F5` is the main gear/range state frame:

| GM signal | Role |
|---|---|
| `CurrentGear_observed` | achieved/current gear, D1 low nibble |
| `CurrentGearShiftPhase_observed` | shift phase, D1 high nibble |
| `TargetGear_observed` | target gear, D2 low nibble |
| `TargetGearShiftDirection_observed` | `0` steady, `1` upshift target, `2` downshift target |
| `ShiftLeverPosition_observed` | Park=1, Reverse=2, Neutral=3, Drive/M6=4, M5=5, M4=6, M3=7, M2=8, M1=9 |

Jaguar cluster/selector gear state is `0x3F3`:

```text
D1 = 0x10       # simplified bench-confirmed gearbox-fault avoidance
D2 = 0x04       # simplified bench-confirmed gearbox-fault avoidance
D3 = counter or raw counter byte
D4 = (D3 + Mode + ManualGear + 2) & 0xFF
D5 = ~Mode & 0xFF
D6 = ~ManualGear & 0xFF
D7 = Mode
D8 = ManualGear
```

Jaguar `Mode` / `ManualGear`:

| Range | Jaguar `Mode` | Jaguar `ManualGear` |
|---|---:|---:|
| Park | `0x00` | `0x80` |
| Reverse | `0x01` | `0x00` |
| Neutral | `0x02` | `0x00` |
| Drive | `0x04` | `0x00` |
| Sport | `0x08` | `0x40` or `0x00` depending mode handling |
| Manual M1..M6 | `0x08` | `0x01`, `0x02`, `0x04`, `0x08`, `0x10`, `0x20` |

GM range to Jaguar cluster translation:

| GM `ShiftLeverPosition_observed` | Meaning | Jaguar `Mode` | Jaguar `ManualGear` |
|---:|---|---:|---:|
| `1` | Park | `0x00` | `0x80` |
| `2` | Reverse | `0x01` | `0x00` |
| `3` | Neutral | `0x02` | `0x00` |
| `4` | Drive/M6 | `0x04` | `0x00` |
| `5` | M5 | `0x08` | `0x10` |
| `6` | M4 | `0x08` | `0x08` |
| `7` | M3 | `0x08` | `0x04` |
| `8` | M2 | `0x08` | `0x02` |
| `9` | M1 | `0x08` | `0x01` |

## Torque Management Translation

This is the high-risk part of the bridge.

The non-GM TCM must produce enough GM TCM behavior for the E38 to perform torque reduction during shifts:

| GM ID | Purpose | Bridge source |
|---|---|---|
| `0x199` | TCM torque request / torque reduction | non-GM TCM shift events |
| `0x1F5` | current/target gear and shift phase | non-GM TCM gear state |
| `0x0F9` | output speed and ratio/status | speed sensor + gear/ratio model |
| `0x19D` | engine speed request candidate | rev-match/downshift logic; unresolved |

Baseline `0x199` when no shift torque management is requested:

| Signal | Baseline observed value |
|---|---:|
| `TCMTorqueReq3Active_observed` | `0` |
| `TCMTorqueReq3_observed` | `1199.5 Nm` |
| `TCMTorqueReq4Active_observed` | `0` |
| `TCMTorqueReq4_observed` | `625 Nm` |
| `TCMTorqueReqRollingCounter_observed` | rolling `0..3` |
| `TCMTorqueIncreaseRate_observed` | `255` |

Upshift behavior observed in GM logs:

1. `0x1F5` announces target gear/direction before or during the shift.
2. `0x199` active bit rises.
3. `TCMTorqueReq3_observed` drops sharply, sometimes near `20 Nm`.
4. After shift completion, `0x1F5` returns to steady current=target and `0x199` returns inactive/baseline.

Do **not** transmit live `0x199` into the E38 until the rolling counter and protection/check field are solved. A bad torque-management request can cause DTCs, limp behavior, or incorrect torque intervention.

## RPM Translation to Jaguar Cluster

GM source:

```text
GM 0x0C9 EngineSpeed_observed = bytes D2-D3 big-endian * 0.25 rpm
```

Jaguar destination `0x295`:

```text
raw16 = 0x8000 + rpm
D6 = raw16 >> 8
D7 = raw16 & 0xFF
D5 = 0xFF - D7
```

The Jaguar cluster requires `0x4D5` ECM status/presence for RPM to be trusted.

## Brake / Cruise Cancel

Cruise will not be safe unless brake cancel is handled both electrically and over CAN.

Open items:

- Determine whether the E38 in this harness uses a hardwired brake input, CAN brake state, or both.
- If bridging CAN brake state, confirm whether GM `0x0C9` `BrakePedalDiscrete_observed` can/should be synthesized when the BCM/stock source is absent.
- For safety, any brake press should immediately send GM cruise `CANCEL` (`0xC0`) on `0x1E1` and suppress torque-management/cruise requests that could add throttle.

## Initial Bridge Implementation Order

1. **Listen-only validation**: decode Jaguar buttons/speed/gear and GM RPM/speed/gear in parallel without transmitting duplicates.
2. **Bench/off-vehicle transmit**: generate GM `0x1E1`, Jaguar `0x295`, and Jaguar `0x3F3` into isolated modules first.
3. **Cruise-only road test**: with stock GM TCM still present, bridge only Jaguar cruise buttons to GM `0x1E1`; do not transmit `0x0F9`, `0x1F5`, or `0x199` duplicates.
4. **TCM shadow mode**: non-GM TCM computes proposed `0x0F9`, `0x1F5`, and `0x199` while stock TCM remains connected, but bridge does not transmit them.
5. **TCM emulation mode**: only after shadow logs match stock TCM patterns, isolate/remove stock TCM messages and transmit the bridge-generated set.

## Open Questions

| Area | Question | Why it matters |
|---|---|---|
| GM `0x199` | How is `TCMTorqueReq4Protection_observed` generated? | Required before safe torque-management transmission |
| GM `0x19D` | Exact engine-speed request layout? | Needed for downshift blips/rev matching |
| GM `0x4C9`/`0x4E9` | Are these required for U0101-free TCM absence? | May be necessary for ECM diagnostics |
| Jaguar speed source | Which Jaguar speed signal should the bridge trust? | Cruise and cluster speed need stable calibrated speed |
| Brake input | Hardwired vs CAN brake authority into E38? | Safety-critical cruise cancel |
| Jaguar cruise `0x20` | Does driver expect set or plus? | Needs context/state mapping to GM `0x54` vs `0x68` |

