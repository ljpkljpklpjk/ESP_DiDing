#include <Arduino.h>
#include <ArduinoJson.h>
#include <SPI.h>

#include "ADS1220Module.h"
#include "DS18B20Module.h"
#include "MotorPWMControl.h"
#include "PeristalticPumpControl.h"

// ---------------- ADS1220 ----------------
static ADS1220Pins kAdsPins = {
    .cs = 21,
    .drdy = 15,
    .sclk = 4,
    .miso = 13,
    .mosi = 14,
};

static constexpr float ENV_TEMP_C = 25.0f;
static PHCalibrationTwoPoint kPhCal = {
    .ph1 = 10.00f,
    .v1 = 0.46935f,
    .ph2 = 6.86f,
    .v2 = 0.93646f,
    .tempC = ENV_TEMP_C,
};

// ---------------- PWM + DFR0523 Pump ----------------
static constexpr uint8_t PWM1_PIN = 5;
static constexpr uint8_t PWM1_CHANNEL = 0;
static constexpr uint32_t PWM_FREQ_HZ = 20000;
static constexpr uint8_t PWM_RES_BITS = 10;
static constexpr uint8_t PUMP_SIGNAL_PIN = 6;
static constexpr uint8_t PUMP_PWM_CHANNEL = 1;
static constexpr uint32_t PUMP_PPM_FREQ_HZ = 500;
static constexpr uint8_t PUMP_PWM_RES_BITS = 10;
static constexpr bool SERIAL_DEBUG_TEXT = false;
static constexpr uint32_t TELEMETRY_INTERVAL_MS = 1000;
static constexpr size_t SERIAL_RX_BUF_SIZE = 256;
static constexpr uint8_t DS18B20_PIN = 2;

static SPIClass adsSpi(FSPI);
static ADS1220Module ads(adsSpi, kAdsPins);
static DS18B20Module ds18b20(DS18B20_PIN);
static MotorPWMControl pwm1(PWM1_PIN, PWM1_CHANNEL, PWM_FREQ_HZ, PWM_RES_BITS);
static PeristalticPumpControl pump(PUMP_SIGNAL_PIN, PUMP_PWM_CHANNEL,
                                   PUMP_PPM_FREQ_HZ, PUMP_PWM_RES_BITS);

static float gPwm1Percent = 0.0f;
static float gPumpPercent = 0.0f;

static uint32_t gLastSampleMs = 0;
static float gLastVoltage = NAN;
static float gLastPh = NAN;
static uint32_t gLastTempSampleMs = 0;
static float gLastTempC = NAN;
static uint32_t gLastTelemetryMs = 0;
static char gSerialRxBuf[SERIAL_RX_BUF_SIZE];
static size_t gSerialRxLen = 0;

static float clampPercent(float p) {
  if (p < 0.0f) return 0.0f;
  if (p > 100.0f) return 100.0f;
  return p;
}

static void setPwm1Percent(float percent) {
  gPwm1Percent = clampPercent(percent);
  pwm1.setSpeedPercent(gPwm1Percent);
}

static void setPumpPercent(float percent) {
  gPumpPercent = clampPercent(percent);
  pump.setSpeedPercent(gPumpPercent);
}

static void sendJsonFloatOrNull(JsonDocument &doc, const char *key, float value) {
  if (isnan(value) || isinf(value)) {
    doc[key] = nullptr;
  } else {
    doc[key] = value;
  }
}

static void sendSerialAck() {
  JsonDocument doc;
  doc["type"] = "ack";
  doc["pwm1_percent"] = gPwm1Percent;
  doc["pump_percent"] = gPumpPercent;
  serializeJson(doc, Serial);
  Serial.println();
}

static void sendSerialError(const char *code) {
  JsonDocument doc;
  doc["type"] = "error";
  doc["code"] = code;
  serializeJson(doc, Serial);
  Serial.println();
}

