#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

class SerialProtocol {
 public:
  using LineHandler = void (*)(JsonDocument &doc, void *context);

  SerialProtocol();

  void begin();
  void processInput(LineHandler handler, void *context);
  void sendTextLine(const char *text);
  void sendJson(JsonDocument &doc);
  void sendAck(long id, float pwm1Percent, float pumpPercent);
  void sendDone(long id, bool ok);
  void sendError(const char *code, long id = -1);
  static void setFloatOrNull(JsonDocument &doc, const char *key, float value);

 private:
  Stream &port();
  void setRs485Transmit(bool enabled);
  void handleLine(const char *line, LineHandler handler, void *context);
  void ensureTxMutex();

  HardwareSerial rs485Serial_;
  bool usingRs485_ = false;
  char rxBuf_[320];
  size_t rxLen_ = 0;
  SemaphoreHandle_t txMutex_ = nullptr;
};
