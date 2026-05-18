#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

#include "NetworkOtaManager.h"
#include "OpticalThermalSampler.h"
#include "OutputController.h"
#include "SensorSampler.h"
#include "SerialProtocol.h"
#include "SliderController.h"

class TitratorApp {
 public:
  void begin();
  void loop();

 private:
  static void handleSerialDocument(JsonDocument &doc, void *context);
  static void emergencyStopCallback(void *context);
  static void otaStatusCallback(const char *event, int code, void *context);

  void handleCommand(JsonDocument &doc);
  void emergencyStop();
  void sendAck(long id = -1);
  void sendTelemetry();
  void sendOtaStatus(const char *event, int code = -1);
  void updateSerialTelemetry();
  void updateSliderCompletion();
  bool jsonHasNumber(JsonDocument &doc, const char *key);
  bool readFloatField(JsonDocument &doc, const char *key, float &out,
                      long id, const char *errorCode);

  SensorSampler sensors_;
  OpticalThermalSampler opticalThermal_;
  OutputController outputs_;
  SliderController slider_;
  NetworkOtaManager network_;
  SerialProtocol serial_;
  uint32_t lastTelemetryMs_ = 0;
};
