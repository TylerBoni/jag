# 2007 GM GMLAN DBC Analysis

## Inputs

- CSV captures under `gm_can_bus/` and `gm_can_bus/cold-start/`.
- Matching video/audio task files under `gm_can_bus/video/` and `gm_can_bus/video/audio/`.
- Existing starter DBC: `gm_can_bus/07_denali_l92.dbc`.

The original CSV `Time Stamp` column was `0` for every row. It now contains elapsed seconds inferred from frame order at the observed aggregate rate of 1172.25 frames/second; these are estimates, not capture-clock timestamps.

## High-confidence signals added

| ID | Signal | Evidence |
|---:|---|---|
| `0x0C9` | `EngineSpeed_observed` | D2-D3 big-endian, scale `0.25 rpm`. Warm idle decodes ~580-660 rpm; `rpm-500-inc`, `throttle-blips`, and `wot` rise smoothly to plausible RPM values. |
| `0x0C9` | `AcceleratorPosition_observed` | D5 scales `0-255` to `0-100%`. Idle/brake/AC are 0, normal accel peaks ~29%, throttle blips ~70%, WOT ~100%. |
| `0x0C9` | `BrakePedalDiscrete_observed` | D6 bit0 maps to brake pedal: `0x40` released and `0x41` near spoken Brake on events. |
| `0x199` | `TCMTorqueReq3_observed` | Provisional TCM torque-request decode. Idle/brake are inactive at `1199.5 Nm`; request drops and active bit rises during upshift windows. |
| `0x0F9` | `TransEstimatedTorqueRatioRaw_observed` | D1-D2 big-endian follows gear/ratio state, not output speed. It is `0x07AF` in 1st/drive stationary, `0x00AA` in 6th, `0x7CF0` in reverse, and `0x0000` in park/neutral. |
| `0x0F9` | `TransOutputShaftSpeed_observed` | D4-D5 big-endian is zero while stationary, rises smoothly with motion, and scales as `0.25 rpm/count`. User observation: raw `6000` is about `40 mph`, consistent with about `1500 rpm` before axle/tire conversion. |
| `0x1F5` | `CurrentGear_observed` / `TargetGear_observed` | D1 low nibble is current gear and D2 low nibble is target gear; high nibbles mark shift phase/direction. |
| `0x1F5` | `ShiftLeverPosition_observed` | D4 enumerates PRNDL/manual gear states in the `prndl` capture: Park=1, Reverse=2, Neutral=3, Drive=4, manual gears 9..4..9. |

## Inferred signals needing video review

| ID | Signal | What to verify |
|---:|---|---|
| `0x0C9` | `CruiseActive_observed` | D6 bit7 appears during parts of `cruise.csv`. Confirm whether it means cruise enabled, active, or another cruise state. |
| `0x1E1` | `CruiseSwitchStatus_observed` | Confirmed labels: `0x00` cruise off, `0x40` on/no buttons, `0x54` negative/set, `0x68` plus/resume, `0xC0` cancel. |
| `0x1F5` | `TapUpDownModeRaw_observed` | D3 is `0x10` in manual/tap sections and `0x00` in normal PRNDL/park sections. |
| `0x1F5` | `DriverShiftControlRaw_observed` | D6 is `0x02` in manual/tap sections and `0x00` in normal PRNDL/park sections. |
| `0x1F1` | Power mode bytes | Mostly stable in run; `0x11/0x12` appear during PRNDL/key transitions and need key-state confirmation. |

## Coverage changes

- Expanded `gm_can_bus/07_denali_l92.dbc` from the starter message list to include every observed arbitration ID across the provided captures.
- Updated DBC DLC values to the maximum observed `LEN` per message so `cantools` can decode captures without length errors.
- Left unknown messages as `Observed_XXX` placeholders unless the signal pattern was strongly supported by multiple task captures.
- Added `gm_can_bus/audio_timing_events.md` with the spoken-event mapping and CAN evidence.
- Added `gm_can_bus/transmission_shift_analysis.md` for gear/shift-phase and torque-management candidates.
- Added `gm_can_bus/gm_torque_management_bridge.md` for the non-GM TCM bridge strategy and `0x199` torque-request findings.

## Remaining questions

1. A/C on/off did not produce a stable powertrain-bus byte pattern in `ac.csv`; this may require another bus, longer capture, or more HVAC state changes.
2. Cruise switch protection is solved; if emulating, use D3 low two bits as counter and compute `Protection=(-Status-(D3&3))&0xFF`.
3. `up-down-manual` still lacks matching audio; PRNDL confirms manual mode bits, but tap up/down event timing would help separate target gear from estimated/current gear.
