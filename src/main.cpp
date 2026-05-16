#include <Arduino.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <ArduinoOTA.h>
#include <SPI.h>
#include <WiFi.h>

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
static constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 10000;
static constexpr size_t SERIAL_RX_BUF_SIZE = 320;
static constexpr size_t SERIAL_BYTES_PER_LOOP = 48;
static constexpr uint32_t OTA_HANDLE_INTERVAL_MS = 10;
static constexpr uint8_t DS18B20_PIN = 2;

static const char *WIFI_SSID = "Lab807_2.4G";
static const char *WIFI_PASSWORD = "lab80700";
static const char *OTA_HOSTNAME = "esp-diding";
static const char *OTA_PASSWORD = "lab80700";

// ---------------- Lead screw slider ----------------
static constexpr uint8_t SLIDER_STEP_PIN = 10;
static constexpr uint8_t SLIDER_DIR_PIN = 11;
static constexpr uint8_t SLIDER_ENABLE_PIN = 12;
static constexpr bool SLIDER_ENABLE_ACTIVE_LOW = true;
static constexpr float SLIDER_DEFAULT_SPEED = 1000.0f;
static constexpr float SLIDER_DEFAULT_ACCEL = 500.0f;
static constexpr float SLIDER_MIN_SPEED = 1.0f;
static constexpr float SLIDER_MAX_SPEED = 5000.0f;
static constexpr long SLIDER_CONTINUOUS_TRAVEL = 1000000000L;
static constexpr float SLIDER_MOTOR_FULL_STEPS_PER_REV = 200.0f;
static constexpr float SLIDER_MICROSTEPS = 16.0f;
static constexpr float SLIDER_LEAD_SCREW_PITCH_MM = 2.0f;
static constexpr float SLIDER_STEPS_PER_MM =
    SLIDER_MOTOR_FULL_STEPS_PER_REV * SLIDER_MICROSTEPS /
    SLIDER_LEAD_SCREW_PITCH_MM;

static SPIClass adsSpi(FSPI);
static ADS1220Module ads(adsSpi, kAdsPins);
static DS18B20Module ds18b20(DS18B20_PIN);
static MotorPWMControl pwm1(PWM1_PIN, PWM1_CHANNEL, PWM_FREQ_HZ, PWM_RES_BITS);
static PeristalticPumpControl pump(PUMP_SIGNAL_PIN, PUMP_PWM_CHANNEL,
                                   PUMP_PPM_FREQ_HZ, PUMP_PWM_RES_BITS);
static AccelStepper sliderStepper(AccelStepper::DRIVER, SLIDER_STEP_PIN,
                                  SLIDER_DIR_PIN);

static float gPwm1Percent = 0.0f;
static float gPumpPercent = 0.0f;
static bool gSliderEnabled = false;
static float gSliderSpeed = SLIDER_DEFAULT_SPEED;
static bool gSliderMoveActive = false;
static long gSliderMoveCommandId = -1;
static bool gSliderStopActive = false;
static long gSliderStopCommandId = -1;

static uint32_t gLastSampleMs = 0;
static float gLastVoltage = NAN;
static float gLastPh = NAN;
static uint32_t gLastTempSampleMs = 0;
static float gLastTempC = NAN;
static uint32_t gLastTelemetryMs = 0;
static uint32_t gLastWifiRetryMs = 0;
static uint32_t gLastOtaHandleMs = 0;
static bool gOtaReady = false;
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

static void setSliderEnabled(bool enabled) {
  gSliderEnabled = enabled;
  digitalWrite(SLIDER_ENABLE_PIN, enabled == SLIDER_ENABLE_ACTIVE_LOW ? LOW : HIGH);
}

static void sendJsonFloatOrNull(JsonDocument &doc, const char *key, float value) {
  if (isnan(value) || isinf(value)) {
    doc[key] = nullptr;
  } else {
    doc[key] = value;
  }
}

static void sendJson(JsonDocument &doc) {
  serializeJson(doc, Serial);
  Serial.println();
}

static void sendSerialAck(long id = -1) {
  JsonDocument doc;
  doc["type"] = "ack";
  if (id >= 0) doc["id"] = id;
  doc["ok"] = true;
  doc["pwm1_percent"] = gPwm1Percent;
  doc["pump_percent"] = gPumpPercent;
  sendJson(doc);
}

