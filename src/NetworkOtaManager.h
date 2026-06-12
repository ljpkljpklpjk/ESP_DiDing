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
  String ssid() const;

  /// Switch to a new AP and persist credentials so they survive reboot.
  void connectToWifi(const char *ssid, const char *password);

 private:
  void loadCredentials();
  void saveCredentials(const char *ssid, const char *password);
  void startWifi();

  Callback emergencyStop_ = nullptr;
  OtaStatusCallback statusCallback_ = nullptr;
  void *context_ = nullptr;
  uint32_t lastWifiRetryMs_ = 0;
  uint32_t lastOtaHandleMs_ = 0;
  bool otaReady_ = false;

  String ssid_;
  String password_;
};
