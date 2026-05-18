#include "TitratorApp.h"

#include <string.h>

#include "AppConfig.h"
#include "Telemetry.h"

void TitratorApp::begin() {
  slider_.begin();

  if (!outputs_.begin()) {
    serial_.sendError("pwm_pump_init_failed");
    while (true) {
      delay(1000);
    }
  }

  const bool dsReady = sensors_.begin();
  const bool opticalReady = opticalThermal_.begin();
  network_.begin(emergencyStopCallback, otaStatusCallback, this);

  JsonDocument boot;
  boot["type"] = "boot";
  boot["ok"] = true;
  boot["ds18b20_ok"] = dsReady;
  boot["optical_thermal_ok"] = opticalReady;
  slider_.addTelemetry(boot);
  serial_.sendJson(boot);
}

void TitratorApp::loop() {
  slider_.run();

  if (slider_.busy()) {
    serial_.processInput(handleSerialDocument, this);
    slider_.run();
    network_.updateOta(true);
    slider_.run();
    network_.updateWifi();
    slider_.run();
    updateSliderCompletion();
    slider_.run();
    return;
  }

  serial_.processInput(handleSerialDocument, this);
  slider_.run();
  network_.updateOta(false);
  slider_.run();
  network_.updateWifi();
  slider_.run();
  updateSliderCompletion();
  slider_.run();
  sensors_.updatePh();
  slider_.run();
  sensors_.updateTemperature();
  slider_.run();
  opticalThermal_.update();
  slider_.run();
  updateSerialTelemetry();
}

void TitratorApp::handleSerialDocument(JsonDocument &doc, void *context) {
  static_cast<TitratorApp *>(context)->handleCommand(doc);
}

void TitratorApp::emergencyStopCallback(void *context) {
  static_cast<TitratorApp *>(context)->emergencyStop();
}

void TitratorApp::otaStatusCallback(const char *event, int code, void *context) {
  static_cast<TitratorApp *>(context)->sendOtaStatus(event, code);
}