static void sendSerialDone(long id, bool ok) {
  JsonDocument doc;
  doc["type"] = "done";
  if (id >= 0) doc["id"] = id;
  doc["ok"] = ok;
  sendJson(doc);
}

static void sendSerialError(const char *code, long id = -1) {
  JsonDocument doc;
  doc["type"] = "error";
  if (id >= 0) doc["id"] = id;
  doc["code"] = code;
  sendJson(doc);
}

static void clearSliderMove(bool sendInterrupted) {
  if (sendInterrupted && gSliderMoveActive) {
    sendSerialDone(gSliderMoveCommandId, false);
  }
  gSliderMoveActive = false;
  gSliderMoveCommandId = -1;
  gSliderStopActive = false;
  gSliderStopCommandId = -1;
}

static void addSliderTelemetry(JsonDocument &doc) {
  JsonObject slider = doc["slider"].to<JsonObject>();
  slider["pos"] = sliderStepper.currentPosition();
  slider["target"] = sliderStepper.targetPosition();
  slider["distance"] = sliderStepper.distanceToGo();
  slider["moving"] = sliderStepper.distanceToGo() != 0;
  slider["enabled"] = gSliderEnabled;
  slider["speed"] = gSliderSpeed;
  slider["steps_per_mm"] = SLIDER_STEPS_PER_MM;
}

static void sendTelemetryJson() {
  JsonDocument doc;
  doc["type"] = "telemetry";
  doc["ms"] = millis();
  sendJsonFloatOrNull(doc, "ph", gLastPh);
  sendJsonFloatOrNull(doc, "voltage", gLastVoltage);
  sendJsonFloatOrNull(doc, "temperature_c", gLastTempC);
  doc["pwm1_percent"] = gPwm1Percent;
  doc["pump_percent"] = gPumpPercent;
  doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "";
  doc["ota_ready"] = gOtaReady;
  addSliderTelemetry(doc);
  sendJson(doc);
}

static void runSlider() {
  if (gSliderEnabled) {
    sliderStepper.run();
  }
}

static bool sliderBusy() {
  return gSliderMoveActive || gSliderStopActive || sliderStepper.distanceToGo() != 0;
}

static void updateSerialTelemetry() {
  if (sliderBusy()) {
    return;
  }
  const uint32_t now = millis();
  if (now - gLastTelemetryMs < TELEMETRY_INTERVAL_MS) {
    return;
  }
  gLastTelemetryMs = now;
  sendTelemetryJson();
}

static bool jsonHasNumber(JsonDocument &doc, const char *key) {
  return doc[key].is<float>() || doc[key].is<int>() || doc[key].is<long>();
}

static bool readFloatField(JsonDocument &doc, const char *key, float &out,
                           long id, const char *errorCode) {
  if (!jsonHasNumber(doc, key)) {
    sendSerialError(errorCode, id);
    return false;
  }
  out = doc[key].as<float>();
  return true;
}

static void sliderMoveSteps(long steps, long id) {
  setSliderEnabled(true);
  clearSliderMove(true);
  sliderStepper.move(steps);
  gSliderMoveActive = true;
  gSliderMoveCommandId = id;
}

static void sliderMoveMm(float mm, long id) {
  sliderMoveSteps(lround(mm * SLIDER_STEPS_PER_MM), id);
}

static bool sliderMoveTime(float mm, float sec, long id) {
  if (sec <= 0.0f) {
    sendSerialError("invalid_slider_time", id);
    return false;
  }

  const long steps = lround(mm * SLIDER_STEPS_PER_MM);
  const float speed = fabs(static_cast<float>(steps)) / sec;
  if (speed < SLIDER_MIN_SPEED || speed > SLIDER_MAX_SPEED) {
    sendSerialError("slider_speed_out_of_range", id);
    return false;
  }

  gSliderSpeed = speed;
  sliderStepper.setMaxSpeed(gSliderSpeed);
  sliderMoveSteps(steps, id);
  return true;
}

