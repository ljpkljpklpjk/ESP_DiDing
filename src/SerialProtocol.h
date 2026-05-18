#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

class SerialProtocol {
 public:
  using LineHandler = void (*)(JsonDocument &doc, void *context);

  SerialProtocol();

  void processInput(LineHandler handler, void *context);
  void sendJson(JsonDocument &doc);
  void sendAck(long id, float pwm1Percent, float pumpPercent);
  void sendDone(long id, bool ok);
  void sendError(const char *code, long id = -1);
  static void setFloatOrNull(JsonDocument &doc, const char *key, float value);

 private:
  void handleLine(const char *line, LineHandler handler, void *context);

  char rxBuf_[320];
  size_t rxLen_ = 0;
};
