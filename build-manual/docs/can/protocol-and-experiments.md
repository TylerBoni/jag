# CAN protocol and experiments

This repository includes [can_engineering](../../../can_engineering/) and [CAN_Triple](../../../CAN_Triple/) projects. These are source artifacts, not automatically validated vehicle-level specifications. Archive relevant commit SHAs before describing a reproducible firmware build.

## Recorded IDs and their limits

| ID | Context | Status |
| --- | --- | --- |
| `0x1F1` | E38 cold-start replay experiment; 56 frames acknowledged by transmit interface | TESTED TX, ECM interpretation OPEN |
| `0x1E1` | Cruise switch protection, two-bit counter discussed | EXPERIMENTAL / details not verified |
| `0x199` | Torque-reduction experiment | EXPERIMENTAL |
| `0x0D0` | Throttle position interpretation discussed | EXPERIMENTAL |

## Reproducible transmit record

Reported command:

```bash
python3 -u scripts/replay_cold_start.py \
  e38_start_tests/early_8e.csv \
  --transmit --ids 1F1 \
  --port /dev/cu.usbmodem102 --verbose
```

Observed tool output included:

```text
loaded 56 data frames + end marker
selected IDs: 1F1:56
acknowledged 56/56 data frames
REPLAY DONE sent=56 drop=0
complete: 56 data frames sent; board reported DONE
```

**This proves the interface reported successful transmission of selected frames, not the ECM's response or a necessary/sufficient start command.** The capture contents and timing must be preserved before claiming an exact payload.

## Capture specification

Every captured/replayed record must state: bus name, physical connector pins, CAN bitrate, 11/29-bit ID, timestamp, data length, exact 8 data bytes or CAN-FD equivalent, direction, power/ignition state, engine state, ECU OS/tune ID, replay source hash, hardware transceiver, firmware commit and an independent receive trace. Note checksum/counter rules only after validated differential captures.

## Safety

Use isolated/bench networks for exploratory transmission whenever possible. Transmitting arbitrary IDs on a live vehicle bus can trigger engine torque commands, unsafe transmission states, ABS/ESC faults or starter activity. Do not replay unknown frames while driveline motion is possible.
