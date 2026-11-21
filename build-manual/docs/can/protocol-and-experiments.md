# CAN bus

I'm using an STM32/CAN Triple setup to investigate the Jaguar electronics and GM E38 integration.

Code: [CAN engineering tools](https://github.com/TylerBoni/jag/tree/master/can_engineering) · [STM32 firmware](https://github.com/TylerBoni/jag/tree/master/CAN_Triple)

## CAN IDs

| ID | What I've been investigating |
| --- | --- |
| `0x1F1` | E38 start-related replay; 56 frames successfully transmitted |
| `0x1E1` | Cruise-switch counter (experimental) |
| `0x199` | Torque-reduction message (experimental) |
| `0x0D0` | Throttle-position interpretation (experimental) |

The last three aren't confirmed decoded message definitions.

## Start replay test

I ran:

```bash
python3 -u scripts/replay_cold_start.py \
  e38_start_tests/early_8e.csv \
  --transmit --ids 1F1 \
  --port /dev/cu.usbmodem102 --verbose
```

Result:

```text
loaded 56 data frames + end marker
selected IDs: 1F1:56
acknowledged 56/56 data frames
REPLAY DONE sent=56 drop=0
complete: 56 data frames sent; board reported DONE
```

This confirms that the STM32 sent the frames without reported drops. It **doesn't** by itself confirm how the E38 responded.

## What a complete message write-up needs

For each confirmed message I'll include the CAN bus and speed, ID, payload, timing, counters/checksums, capture file, firmware revision and observed result. I won't publish guessed payload bytes as a working command.

**Safety:** Replay unknown messages on a bench or isolated bus. Starter, transmission and torque-control messages can have unintended effects on a live vehicle.
