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

void SensorSampler::updateTds() {
  const uint32_t now = millis();
  if (now - lastTdsSampleMs_ < AppConfig::TDS_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastTdsSampleMs_ = now;

  const float v = ads_.readVoltage(ADS1220Module::AIN2_AIN3,
                                   AppConfig::ADS1220_READ_TIMEOUT_MS);
  if (isnan(v)) {
    tdsVoltage_ = NAN;
    tdsPpm_ = NAN;
    if (AppConfig::SERIAL_DEBUG_TEXT) {
      Serial.println("ADS1220 TDS timeout (check AIN2/AIN3 wiring)");
    }
    return;
  }

  tdsVoltage_ = fabs(v);
  const float tempC = isnan(temperatureC_) ? 25.0f : temperatureC_;
  const float compensation =
      1.0f + AppConfig::TDS_TEMP_COEFFICIENT * (tempC - 25.0f);
  const float compensatedVoltage =
      compensation > 0.0f ? tdsVoltage_ / compensation : tdsVoltage_;
  const float tds = (133.42f * compensatedVoltage * compensatedVoltage *
                         compensatedVoltage -
                     255.86f * compensatedVoltage * compensatedVoltage +
                     857.39f * compensatedVoltage) *
                    AppConfig::TDS_CALIBRATION_FACTOR;
  const float newTdsPpm = tds < 0.0f ? 0.0f : tds;
  if (!isnan(lastTdsPpm_) && lastTdsRateMs_ > 0 && now > lastTdsRateMs_) {
    tdsSlopeMgLMin_ =
        (newTdsPpm - lastTdsPpm_) * 60000.0f / static_cast<float>(now - lastTdsRateMs_);
  }
  lastTdsPpm_ = newTdsPpm;
  lastTdsRateMs_ = now;
  tdsPpm_ = newTdsPpm;

  if (AppConfig::SERIAL_DEBUG_TEXT) {
    Serial.printf("TDS voltage=%.6f V, TDS=%.1f ppm\n", tdsVoltage_, tdsPpm_);
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
