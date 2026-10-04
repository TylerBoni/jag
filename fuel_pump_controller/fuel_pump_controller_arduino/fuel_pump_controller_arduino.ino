/*
 * Jaguar FPC - Bench/Test Firmware
 * Arduino Nano / ATmega328P
 *
 * A0 = Jaguar low-pressure fuel sensor
 * D2 = E38 fuel pump enable (active HIGH)
 * D3 = Gauge serial TX (5V TTL, 38400 baud)
 * D4 = Gauge serial RX (reserved by SoftwareSerial)
 * D9 = Jaguar FPDM PWM command
 *
 * IMPORTANT:
 * FPDM frequency/electrical interface still needs verification.
 */

#include <SoftwareSerial.h>
#include <avr/wdt.h>

// Capture the reset cause and stop a previously enabled watchdog before setup().
uint8_t resetFlags __attribute__((section(".noinit")));

void captureResetFlags() __attribute__((naked, used, section(".init3")));
void captureResetFlags()
{
  resetFlags = MCUSR;
  MCUSR = 0;
  wdt_disable();
}

const byte PRESSURE_PIN = A0;
const byte ENABLE_PIN   = 2;
const byte GAUGE_TX_PIN = 3;
const byte GAUGE_RX_PIN = 4;
const byte FPDM_PIN     = 9;

const unsigned long USB_BAUD = 115200;
const unsigned long GAUGE_BAUD = 38400;
const uint16_t FPDM_PWM_TOP = (F_CPU / (8UL * 150UL)) - 1;

// Set false when the E38 enable signal is connected.
const bool BYPASS_E38_ENABLE = true;

// Current Jaguar command assumptions
const float FPDM_OFF = 75.0;
// Calibrated from ADC 101 at 0 PSI and ADC 437.9 at 60.5 PSI.
const float PRESSURE_ADC_SLOPE = 0.17958;
const float PRESSURE_ADC_OFFSET = -18.137;
const float PRESSURE_ADC_MIN = 8.0;
const float PRESSURE_ADC_MAX = 600.0;
const float PRESSURE_TARGET_PSI = 58.0;
const float PRESSURE_SOFT_LIMIT_PSI = 59.0;
const float PRESSURE_HARD_LIMIT_PSI = 70.0;
const float FPDM_MIN = 5.0;
const unsigned long CONTROL_INTERVAL_MS = 20;
const float PRESSURE_BUILD_MIN_PSI = 10.0;
const unsigned long PRESSURE_BUILD_TIMEOUT_MS = 5000;

// Conservative PI tune based on the stable P-only bench response.
const float PID_KP = 1.5;
const float PID_KI = 0.25;
const float PID_KD = 0.0;
const float PID_TAU_SECONDS = 0.03;
const float FPDM_RISE_RATE_PER_SECOND = 12.5;

float currentDuty = FPDM_OFF;
float fpdmMax = 50.0;
float pressureADC = 0.0;
uint16_t pressureADCRawMin = 0;
uint16_t pressureADCRawMax = 0;
uint16_t supplyMillivolts = 5000;
float pressurePSI = 0.0;
bool pressureSensorValid = false;
bool overpressureLatched = false;
bool pressureBuildFaultLatched = false;
unsigned long lowPressureSince = 0;
unsigned long lastControlMillis = 0;

float pidProportional = 0.0;
float pidIntegrator = 0.0;
float pidDifferentiator = 0.0;
float pidOutput = 0.0;
float pidPreviousError = 0.0;
float pidPreviousMeasurement = 0.0;
bool pidInitialized = false;

SoftwareSerial gaugeSerial(GAUGE_RX_PIN, GAUGE_TX_PIN);

bool isPumpEnabled()
{
  return BYPASS_E38_ENABLE || digitalRead(ENABLE_PIN) == HIGH;
}

// --------------------------------------------------
// Configure Timer1 / OC1A (D9) for 150 Hz Fast PWM
// --------------------------------------------------

void setupFPDMPWM()
{
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;

  ICR1 = FPDM_PWM_TOP;
  OCR1A = 0;

  // Fast PWM, TOP = ICR1, non-inverting OC1A, prescaler = 8.
  TCCR1A = _BV(COM1A1) | _BV(WGM11);
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11);
}


