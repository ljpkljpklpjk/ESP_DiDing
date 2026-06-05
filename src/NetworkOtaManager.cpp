#include "NetworkOtaManager.h"

#include <ArduinoOTA.h>
#include <WiFi.h>

#include "AppConfig.h"

static NetworkOtaManager *gNetworkOtaInstance = nullptr;

NetworkOtaManager::NetworkOtaManager() = default;

void NetworkOtaManager::begin(Callback emergencyStop,
                              OtaStatusCallback statusCallback,
                              void *context) {
  emergencyStop_ = emergencyStop;
  statusCallback_ = statusCallback;
  context_ = context;
  gNetworkOtaInstance = this;

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(AppConfig::WIFI_SSID, AppConfig::WIFI_PASSWORD);

  ArduinoOTA.setHostname(AppConfig::OTA_HOSTNAME);
  ArduinoOTA.setPassword(AppConfig::OTA_PASSWORD);
  ArduinoOTA.onStart([]() {
    if (gNetworkOtaInstance && gNetworkOtaInstance->emergencyStop_) {
      gNetworkOtaInstance->emergencyStop_(gNetworkOtaInstance->context_);
    }
    if (gNetworkOtaInstance && gNetworkOtaInstance->statusCallback_) {
      gNetworkOtaInstance->statusCallback_("start", -1, gNetworkOtaInstance->context_);
    }
  });
  ArduinoOTA.onEnd([]() {
    if (gNetworkOtaInstance && gNetworkOtaInstance->statusCallback_) {
      gNetworkOtaInstance->statusCallback_("end", -1, gNetworkOtaInstance->context_);
    }
  });
  ArduinoOTA.onError([](ota_error_t error) {
    if (gNetworkOtaInstance && gNetworkOtaInstance->statusCallback_) {
      gNetworkOtaInstance->statusCallback_("error", static_cast<int>(error),
                                           gNetworkOtaInstance->context_);
    }
  });
  ArduinoOTA.begin();
  otaReady_ = true;
  if (statusCallback_) {
    statusCallback_("ready", -1, context_);
  }
}

void NetworkOtaManager::updateOta(bool busy) {
  const uint32_t now = millis();
  const uint32_t interval = busy ? AppConfig::OTA_HANDLE_MOVING_INTERVAL_MS
                                : AppConfig::OTA_HANDLE_INTERVAL_MS;
  if (now - lastOtaHandleMs_ < interval) {
    return;
  }
  lastOtaHandleMs_ = now;
  ArduinoOTA.handle();
}

void NetworkOtaManager::updateWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  const uint32_t now = millis();
  if (now - lastWifiRetryMs_ < AppConfig::WIFI_RETRY_INTERVAL_MS) {
    return;
  }
  lastWifiRetryMs_ = now;
  WiFi.disconnect();
  WiFi.begin(AppConfig::WIFI_SSID, AppConfig::WIFI_PASSWORD);
}

bool NetworkOtaManager::wifiConnected() const {
  return WiFi.status() == WL_CONNECTED;
}

String NetworkOtaManager::ipText() const {
  return wifiConnected() ? WiFi.localIP().toString() : "";
}