static void sliderMoveContinuous(int direction) {
  setSliderEnabled(true);
  clearSliderMove(true);
  sliderStepper.setMaxSpeed(gSliderSpeed);
  sliderStepper.moveTo(sliderStepper.currentPosition() +
                       direction * SLIDER_CONTINUOUS_TRAVEL);
}

static void sliderHalt() {
  sliderStepper.setCurrentPosition(sliderStepper.currentPosition());
  sliderStepper.moveTo(sliderStepper.currentPosition());
  clearSliderMove(true);
}

static void emergencyStop() {
  sliderHalt();
  setSliderEnabled(false);
  setPwm1Percent(0.0f);
  setPumpPercent(0.0f);
}

static void sendOtaStatus(const char *event) {
  JsonDocument doc;
  doc["type"] = "ota";
  doc["event"] = event;
  doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "";
  sendJson(doc);
}

static void setupOta() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.onStart([]() {
    emergencyStop();
    sendOtaStatus("start");
  });
  ArduinoOTA.onEnd([]() {
    sendOtaStatus("end");
  });
  ArduinoOTA.onError([](ota_error_t error) {
    JsonDocument doc;
    doc["type"] = "ota";
    doc["event"] = "error";
    doc["code"] = static_cast<int>(error);
    sendJson(doc);
  });
  ArduinoOTA.begin();
  gOtaReady = true;
  sendOtaStatus("ready");
}

static void updateOta() {
  const uint32_t now = millis();
  if (now - gLastOtaHandleMs < OTA_HANDLE_INTERVAL_MS) {
    return;
  }
  gLastOtaHandleMs = now;
  ArduinoOTA.handle();
}

static void updateWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  const uint32_t now = millis();
  if (now - gLastWifiRetryMs < WIFI_RETRY_INTERVAL_MS) {
    return;
  }
  gLastWifiRetryMs = now;
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

static void handleCommandObject(JsonDocument &doc) {
  const char *cmd = doc["cmd"] | "";
  const long id = doc["id"] | -1;

  if (strcmp(cmd, "emergency_stop") == 0) {
    emergencyStop();
    sendSerialAck(id);
    sendTelemetryJson();
    return;
  }

  if (strcmp(cmd, "set_pwm1") == 0) {
    float percent = 0.0f;
    if (!readFloatField(doc, "percent", percent, id, "missing_percent")) return;
    setPwm1Percent(percent);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "set_pump") == 0) {
    float percent = 0.0f;
    if (!readFloatField(doc, "percent", percent, id, "missing_percent")) return;
    setPumpPercent(percent);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "pump_stop") == 0) {
    setPumpPercent(0.0f);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_enable") == 0) {
    setSliderEnabled(true);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_disable") == 0) {
    sliderHalt();
    setSliderEnabled(false);
    sendSerialAck(id);
    sendTelemetryJson();
    return;
  }

  if (strcmp(cmd, "slider_speed") == 0) {
    float speed = 0.0f;
    if (!readFloatField(doc, "speed", speed, id, "missing_speed")) return;
    if (speed < SLIDER_MIN_SPEED || speed > SLIDER_MAX_SPEED) {
      sendSerialError("slider_speed_out_of_range", id);
      return;
    }
    gSliderSpeed = speed;
    sliderStepper.setMaxSpeed(gSliderSpeed);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_accel") == 0) {
    float accel = 0.0f;
    if (!readFloatField(doc, "accel", accel, id, "missing_accel")) return;
    if (accel <= 0.0f) {
      sendSerialError("invalid_slider_accel", id);
      return;
    }
    sliderStepper.setAcceleration(accel);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move") == 0) {
    if (!jsonHasNumber(doc, "steps")) {
      sendSerialError("missing_steps", id);
      return;
    }
    sliderMoveSteps(doc["steps"].as<long>(), id);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move_mm") == 0) {
    float mm = 0.0f;
    if (!readFloatField(doc, "mm", mm, id, "missing_mm")) return;
    sliderMoveMm(mm, id);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move_time") == 0) {
    float mm = 0.0f;
    float sec = 0.0f;
    if (!readFloatField(doc, "mm", mm, id, "missing_mm")) return;
    if (!readFloatField(doc, "sec", sec, id, "missing_sec")) return;
    if (sliderMoveTime(mm, sec, id)) sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_left") == 0) {
    sliderMoveContinuous(-1);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_right") == 0) {
    sliderMoveContinuous(1);
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_stop") == 0) {
    sliderStepper.stop();
    gSliderStopActive = true;
    gSliderStopCommandId = id;
    sendSerialAck(id);
    return;
  }

  if (strcmp(cmd, "slider_halt") == 0) {
    sliderHalt();
    sendSerialAck(id);
    sendTelemetryJson();
    return;
  }

  if (strcmp(cmd, "slider_zero") == 0) {
    sliderStepper.setCurrentPosition(0);
    sendSerialAck(id);
    sendTelemetryJson();
    return;
  }

  if (strcmp(cmd, "status") == 0 || strcmp(cmd, "read") == 0) {
    sendSerialAck(id);
    sendTelemetryJson();
    return;
  }

  if (doc["pwm1_percent"].is<float>() || doc["pwm1_percent"].is<int>()) {
    setPwm1Percent(doc["pwm1_percent"].as<float>());
  }
  if (doc["pump_percent"].is<float>() || doc["pump_percent"].is<int>()) {
    setPumpPercent(doc["pump_percent"].as<float>());
  }
  if (doc["pwm1_percent"].is<float>() || doc["pwm1_percent"].is<int>() ||
      doc["pump_percent"].is<float>() || doc["pump_percent"].is<int>()) {
    sendSerialAck(id);
    return;
  }

  sendSerialError("unknown_command", id);
}

