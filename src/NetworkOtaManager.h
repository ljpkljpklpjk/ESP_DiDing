#pragma once

#include <ArduinoJson.h>

class NetworkOtaManager {
 public:
  using Callback = void (*)(void *context);
  using OtaStatusCallback = void (*)(const char *event, int code, void *context);

  NetworkOtaManager();

  void begin(Callback emergencyStop, OtaStatusCallback statusCallback, void *context);
  void updateOta(bool busy);
  void updateWifi();
  bool otaReady() const { return otaReady_; }
  bool wifiConnected() const;
  String ipText() const;

 private:
  Callback emergencyStop_ = nullptr;
  OtaStatusCallback statusCallback_ = nullptr;
  void *context_ = nullptr;
  uint32_t lastWifiRetryMs_ = 0;
  uint32_t lastOtaHandleMs_ = 0;
  bool otaReady_ = false;
};
