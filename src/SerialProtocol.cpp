#include "SerialProtocol.h"

#include "AppConfig.h"

SerialProtocol::SerialProtocol() : rs485Serial_(AppConfig::RS485_UART_NUM) {}

void SerialProtocol::begin() {
  if (AppConfig::COMM_INTERFACE == AppConfig::CommInterface::Rs485Uart) {
    usingRs485_ = true;
    if (AppConfig::RS485_DE_PIN >= 0) {
      pinMode(AppConfig::RS485_DE_PIN, OUTPUT);
    }
    if (AppConfig::RS485_RE_PIN >= 0) {
      pinMode(AppConfig::RS485_RE_PIN, OUTPUT);
    }
    setRs485Transmit(false);
    rs485Serial_.begin(AppConfig::COMM_BAUDRATE, SERIAL_8N1,
                       AppConfig::RS485_RX_PIN, AppConfig::RS485_TX_PIN);
    return;
  }

  usingRs485_ = false;
  Serial.begin(AppConfig::COMM_BAUDRATE);
}

Stream &SerialProtocol::port() {
  if (usingRs485_) {
    return rs485Serial_;
  }
  return Serial;
}

void SerialProtocol::setRs485Transmit(bool enabled) {
  if (!usingRs485_) {
    return;
  }
  const uint8_t active = AppConfig::RS485_ENABLE_ACTIVE_HIGH ? HIGH : LOW;
  const uint8_t inactive = AppConfig::RS485_ENABLE_ACTIVE_HIGH ? LOW : HIGH;
  if (AppConfig::RS485_DE_PIN >= 0) {
    digitalWrite(AppConfig::RS485_DE_PIN, enabled ? active : inactive);
  }
  if (AppConfig::RS485_RE_PIN >= 0) {
    digitalWrite(AppConfig::RS485_RE_PIN, enabled ? active : inactive);
  }
  if (enabled && AppConfig::RS485_TX_SETTLE_US > 0) {
    delayMicroseconds(AppConfig::RS485_TX_SETTLE_US);
  }
}

void SerialProtocol::ensureTxMutex() {
  if (!txMutex_) {
    txMutex_ = xSemaphoreCreateMutex();
  }
}

void SerialProtocol::processInput(LineHandler handler, void *context) {
  size_t processed = 0;
  Stream &serialPort = port();
  while (serialPort.available() > 0 &&
         processed < AppConfig::SERIAL_BYTES_PER_LOOP) {
    ++processed;
    const char c = static_cast<char>(serialPort.read());
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

void SerialProtocol::sendTextLine(const char *text) {
  ensureTxMutex();
  if (txMutex_) {
    xSemaphoreTake(txMutex_, portMAX_DELAY);
  }
  Stream &serialPort = port();
  setRs485Transmit(true);
  serialPort.println(text);
  serialPort.flush();
  setRs485Transmit(false);
  if (txMutex_) {
    xSemaphoreGive(txMutex_);
  }
}

void SerialProtocol::sendJson(JsonDocument &doc) {
  ensureTxMutex();
  if (txMutex_) {
    xSemaphoreTake(txMutex_, portMAX_DELAY);
  }
  Stream &serialPort = port();
  setRs485Transmit(true);
  serializeJson(doc, serialPort);
  serialPort.println();
  serialPort.flush();
  setRs485Transmit(false);
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
