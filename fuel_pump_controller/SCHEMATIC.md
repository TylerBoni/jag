# Jaguar Fuel Pump Controller Wiring

## System schematic

```text
                       VEHICLE 12 V
                            |
                 Automotive 5 V regulator
                  (fused, protected supply)
                            |
                            +---------------------+
                            |                     |
                         Nano 5V          Pressure sensor
                                      VREFA (brown/blue, pin 3)

Vehicle ground -------------+---------------------+
                            |                     |
                         Nano GND      RTN (white/violet, pin 1)

Sensor SIG (green/white, pin 2) ------------- Nano A0
                            |
                          100 kΩ
                            |
                           GND

E38 pump enable ---- Protected 12 V-to-5 V input ---- Nano D2

Nano D9 ---- Verified FPDM electrical interface ---- FPDM PWM command

Nano D3 TX -------- Gauge/controller RX
Nano GND ---------- Gauge/controller GND

Nano USB ---------- USB host (115200 baud, JSON Lines)
```

## Nano connections

| Nano pin | Connection | Notes |
|---|---|---|
| `5V` | Sensor VREFA pin 3 | Brown/blue wire; use a clean regulated 5 V supply |
| `GND` | Sensor RTN pin 1 | White/violet wire; common sensor and controller ground |
| `A0` | Sensor SIG pin 2 | Green/white wire; add 100 kΩ pull-down to GND |
| `D2` | E38 pump enable | Active HIGH; requires automotive input protection; currently bypassed in firmware |
| `D3` | Gauge serial RX | 38400 baud, 5 V TTL JSON Lines output |
| `D4` | Reserved serial RX | Leave disconnected |
| `D9` | FPDM PWM command | 150 Hz; electrical interface must be verified |
| `USB` | Host computer | 115200 baud JSON Lines output |

## Serial telemetry

```json
{"type":"telemetry","millis":1250,"adc":180.2,"adcRawMin":179,"adcRawMax":181,"adcValidMin":8,"adcValidMax":600,"sensorVolts":0.881,"vccVoltsApprox":5.002,"pressurePsi":29.6,"sensorValid":true,"sensorFault":"none","d2Raw":false,"pumpEnabled":true,"e38Bypassed":true,"fpdmMax":10,"overpressureLatched":false,"pressureBuildFault":false,"fpdmDuty":8.1,"pidKp":1.500,"pidKi":0.250,"pidKd":0.000,"fpdmRiseRate":12.5,"pidP":42.60,"pidI":0.50,"pidD":0.00,"pidOutput":10.00}
```

For sensor troubleshooting:

- `signal_low`: A0 is below ADC 8 (approximately 0.04 V); check sensor 5 V, ground, signal continuity, and pin order.
- `signal_high`: A0 is above ADC 600 (approximately 2.93 V at 5 V VCC); check for a signal short to 5 V or an incorrect sensor calibration range.
- A large difference between `adcRawMin` and `adcRawMax` indicates noise or an intermittent connection.
- `vccVoltsApprox` reports the Nano supply measured against its internal reference.
- Pressure calibration uses ADC 101 at 0 PSI and ADC 437.9 at 60.5 PSI.

## Serial FPDM limit

The controller starts with the pump commanded off. In the USB serial monitor at 115200 baud, send one digit to set the maximum FPDM duty:

- `0`: off
- `1`: 10%
- `2`: 20%
- `3`: 30%
- `4`: 40%
- `5`: 50%

Line endings are ignored. The automatic pressure controller remains active and will ramp only as high as the selected limit.

## Pressure PID

The 20 ms pressure loop supports proportional control, trapezoidal integration,
filtered derivative-on-measurement, and output-clamp anti-windup. Testing of
the initially scaled reference gains produced repeated overshoot and reached
the 70 PSI hard limit. A stable P-only test then settled around 52 PSI without
oscillation, so a small integral term is now enabled:

- `Kp = 1.500` command-percent/PSI
- `Ki = 0.250` command-percent/(PSI·second)
- `Kd = 0.000`
- Derivative filter time constant: `0.030` seconds
- Maximum command increase: `12.5` percentage points/second

The PID output is limited by the serially selected `fpdmMax`. The active FPDM
command has a 5% floor; command reductions are immediate, while increases are
slew-limited. Integration is suspended while that rise limit is active. At the
59 PSI soft limit, the controller tracks the integrator to the 5% command for
a bumpless return instead of discarding all controller state. The 75% command
remains the disabled/fault command. PID state is cleared when control is
disabled, a fault occurs, or the operator changes `fpdmMax`.

## Safety notes

- Set `BYPASS_E38_ENABLE` to `false` before relying on the E38 enable input. While it is `true`, valid pressure input can run the pump without an E38 signal.
- Do not connect vehicle 12 V directly to any Nano pin.
- Do not power the Nano directly from unprotected vehicle 12 V.
- Verify whether the FPDM command requires 5 V logic, open-drain drive, inversion, or a 12 V interface before connecting D9.
- Use a level shifter or divider from D3 when the receiving gauge uses 3.3 V logic.
- The 100 kΩ A0 pull-down makes a disconnected pressure-sensor signal fail low.
- Use a mechanical fuel-pressure relief device; software shutdown is not overpressure protection by itself.

## MCU safety configuration

- The firmware enables the ATmega328P watchdog with a 2-second timeout. A stalled main loop automatically resets the MCU.
- Program the ATmega328P brown-out detector for 4.3 V (`BODLEVEL=100`, extended fuse `0xFC`). A 16 MHz ATmega328P is not rated to run across the full voltage range allowed by the Nano's usual 2.7 V brown-out setting.
- Set the brown-out fuse with an ISP programmer, then verify it by reading the extended fuse. Normal sketch uploads do not change fuse settings; burning a bootloader may restore the board package's default.
- Fuse writes can make the MCU unbootable if programmed incorrectly. Preserve the low and high fuse values and change only the extended fuse.