// --------------------------------------------------
// Set FPDM PWM duty
// --------------------------------------------------

void setFPDM(float duty)
{
  duty = constrain(duty, 0.0, 100.0);

  OCR1A = round(duty * (FPDM_PWM_TOP + 1UL) / 100.0);

  currentDuty = duty;
}

void resetPID()
{
  pidProportional = 0.0;
  pidIntegrator = 0.0;
  pidDifferentiator = 0.0;
  pidOutput = 0.0;
  pidPreviousError = 0.0;
  pidPreviousMeasurement = pressurePSI;
  pidInitialized = false;
  lastControlMillis = millis();
}

float updatePID(
  float setpoint,
  float measurement,
  float periodSeconds,
  float outputMin,
  float outputMax)
{
  float error = setpoint - measurement;

  if (!pidInitialized)
  {
    pidPreviousError = error;
    pidPreviousMeasurement = measurement;
    pidInitialized = true;
  }

  pidProportional = PID_KP * error;

  float previousIntegrator = pidIntegrator;
  pidIntegrator +=
    0.5 * PID_KI * periodSeconds * (error + pidPreviousError);

  pidDifferentiator =
    (-2.0 * PID_KD * (measurement - pidPreviousMeasurement) +
      (2.0 * PID_TAU_SECONDS - periodSeconds) * pidDifferentiator) /
    (2.0 * PID_TAU_SECONDS + periodSeconds);

  pidPreviousError = error;
  pidPreviousMeasurement = measurement;

  float output = pidProportional + pidIntegrator + pidDifferentiator;

  if (output < outputMin || output > outputMax)
  {
    pidIntegrator = previousIntegrator;
  }

  pidOutput = constrain(output, outputMin, outputMax);
  return pidOutput;
}

void handleSerialInput()
{
  while (Serial.available() > 0)
  {
    char command = Serial.read();

    if (command < '0' || command > '5')
    {
      continue;
    }

    fpdmMax = (command - '0') * 10.0;
    resetPID();

    if (fpdmMax == 0.0)
    {
      setFPDM(FPDM_OFF);
    }
    else if (currentDuty != FPDM_OFF && currentDuty > fpdmMax)
    {
      setFPDM(fpdmMax);
    }

    Serial.print(F("{\"type\":\"status\",\"fpdmMax\":"));
    Serial.print(fpdmMax, 0);
    Serial.println(F("}"));
  }
}

uint16_t readSupplyMillivolts()
{
  // Measure the internal 1.1 V reference against AVcc.
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delayMicroseconds(250);
  ADCSRA |= _BV(ADSC);

  while (bit_is_set(ADCSRA, ADSC))
  {
  }

  uint16_t reading = ADC;
  return reading == 0 ? 0 : 1125300UL / reading;
}

void updateSupplyVoltage()
{
  static unsigned long lastReading = 0;
  static bool hasReading = false;
  unsigned long now = millis();

  if (!hasReading || now - lastReading >= 1000)
  {
    supplyMillivolts = readSupplyMillivolts();
    lastReading = now;
    hasReading = true;
  }
}


// --------------------------------------------------
// Read and validate calibrated fuel pressure
// --------------------------------------------------

void updateFuelPressure()
{
  unsigned long total = 0;
  pressureADCRawMin = 1023;
  pressureADCRawMax = 0;

  // Discard the first conversion after measuring the internal reference.
  analogRead(PRESSURE_PIN);

  // Average 16 samples to reduce noise
  for (byte i = 0; i < 16; i++)
  {
    uint16_t sample = analogRead(PRESSURE_PIN);
    total += sample;
    pressureADCRawMin = min(pressureADCRawMin, sample);
    pressureADCRawMax = max(pressureADCRawMax, sample);
  }

  pressureADC = total / 16.0;
  bool readingValid =
    pressureADC >= PRESSURE_ADC_MIN &&
    pressureADC <= PRESSURE_ADC_MAX;

  if (!readingValid)
  {
    pressurePSI = 0.0;

    // Any sensor fault immediately commands the pump OFF.
    setFPDM(FPDM_OFF);
  }
  else
  {
    pressurePSI =
      PRESSURE_ADC_SLOPE * pressureADC + PRESSURE_ADC_OFFSET;
    pressurePSI = max(pressurePSI, 0.0);
  }

  pressureSensorValid = readingValid;
}


