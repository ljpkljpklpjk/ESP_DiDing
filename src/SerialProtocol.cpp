#include "SerialProtocol.h"

#include "AppConfig.h"

SerialProtocol::SerialProtocol() = default;

void SerialProtocol::ensureTxMutex() {
  if (!txMutex_) {
    txMutex_ = xSemaphoreCreateMutex();
  }
}

void SerialProtocol::processInput(LineHandler handler, void *context) {
  size_t processed = 0;
  while (Serial.available() > 0 && processed < AppConfig::SERIAL_BYTES_PER_LOOP) {
    ++processed;
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      rxBuf_[rxLen_] = '\0';
      if (rxLen_ > 0) {
        handleLine(rxBuf_, handler, context);
      }
      rxLen_ = 0;
      continue;
    }
    if (rxLen_ < sizeof(rxBuf_) - 1) {
      rxBuf_[rxLen_++] = c;
    } else {
      rxLen_ = 0;
      sendError("line_too_long");
    }
  }
}

void SerialProtocol::sendJson(JsonDocument &doc) {
  ensureTxMutex();
  if (txMutex_) {
    xSemaphoreTake(txMutex_, portMAX_DELAY);
  }
  serializeJson(doc, Serial);
  Serial.println();
  if (txMutex_) {
    xSemaphoreGive(txMutex_);
  }
}

void SerialProtocol::sendAck(long id, float pwm1Percent, float pumpPercent) {
  JsonDocument doc;
  doc["type"] = "ack";
  if (id >= 0) doc["id"] = id;
  doc["ok"] = true;
  doc["pwm1_percent"] = pwm1Percent;
  doc["pump_percent"] = pumpPercent;
  sendJson(doc);
}

void SerialProtocol::sendDone(long id, bool ok) {
  JsonDocument doc;
  doc["type"] = "done";
  if (id >= 0) doc["id"] = id;
  doc["ok"] = ok;
  sendJson(doc);
}

void SerialProtocol::sendError(const char *code, long id) {
  JsonDocument doc;
  doc["type"] = "error";
  if (id >= 0) doc["id"] = id;
  doc["code"] = code;
  sendJson(doc);
}

void SerialProtocol::setFloatOrNull(JsonDocument &doc, const char *key, float value) {
  if (isnan(value) || isinf(value)) {
    doc[key] = nullptr;
  } else {
    doc[key] = value;
  }
}

void SerialProtocol::handleLine(const char *line, LineHandler handler, void *context) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    sendError("invalid_json");
    return;
  }

  handler(doc, context);
}
