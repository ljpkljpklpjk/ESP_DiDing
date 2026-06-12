#include "NetworkOtaManager.h"

#include <ArduinoOTA.h>
#include <Preferences.h>
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

  loadCredentials();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  startWifi();

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
  startWifi();
}

void NetworkOtaManager::connectToWifi(const char *ssid, const char *password) {
  saveCredentials(ssid, password);
  ssid_ = ssid;
  password_ = password;

  WiFi.disconnect();
  delay(100);
  startWifi();
}

bool NetworkOtaManager::wifiConnected() const {
  return WiFi.status() == WL_CONNECTED;
}

String NetworkOtaManager::ipText() const {
  return wifiConnected() ? WiFi.localIP().toString() : "";
}

String NetworkOtaManager::ssid() const {
  return wifiConnected() ? WiFi.SSID() : ssid_;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

void NetworkOtaManager::loadCredentials() {
  Preferences prefs;
  if (!prefs.begin(AppConfig::WIFI_NVS_NAMESPACE, true)) {
    // NVS partition not available — use compile-time defaults
    ssid_ = AppConfig::WIFI_SSID;
    password_ = AppConfig::WIFI_PASSWORD;
    return;
  }
  ssid_ = prefs.getString("ssid", AppConfig::WIFI_SSID);
  password_ = prefs.getString("pass", AppConfig::WIFI_PASSWORD);
  prefs.end();
}

void NetworkOtaManager::saveCredentials(const char *ssid, const char *password) {
  Preferences prefs;
  prefs.begin(AppConfig::WIFI_NVS_NAMESPACE, false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", password);
  prefs.end();
}

void NetworkOtaManager::startWifi() {
  WiFi.begin(ssid_.c_str(), password_.c_str());
}