static void handleSerialJsonLine(const char *line) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    sendSerialError("invalid_json");
    return;
  }

  bool applied = false;
  if (doc["pwm1_percent"].is<float>()) {
    setPwm1Percent(doc["pwm1_percent"].as<float>());
    applied = true;
  }
  if (doc["pump_percent"].is<float>()) {
    setPumpPercent(doc["pump_percent"].as<float>());
    applied = true;
  }

  if (!applied) {
    sendSerialError("no_valid_setpoints");
    return;
  }

  sendSerialAck();
}

static void processSerialInput() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      gSerialRxBuf[gSerialRxLen] = '\0';
      if (gSerialRxLen > 0) {
        handleSerialJsonLine(gSerialRxBuf);
      }
      gSerialRxLen = 0;
      continue;
    }
    if (gSerialRxLen < SERIAL_RX_BUF_SIZE - 1) {
      gSerialRxBuf[gSerialRxLen++] = c;
    } else {
      gSerialRxLen = 0;
      sendSerialError("line_too_long");
    }
  }
}

static void sendTelemetryJson() {
  JsonDocument doc;
  doc["type"] = "telemetry";
  sendJsonFloatOrNull(doc, "ph", gLastPh);
  sendJsonFloatOrNull(doc, "temperature_c", gLastTempC);
  doc["pwm1_percent"] = gPwm1Percent;
  doc["pump_percent"] = gPumpPercent;
  serializeJson(doc, Serial);
  Serial.println();
}

static void updateSerialTelemetry() {
  const uint32_t now = millis();
  if (now - gLastTelemetryMs < TELEMETRY_INTERVAL_MS) {
    return;
  }
  gLastTelemetryMs = now;
  sendTelemetryJson();
}

static void updatePhReading() {
  const uint32_t now = millis();
  if (now - gLastSampleMs < 500) {
    return;
  }
  gLastSampleMs = now;

  const float v = ads.readVoltage(ADS1220Module::AIN0_AIN1);
  if (isnan(v)) {
    gLastVoltage = NAN;
    gLastPh = NAN;
    if (SERIAL_DEBUG_TEXT) {
      Serial.println("ADS1220 timeout (check DRDY pin/wiring)");
    }
    return;
  }

  gLastVoltage = v;
  gLastPh = ads.voltageToPH(v);

  if (SERIAL_DEBUG_TEXT) {
    Serial.printf("PH voltage=%.6f V, pH=%.3f, PWM1=%.1f%%, Pump=%.1f%%\n",
                  gLastVoltage, gLastPh, gPwm1Percent, gPumpPercent);
  }
}

static void updateTemperatureReading() {
  const uint32_t now = millis();
  if (now - gLastTempSampleMs < 1000) {
    return;
  }
  gLastTempSampleMs = now;

  gLastTempC = ds18b20.readCelsius();
  if (isnan(gLastTempC)) {
    if (SERIAL_DEBUG_TEXT) {
      Serial.println("DS18B20 read failed");
    }
    return;
  }

  if (SERIAL_DEBUG_TEXT) {
    Serial.printf("Temp: %.2f C\n", gLastTempC);
  }
}

void setup() {
  Serial.begin(115200);

  if (!pwm1.begin() || !pump.begin()) {
    sendSerialError("pwm_pump_init_failed");
    while (true) {
      delay(1000);
    }
  }
  setPwm1Percent(0.0f);
  setPumpPercent(0.0f);

  ads.begin();
  ads.setPHCalibration(kPhCal);
  const bool dsReady = ds18b20.begin();

  if (SERIAL_DEBUG_TEXT) {
    Serial.printf("ADS1220 cfg: R0=0x%02X R1=0x%02X R2=0x%02X R3=0x%02X\n",
                  ads.readRegister(0), ads.readRegister(1), ads.readRegister(2), ads.readRegister(3));
    Serial.printf("PH calib: slope=%.6f intercept=%.6f\n", ads.getPHSlope(), ads.getPHIntercept());
    Serial.printf("DS18B20 init: %s (pin=%u)\n", dsReady ? "OK" : "FAIL", DS18B20_PIN);
  }
}

void loop() {
  processSerialInput();
  updatePhReading();
  updateTemperatureReading();
  updateSerialTelemetry();
  delay(5);
}