static void handleSerialJsonLine(const char *line) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    sendSerialError("invalid_json");
    return;
  }

  handleCommandObject(doc);
}

static void processSerialInput() {
  size_t processed = 0;
  while (Serial.available() > 0 && processed < SERIAL_BYTES_PER_LOOP) {
    ++processed;
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

static void updateSliderCompletion() {
  if (gSliderStopActive && sliderStepper.distanceToGo() == 0) {
    sendSerialDone(gSliderStopCommandId, true);
    gSliderStopActive = false;
    gSliderStopCommandId = -1;
    clearSliderMove(false);
    sendTelemetryJson();
    return;
  }

  if (gSliderMoveActive && sliderStepper.distanceToGo() == 0) {
    sendSerialDone(gSliderMoveCommandId, true);
    gSliderMoveActive = false;
    gSliderMoveCommandId = -1;
    sendTelemetryJson();
  }
}

static void initSlider() {
  pinMode(SLIDER_ENABLE_PIN, OUTPUT);
  sliderStepper.setMaxSpeed(gSliderSpeed);
  sliderStepper.setAcceleration(SLIDER_DEFAULT_ACCEL);
  sliderStepper.setEnablePin(SLIDER_ENABLE_PIN);
  sliderStepper.setPinsInverted(false, false, SLIDER_ENABLE_ACTIVE_LOW);
  setSliderEnabled(false);
}

void setup() {
  Serial.begin(115200);

  initSlider();

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

  setupOta();

  if (SERIAL_DEBUG_TEXT) {
    Serial.printf("ADS1220 cfg: R0=0x%02X R1=0x%02X R2=0x%02X R3=0x%02X\n",
                  ads.readRegister(0), ads.readRegister(1), ads.readRegister(2), ads.readRegister(3));
    Serial.printf("PH calib: slope=%.6f intercept=%.6f\n", ads.getPHSlope(), ads.getPHIntercept());
    Serial.printf("DS18B20 init: %s (pin=%u)\n", dsReady ? "OK" : "FAIL", DS18B20_PIN);
  }

  JsonDocument boot;
  boot["type"] = "boot";
  boot["ok"] = true;
  boot["ds18b20_ok"] = dsReady;
  addSliderTelemetry(boot);
  sendJson(boot);
}

void loop() {
  runSlider();
  processSerialInput();
  runSlider();
  updateOta();
  runSlider();
  updateWifi();
  runSlider();
  updateSliderCompletion();
  runSlider();

  if (!sliderBusy()) {
    updatePhReading();
    runSlider();
    updateTemperatureReading();
    runSlider();
    updateSerialTelemetry();
  }
}
