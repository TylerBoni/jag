# GM Torque-Management Bridge Notes

Goal: keep the GM ECM and its torque-management behavior, while using a non-GM TCM. The bridge should translate non-GM TCM shift intent into the GM messages the ECM expects from a T43-style TCM.

## Strategy Summary

Known behavior from public service/aftermarket docs:

- GM 6-speed OE applications rely heavily on torque reduction for shift feel and clutch durability.
- The TCM sends a requested torque / torque-reduction request to the ECU.
- The ECU reduces engine output with spark timing and/or DBW throttle.
- Torque management applies to upshifts, downshifts, TCC events, and related shift transitions.

Useful references:

- Holley 6L80/90E GM 6 Speed Transmission Control: describes TCM requested torque, ECU virtual torque, and torque reduction by timing/DBW.
- GM service info for P2544: states the TCM may request ECM torque reduction during shift events.
- l77rodeo/gmlan: confirms the E38/T43 message set and published contents for `0x0F9`, `0x1F5`, `0x1E1`, `0x1F1`, and `0x4E9`.
- Community reverse-engineering threads identify `0x199` as TCM-to-ECM engine torque request and `0x19D` as TCM-to-ECM engine speed request.

## Current Best Message Set

| ID | Direction | Role for bridge |
|---:|---|---|
| `0x199` | non-GM TCM bridge -> ECM | engine torque request / torque-reduction request |
| `0x19D` | non-GM TCM bridge -> ECM | engine speed request candidate; likely useful for blips/rev matching |
| `0x0F9` | non-GM TCM bridge -> ECM | transmission output speed and torque-ratio/status |
| `0x1F5` | non-GM TCM bridge -> ECM | current gear, target gear, shift direction/phase, selector/manual mode |
| `0x4C9` | non-GM TCM bridge -> ECM | appears in U0101 TCM comms list from community reports; still undecoded locally |
| `0x4E9` | BCM/GW bridge -> ECM | platform configuration; includes ABS/traction/platform present flags |

## `0x199` Decode Tested Against Local Logs

The following community layout was tested against the local captures and fits well enough to include as provisional DBC signals:

| Signal | Layout | Behavior in local logs |
|---|---|---|
| `TCMTorqueReq3_observed` | `3|12@0+`, scale `0.5`, offset `-848 Nm` | idle/brake inactive value is `1199.5 Nm`; drops to realistic lower requested torque values during upshift windows |
| `TCMTorqueReq3Active_observed` | `4|1@0+` | `0` in idle/brake; becomes `1` during many upshift target windows |
| `TCMTorqueReqRollingCounter_observed` | `6|2@1+` | cycles `0..3` continuously |
| `TCMTorqueReq4_observed` | `19|12@0+`, scale `0.5`, offset `-848 Nm` | mostly inactive `625 Nm`; changes in some manual downshift windows |
| `TCMTorqueReq4Active_observed` | `22|3@0+` | mostly `0`; sometimes active in manual downshift windows |
| `TCMTorqueReq4Protection_observed` | `36|13@0+` | tracks request/counter; must be generated correctly if transmitting |
| `TCMTorqueIncreaseRate_observed` | `63|8@0+` | fixed `255` in local captures |

### Observed Values

| Capture | `Req3` behavior |
|---|---|
| warm idle | fixed `1199.5 Nm`, active `0` |
| brake | fixed `1199.5 Nm`, active `0` |
| normal accel | mostly `1199.5 Nm`; drops as low as `20 Nm` during upshift target windows |
| WOT | mostly `1199.5 Nm`; drops as low as `20 Nm` during upshift target windows |
| cruise | mostly `1199.5 Nm`; drops during multiple shift windows |
| manual | mostly `1199.5 Nm`; `Req4` also changes during downshift/manual windows |

Interpretation: `0x199` is the strongest candidate for the torque-management request your bridge needs to produce.

## Bridge Behavior Proposal

For the first safe implementation:

1. Always transmit baseline `0x199` when no shift torque management is requested:
   - `TCMTorqueReq3Active = 0`
   - `TCMTorqueReq3 = 1199.5 Nm`
   - `TCMTorqueReq4Active = 0`
   - `TCMTorqueReq4 = 625 Nm`
   - rolling counter cycles `0..3`
   - protection value generated correctly
2. During an upshift:
   - set `0x1F5` target gear and upshift direction first
   - assert `TCMTorqueReq3Active`
   - command a conservative low torque request value
   - hold through the clutch handoff
   - release request only after current gear equals target and shift is settled
3. During downshift/rev-match/TCC events:
   - test carefully; local logs suggest `Req4` may matter in manual downshift events, but this is less proven than `Req3`
4. Do not transmit arbitrary `0x199` values without correct rolling/protection behavior.

## What Still Needs Proof

- Exact protection/checksum formula for `TCMTorqueReq4Protection_observed`.
- Whether `Req3` is a max-torque request, torque-reduction request, or one of several torque arbitration lanes.
- `0x19D` decode for engine speed request / blip behavior.
- `0x4C9` role for satisfying ECM U0101 diagnostics.
- Whether the ECM accepts `0x199` torque requests without a full matching set of TCM/BCM keepalive/config frames.