// --------------------------------------------------
// Automatic 58 PSI pressure control
// --------------------------------------------------

void updatePumpControl()
{
  if (!isPumpEnabled() || fpdmMax == 0.0)
  {
    setFPDM(FPDM_OFF);
    resetPID();
    overpressureLatched = false;
    pressureBuildFaultLatched = false;
    lowPressureSince = 0;
    return;
  }

  if (!pressureSensorValid ||
      overpressureLatched ||
      pressureBuildFaultLatched)
  {
    setFPDM(FPDM_OFF);
    resetPID();
    return;
  }

  if (pressurePSI >= PRESSURE_HARD_LIMIT_PSI)
  {
    overpressureLatched = true;
    setFPDM(FPDM_OFF);
    resetPID();
    return;
  }

  unsigned long now = millis();

  if (currentDuty == FPDM_OFF)
  {
    setFPDM(FPDM_MIN);
    resetPID();
    lowPressureSince = 0;
    return;
  }

  if (currentDuty >= fpdmMax &&
      pressurePSI < PRESSURE_BUILD_MIN_PSI)
  {
    if (lowPressureSince == 0)
    {
      lowPressureSince = now;
    }
    else if (now - lowPressureSince >= PRESSURE_BUILD_TIMEOUT_MS)
    {
      pressureBuildFaultLatched = true;
      setFPDM(FPDM_OFF);
      resetPID();
      return;
    }
  }
  else
  {
    lowPressureSince = 0;
  }

  // Reduce to minimum early and track the integrator for a bumpless return
  // to closed-loop control. Reserve OFF for disabled/fault conditions.
  if (pressurePSI >= PRESSURE_SOFT_LIMIT_PSI)
  {
    float error = PRESSURE_TARGET_PSI - pressurePSI;
    pidProportional = PID_KP * error;
    pidDifferentiator = 0.0;
    pidIntegrator = constrain(
      FPDM_MIN - pidProportional,
      0.0,
      fpdmMax);
    pidOutput = FPDM_MIN;
    pidPreviousError = error;
    pidPreviousMeasurement = pressurePSI;
    pidInitialized = true;
    lastControlMillis = now;
    setFPDM(FPDM_MIN);
    return;
  }

  unsigned long elapsedMillis = now - lastControlMillis;

  if (elapsedMillis < CONTROL_INTERVAL_MS)
  {
    return;
  }

  lastControlMillis = now;

  float periodSeconds = elapsedMillis / 1000.0;
  float previousIntegrator = pidIntegrator;
  float command = updatePID(
    PRESSURE_TARGET_PSI,
    pressurePSI,
    periodSeconds,
    0.0,
    fpdmMax);

  command = max(command, FPDM_MIN);

  // Limit command increases so delayed pump response cannot create a large
  // pressure overshoot. Reductions remain immediate.
  if (command > currentDuty)
  {
    float maximumIncrease = FPDM_RISE_RATE_PER_SECOND * periodSeconds;
    float maximumCommand = currentDuty + maximumIncrease;

    if (command > maximumCommand)
    {
      // The slew limiter is actuator saturation too; do not integrate while
      // the requested output cannot be applied.
      pidIntegrator = previousIntegrator;
      pidOutput = constrain(
        pidProportional + pidIntegrator + pidDifferentiator,
        0.0,
        fpdmMax);
      command = max(pidOutput, FPDM_MIN);
    }

    command = min(command, maximumCommand);
  }

  setFPDM(command);
}


// --------------------------------------------------
// JSON Lines output
// --------------------------------------------------

