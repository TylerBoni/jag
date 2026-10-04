# Audio Timing Events

These are the spoken timestamps supplied for the local audio files. The CSV timestamps are elapsed seconds inferred from frame order at 1172.25 frames/second, not capture-clock timestamps.

## Brake Pedal

Source: `brake-pedal.m4a` with `gm_can_bus/brake.csv`.

| Audio time | Event | CAN evidence |
|---:|---|---|
| `0:01` | Start / brake off | `0x0C9` D6 is `0x40`. |
| `0:07` | Brake on | `0x0C9` D6 is `0x41`. |
| `0:12` | Brake off | transition window, `0x0C9` D6 returns toward `0x40`. |
| `0:16` | Brake on | `0x0C9` D6 is predominantly `0x41`. |
| `0:20` | Brake off | `0x0C9` D6 is `0x40`. |

Conclusion: `0x0C9` D6 bit0 is brake pedal discrete.

## PRNDL

Source: `prndl.m4a` with `gm_can_bus/prndl.csv`.

The clearest direct sequence is `0x1F5`, compressed by payload run:

| Approx CAN time | Payload | Interpretation |
|---:|---|---|
| `0.00-8.05s` | `0F 0F 00 01 00 00` | Park |
| `8.09-11.71s` | `0E 0E 00 02 00 00` | Reverse |
| `11.71-14.18s` | `0D 0D 00 03 00 00` | Neutral |
| `14.21-16.94s` | `01 01 00 04 00 00` | Drive |
| `16.94-31.19s` | `01 01 10 09..04..09 00 02` | Manual/tap mode, D4 is selected/manual gear |
| `31.19-33.37s` | `01 01 00 04 00 00` | Drive |
| `33.40-35.55s` | `0D 0D 00 03 00 00` | Neutral |
| `35.58-37.89s` | `0E 0E 00 02 00 00` | Reverse |
| `37.89-44.60s` | `0F 0F 00 01 00 00` | Park |

Conclusion: `0x1F5` D4 is the strongest PRNDL/manual gear enum. D3 `0x10` and D6 `0x02` mark manual/tap mode.

## Cruise

Source: `cruise.m4a` with `gm_can_bus/cruise.csv`.

`0x1E1` D1 is the switch-status byte; D2 is a protection/complement byte with a rolling component, and D3 rolls `0..3`.

| Observed D1 | Confirmed label |
|---:|---|---|
| `0x00` | cruise off completely |
| `0x40` | cruise on, no buttons pressed |
| `0x54` | negative/set button down |
| `0x68` | plus/resume button down |
| `0xC0` | cancel button down |

The protection byte is derived from this status and the low two bits of D3.

## A/C

Source: `ac.m4a` with `gm_can_bus/ac.csv`.

Spoken events:

| Audio time | Event |
|---:|---|
| `0:01` | A/C off / start |
| `0:08` | A/C on |
| `0:15` | A/C off |

No stable powertrain-bus byte pattern separated the on/off windows in the provided capture. The A/C compressor/config contents listed for `0x4E9` may require a different bus, a longer capture, or more HVAC state changes.

## RPM Steps

Source: `rpm-500-inc.m4a` with `gm_can_bus/rpm-500-inc.csv`.

Spoken RPM steps confirm `0x0C9` D2-D3 big-endian with scale `0.25 rpm`. The signal is smooth and plausible across warm idle, blips, 500-step capture, and WOT.
