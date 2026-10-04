# Cruise Switch Analysis

Source files:

- `gm_can_bus/cruise_timeline.csv`
- `gm_can_bus/cruise.csv`
- `gm_can_bus/07_denali_l92.dbc`

## Frame Layout

Observed `0x1E1` is three bytes:

| Byte | DBC signal | Meaning |
|---:|---|---|
| D1 | `CruiseSwitchStatus_observed` | switch status; labels confirmed by user/video review |
| D2 | `CruiseSwitchProtection_observed` | protection/check byte |
| D3 bits 0-1 | `CruiseSwitchAliveCounter_observed` | 2-bit alive counter |
| D3 bit 2 | `CruiseSwitchByte3Bit2_observed` | extra mode/status bit seen in key/cold-start captures |

## Protection Formula

The protection byte is exactly:

```text
CruiseSwitchProtection = (-CruiseSwitchStatus - (D3 & 0x03)) & 0xFF
```

Equivalent:

```text
(Status + Protection + (D3 & 0x03)) & 0xFF == 0
```

This matched all raw `0x1E1` frames across the raw CAN captures, including key/cold-start captures where D3 is `0x04..0x07`.

## D3 Is Not a 0-255 Counter

Across the raw logs, D3 only appears as `0x00..0x07`.

- Normal running captures use `0x00..0x03`.
- `Key-on-key-off-cold.csv` uses `0x04..0x07`.
- `cold-start.csv` contains both `0x00..0x03` and `0x04..0x07`.

The low two bits always increment modulo 4. Bit2 can be set, but the protection byte ignores it.

## Examples

| Status | Counter | Protection |
|---:|---:|---:|
| `0x00` cruise off | `0` | `0x00` |
| `0x00` cruise off | `1` | `0xFF` |
| `0x00` cruise off | `4` (`low2=0`) | `0x00` |
| `0x00` cruise off | `5` (`low2=1`) | `0xFF` |
| `0x00` cruise off | `6` (`low2=2`) | `0xFE` |
| `0x00` cruise off | `7` (`low2=3`) | `0xFD` |
| `0x40` cruise on / no buttons | `0` | `0xC0` |
| `0x40` cruise on / no buttons | `1` | `0xBF` |
| `0x40` cruise on / no buttons | `2` | `0xBE` |
| `0x40` cruise on / no buttons | `3` | `0xBD` |
| `0x54` negative/set button down | `0` | `0xAC` |
| `0x68` plus/resume button down | `0` | `0x98` |
| `0xC0` cancel button down | `0` | `0x40` |

## Status Runs In Timeline

The timeline shows these non-released status windows:

| Time range | Status |
|---:|---:|
| `17.709-20.114s` | `0x00` |
| `22.993-23.163s` | `0x54` |
| `26.605-26.779s` | `0x54` |
| `27.696-27.853s` | `0x54` |
| `31.916-32.092s` | `0x68` |
| `32.892-33.049s` | `0x68` |
| `34.009-34.181s` | `0x68` |
| `38.306-38.535s` | `0xC0` |
| `43.875-44.102s` | `0x68` |
| `49.090-53.517s` | `0x00` |
| `56.142-56.314s` | `0x54` |

Button labels were confirmed by user/video review:

| Status | Meaning |
|---:|---|
| `0x00` | cruise off completely |
| `0x40` | cruise on, no buttons pressed |
| `0x54` | negative/set button down |
| `0x68` | plus/resume button down |
| `0xC0` | cancel button down |

## Emulator Use

When emitting `0x1E1`:

1. Pick a `CruiseSwitchStatus_observed` byte.
2. Increment `CruiseSwitchAliveCounter_observed` modulo 4 in D3 bits 0-1.
3. Set D3 bit2 only if intentionally emulating the key/cold-start mode where status is `0x00`; otherwise leave it clear.
4. Compute `CruiseSwitchProtection_observed = (-status - (d3 & 0x03)) & 0xFF`.
5. Transmit `[status, protection, d3]`.