void writeTelemetry(Print &output)
{
  output.print(F("{\"type\":\"telemetry\",\"millis\":"));
  output.print(millis());
  output.print(F(",\"adc\":"));
  output.print(pressureADC, 1);
  output.print(F(",\"adcRawMin\":"));
  output.print(pressureADCRawMin);
  output.print(F(",\"adcRawMax\":"));
  output.print(pressureADCRawMax);
  output.print(F(",\"adcValidMin\":"));
  output.print(PRESSURE_ADC_MIN, 0);
  output.print(F(",\"adcValidMax\":"));
  output.print(PRESSURE_ADC_MAX, 0);
  output.print(F(",\"sensorVolts\":"));
  output.print(pressureADC * supplyMillivolts / 1023000.0, 3);
  output.print(F(",\"vccVoltsApprox\":"));
  output.print(supplyMillivolts / 1000.0, 3);
  output.print(F(",\"pressurePsi\":"));
  output.print(pressurePSI, 1);
  output.print(F(",\"sensorValid\":"));
  output.print(pressureSensorValid ? F("true") : F("false"));
  output.print(F(",\"sensorFault\":\""));

  if (pressureADC < PRESSURE_ADC_MIN)
  {
    output.print(F("signal_low"));
  }
  else if (pressureADC > PRESSURE_ADC_MAX)
  {
    output.print(F("signal_high"));
  }
  else
  {
    output.print(F("none"));
  }

  output.print(F("\""));
  output.print(F(",\"d2Raw\":"));
  output.print(digitalRead(ENABLE_PIN) == HIGH ? F("true") : F("false"));
  output.print(F(",\"pumpEnabled\":"));
  output.print(isPumpEnabled() ? F("true") : F("false"));
  output.print(F(",\"e38Bypassed\":"));
  output.print(BYPASS_E38_ENABLE ? F("true") : F("false"));
  output.print(F(",\"fpdmMax\":"));
  output.print(fpdmMax, 0);
  output.print(F(",\"overpressureLatched\":"));
  output.print(overpressureLatched ? F("true") : F("false"));
  output.print(F(",\"pressureBuildFault\":"));
  output.print(pressureBuildFaultLatched ? F("true") : F("false"));
  output.print(F(",\"fpdmDuty\":"));
  output.print(currentDuty, 1);
  output.print(F(",\"pidKp\":"));
  output.print(PID_KP, 3);
  output.print(F(",\"pidKi\":"));
  output.print(PID_KI, 3);
  output.print(F(",\"pidKd\":"));
  output.print(PID_KD, 3);
  output.print(F(",\"fpdmRiseRate\":"));
  output.print(FPDM_RISE_RATE_PER_SECOND, 1);
  output.print(F(",\"pidP\":"));
  output.print(pidProportional, 2);
  output.print(F(",\"pidI\":"));
  output.print(pidIntegrator, 2);
  output.print(F(",\"pidD\":"));
  output.print(pidDifferentiator, 2);
  output.print(F(",\"pidOutput\":"));
  output.print(pidOutput, 2);
  output.println(F("}"));
}

// --------------------------------------------------
// Setup
// --------------------------------------------------

void setup()
{
  pinMode(PRESSURE_PIN, INPUT);
  pinMode(ENABLE_PIN, INPUT);
  pinMode(FPDM_PIN, OUTPUT);

  setupFPDMPWM();

  // Start with pump commanded OFF
  setFPDM(FPDM_OFF);

  Serial.begin(USB_BAUD);
  gaugeSerial.begin(GAUGE_BAUD);

  delay(500);

  Serial.println(
    F("{\"type\":\"status\",\"status\":\"ready\","
      "\"control\":\"auto\",\"targetPsi\":58.0,\"hardLimitPsi\":70.0,"
      "\"fpdmMax\":0,\"fpdmCommand\":\"0-5\","
      "\"usbBaud\":115200,\"gaugeBaud\":38400,\"gaugeTxPin\":3}")
  );

  // Reboot if the main loop stops completing for two seconds.
  wdt_reset();
  wdt_enable(WDTO_2S);
}


// --------------------------------------------------
// Main loop
// --------------------------------------------------

void loop()
{
  handleSerialInput();
  updateSupplyVoltage();
  updateFuelPressure();
  updatePumpControl();


  // --------------------------
  // Print sensor data
  // --------------------------

  static unsigned long lastPrint = 0;

  if (millis() - lastPrint >= 250)
  {
    lastPrint = millis();

    writeTelemetry(Serial);
    writeTelemetry(gaugeSerial);
  }

  wdt_reset();
}