void TitratorApp::handleCommand(JsonDocument &doc) {
  const char *cmd = doc["cmd"] | "";
  const long id = doc["id"] | -1;

  if (strcmp(cmd, "emergency_stop") == 0) {
    emergencyStop();
    sendAck(id);
    sendTelemetry();
    return;
  }

  if (strcmp(cmd, "set_pwm1") == 0) {
    float percent = 0.0f;
    if (!readFloatField(doc, "percent", percent, id, "missing_percent")) return;
    outputs_.setPwm1Percent(percent);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "set_pump") == 0) {
    float percent = 0.0f;
    if (!readFloatField(doc, "percent", percent, id, "missing_percent")) return;
    outputs_.setPumpPercent(percent);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "pump_stop") == 0) {
    outputs_.setPumpPercent(0.0f);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_enable") == 0) {
    slider_.setEnabled(true);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_disable") == 0) {
    slider_.halt();
    slider_.setEnabled(false);
    sendAck(id);
    sendTelemetry();
    return;
  }

  if (strcmp(cmd, "slider_speed") == 0) {
    float speed = 0.0f;
    if (!readFloatField(doc, "speed", speed, id, "missing_speed")) return;
    if (!slider_.speedInRange(speed)) {
      serial_.sendError("slider_speed_out_of_range", id);
      return;
    }
    slider_.setSpeed(speed);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_accel") == 0) {
    float accel = 0.0f;
    if (!readFloatField(doc, "accel", accel, id, "missing_accel")) return;
    if (accel <= 0.0f) {
      serial_.sendError("invalid_slider_accel", id);
      return;
    }
    slider_.setAcceleration(accel);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move") == 0) {
    if (!jsonHasNumber(doc, "steps")) {
      serial_.sendError("missing_steps", id);
      return;
    }
    slider_.moveSteps(doc["steps"].as<long>(), id);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move_mm") == 0) {
    float mm = 0.0f;
    if (!readFloatField(doc, "mm", mm, id, "missing_mm")) return;
    slider_.moveMm(mm, id);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_move_time") == 0) {
    float mm = 0.0f;
    float sec = 0.0f;
    if (!readFloatField(doc, "mm", mm, id, "missing_mm")) return;
    if (!readFloatField(doc, "sec", sec, id, "missing_sec")) return;
    if (sec <= 0.0f) {
      serial_.sendError("invalid_slider_time", id);
      return;
    }
    const long steps = lround(mm * AppConfig::SLIDER_STEPS_PER_MM);
    const float requiredSpeed = fabs(static_cast<float>(steps)) / sec;
    if (!slider_.speedInRange(requiredSpeed)) {
      serial_.sendError("slider_speed_out_of_range", id);
      return;
    }
    slider_.moveTime(mm, sec, id);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_left") == 0) {
    slider_.moveContinuous(-1);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_right") == 0) {
    slider_.moveContinuous(1);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_stop") == 0) {
    slider_.stop(id);
    sendAck(id);
    return;
  }

  if (strcmp(cmd, "slider_halt") == 0) {
    slider_.halt();
    sendAck(id);
    sendTelemetry();
    return;
  }

  if (strcmp(cmd, "slider_zero") == 0) {
    slider_.zero();
    sendAck(id);
    sendTelemetry();
    return;
  }

  if (strcmp(cmd, "status") == 0 || strcmp(cmd, "read") == 0) {
    sendAck(id);
    sendTelemetry();
    return;
  }

  if (doc["pwm1_percent"].is<float>() || doc["pwm1_percent"].is<int>()) {
    outputs_.setPwm1Percent(doc["pwm1_percent"].as<float>());
  }
  if (doc["pump_percent"].is<float>() || doc["pump_percent"].is<int>()) {
    outputs_.setPumpPercent(doc["pump_percent"].as<float>());
  }
  if (doc["pwm1_percent"].is<float>() || doc["pwm1_percent"].is<int>() ||
      doc["pump_percent"].is<float>() || doc["pump_percent"].is<int>()) {
    sendAck(id);
    return;
  }

  serial_.sendError("unknown_command", id);
}

void TitratorApp::emergencyStop() {
  slider_.halt();
  slider_.setEnabled(false);
  outputs_.stopAll();
}

void TitratorApp::sendAck(long id) {
  serial_.sendAck(id, outputs_.pwm1Percent(), outputs_.pumpPercent());
}

void TitratorApp::sendTelemetry() {
  JsonDocument doc;
  buildTelemetry(doc, sensors_, opticalThermal_, outputs_, slider_, network_);
  serial_.sendJson(doc);
}

void TitratorApp::sendOtaStatus(const char *event, int code) {
  JsonDocument doc;
  doc["type"] = "ota";
  doc["event"] = event;
  if (code >= 0) {
    doc["code"] = code;
  }
  doc["ip"] = network_.ipText();
  serial_.sendJson(doc);
}

void TitratorApp::updateSerialTelemetry() {
  if (slider_.busy()) {
    return;
  }
  const uint32_t now = millis();
  if (now - lastTelemetryMs_ < AppConfig::TELEMETRY_INTERVAL_MS) {
    return;
  }
  lastTelemetryMs_ = now;
  sendTelemetry();
}

void TitratorApp::updateSliderCompletion() {
  SliderEvent event = slider_.updateCompletion();
  if (!event.active) {
    return;
  }
  serial_.sendDone(event.id, event.ok);
  sendTelemetry();
}

bool TitratorApp::jsonHasNumber(JsonDocument &doc, const char *key) {
  return doc[key].is<float>() || doc[key].is<int>() || doc[key].is<long>();
}

bool TitratorApp::readFloatField(JsonDocument &doc, const char *key, float &out,
                                 long id, const char *errorCode) {
  if (!jsonHasNumber(doc, key)) {
    serial_.sendError(errorCode, id);
    return false;
  }
  out = doc[key].as<float>();
  return true;
}
