#include "SensorSampler.h"

#include "AppConfig.h"

SensorSampler::SensorSampler()
    : adsSpi_(FSPI),
      ads_(adsSpi_, AppConfig::adsPins()),
      ds18b20_(AppConfig::DS18B20_PIN) {}

bool SensorSampler::begin() {
  ads_.begin();
  ads_.setPHCalibration(AppConfig::phCalibration());
  ds18b20Ready_ = ds18b20_.begin();
  return ds18b20Ready_;
}

void SensorSampler::updatePh() {
  const uint32_t now = millis();
  if (now - lastPhSampleMs_ < 500) {
    return;
  }
  lastPhSampleMs_ = now;

  const float v = ads_.readVoltage(ADS1220Module::AIN0_AIN1,
                                   AppConfig::ADS1220_READ_TIMEOUT_MS);
  if (isnan(v)) {
    voltage_ = NAN;
    ph_ = NAN;
    if (AppConfig::SERIAL_DEBUG_TEXT) {
      Serial.println("ADS1220 timeout (check DRDY pin/wiring)");
    }
    return;
  }

  voltage_ = v;
  ph_ = ads_.voltageToPH(v);

  if (AppConfig::SERIAL_DEBUG_TEXT) {
    Serial.printf("PH voltage=%.6f V, pH=%.3f\n", voltage_, ph_);
  }
}

void SensorSampler::updateTemperature() {
  const uint32_t now = millis();
  if (!tempConversionPending_ &&
      now - lastTempRequestMs_ >= AppConfig::TEMP_REQUEST_INTERVAL_MS) {
    ds18b20_.requestTemperature();
    lastTempRequestMs_ = now;
    tempConversionPending_ = true;
    return;
  }

  if (!tempConversionPending_ ||
      now - lastTempRequestMs_ < AppConfig::TEMP_CONVERSION_DELAY_MS) {
    return;
  }

  tempConversionPending_ = false;
  lastTempSampleMs_ = now;
  temperatureC_ = ds18b20_.readLastCelsius();
  if (isnan(temperatureC_)) {
    if (AppConfig::SERIAL_DEBUG_TEXT) {
      Serial.println("DS18B20 read failed");
    }
    return;
  }

  if (AppConfig::SERIAL_DEBUG_TEXT) {
    Serial.printf("Temp: %.2f C\n", temperatureC_);
  }
}
