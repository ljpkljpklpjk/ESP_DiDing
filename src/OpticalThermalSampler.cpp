#include "OpticalThermalSampler.h"

#include <Wire.h>
#include <math.h>

#include "AppConfig.h"
#include "SerialProtocol.h"

bool OpticalThermalSampler::begin() {
  Wire.begin(AppConfig::I2C_SDA_PIN, AppConfig::I2C_SCL_PIN);

  mlxReady_ = mlx_.begin(0x33, &Wire);
  if (mlxReady_) {
    mlx_.setMode(MLX90640_INTERLEAVED);
    mlx_.setResolution(MLX90640_ADC_18BIT);
    mlx_.setRefreshRate(MLX90640_4_HZ);
  }

  as7341Ready_ = as7341_.begin();
  if (as7341Ready_) {
    as7341_.setATIME(100);
    as7341_.setASTEP(99);
    as7341_.setGain(AS7341_GAIN_256X);
  }

  bme280Ready_ = bme280_.begin(AppConfig::BME280_I2C_ADDR_PRIMARY, &Wire);
  if (!bme280Ready_) {
    bme280Ready_ = bme280_.begin(AppConfig::BME280_I2C_ADDR_SECONDARY, &Wire);
  }

  tofReady_ = tof_.begin(AppConfig::TOF_I2C_ADDR, false, &Wire);

  return mlxReady_ || as7341Ready_ || bme280Ready_ || tofReady_;
}

void OpticalThermalSampler::update() {
  updateMlx();
  updateAs7341();
  updateBme280();
  updateTof();
}

void OpticalThermalSampler::updateMlx() {
  if (!mlxReady_) {
    return;
  }

  const uint32_t now = millis();
  if (now - lastMlxSampleMs_ < AppConfig::MLX90640_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastMlxSampleMs_ = now;

  static float frame[32 * 24];
  if (mlx_.getFrame(frame) != 0) {
    return;
  }

  float sum = 0.0f;
  float minTemp = frame[0];
  float maxTemp = frame[0];
  for (int i = 0; i < 32 * 24; ++i) {
    sum += frame[i];
    if (frame[i] < minTemp) {
      minTemp = frame[i];
    }
    if (frame[i] > maxTemp) {
      maxTemp = frame[i];
    }
  }
  mlxAverageTempC_ = sum / static_cast<float>(32 * 24);
  mlxMinTempC_ = minTemp;
  mlxMaxTempC_ = maxTemp;
  thermalGradientC_ = maxTemp - minTemp;
}

void OpticalThermalSampler::updateAs7341() {
  if (!as7341Ready_) {
    return;
  }

  const uint32_t now = millis();
  if (now - lastAs7341SampleMs_ < AppConfig::AS7341_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastAs7341SampleMs_ = now;

  if (!as7341_.readAllChannels(spectrum_)) {
    return;
  }

  const int green = spectrum_[3] + spectrum_[4];
  const int yellow = spectrum_[5];
  const int red = spectrum_[6] + spectrum_[7];
  const int intensity = green + yellow + red;
  if (lastColorTimeMs_ > 0) {
    colorRate_ = (intensity - colorIntensity_) * 1000.0f / (now - lastColorTimeMs_);
  }
  colorIntensity_ = intensity;
  lastColorTimeMs_ = now;
  updateDerivedColorMetrics();
}

void OpticalThermalSampler::updateBme280() {
  if (!bme280Ready_) {
    return;
  }

  const uint32_t now = millis();
  if (now - lastBmeSampleMs_ < AppConfig::BME280_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastBmeSampleMs_ = now;

  bmeTemperatureC_ = bme280_.readTemperature();
  bmeHumidityPercent_ = bme280_.readHumidity();
  bmePressureHpa_ = bme280_.readPressure() / 100.0f;
}

void OpticalThermalSampler::updateTof() {
  if (!tofReady_) {
    return;
  }

  const uint32_t now = millis();
  if (now - lastTofSampleMs_ < AppConfig::TOF_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastTofSampleMs_ = now;

  VL53L0X_RangingMeasurementData_t measure;
  tof_.rangingTest(&measure, false);
  if (measure.RangeStatus == 4) {
    tofDistanceMm_ = NAN;
    tofConfidence_ = 0;
    return;
  }
  tofDistanceMm_ = measure.RangeMilliMeter;
  tofConfidence_ = 100;
}

void OpticalThermalSampler::updateDerivedColorMetrics() {
  if (colorIntensity_ <= 0 || AppConfig::ABSORBANCE_REFERENCE_INTENSITY <= 0.0f) {
    absorbanceAu_ = NAN;
    concentration_ = NAN;
    return;
  }

  const float ratio =
      static_cast<float>(colorIntensity_) / AppConfig::ABSORBANCE_REFERENCE_INTENSITY;
  if (ratio <= 0.0f) {
    absorbanceAu_ = NAN;
    concentration_ = NAN;
    return;
  }

  absorbanceAu_ = -log10f(ratio);
  concentration_ =
      AppConfig::CONCENTRATION_SLOPE * absorbanceAu_ +
      AppConfig::CONCENTRATION_INTERCEPT;
}

void OpticalThermalSampler::addTelemetry(JsonDocument &doc) const {
  doc["mlx90640_ok"] = mlxReady_;
  doc["as7341_ok"] = as7341Ready_;
  doc["bme280_ok"] = bme280Ready_;
  doc["tof_ok"] = tofReady_;
  SerialProtocol::setFloatOrNull(doc, "mlx90640_avg_temp_c", mlxAverageTempC_);
  SerialProtocol::setFloatOrNull(doc, "thermal_avg_c", mlxAverageTempC_);
  SerialProtocol::setFloatOrNull(doc, "thermal_max_c", mlxMaxTempC_);
  SerialProtocol::setFloatOrNull(doc, "thermal_min_c", mlxMinTempC_);
  SerialProtocol::setFloatOrNull(doc, "thermal_gradient_c", thermalGradientC_);
  SerialProtocol::setFloatOrNull(doc, "bme280_temperature_c", bmeTemperatureC_);
  SerialProtocol::setFloatOrNull(doc, "bme280_humidity_percent", bmeHumidityPercent_);
  SerialProtocol::setFloatOrNull(doc, "bme280_pressure_hpa", bmePressureHpa_);
  SerialProtocol::setFloatOrNull(doc, "tof_distance_mm", tofDistanceMm_);
  doc["tof_confidence"] = tofConfidence_;
  doc["as7341_intensity"] = colorIntensity_;
  SerialProtocol::setFloatOrNull(doc, "as7341_rate", colorRate_);
  SerialProtocol::setFloatOrNull(doc, "absorbance_au", absorbanceAu_);
  SerialProtocol::setFloatOrNull(doc, "concentration", concentration_);

  JsonArray channels = doc["as7341_channels"].to<JsonArray>();
  for (uint8_t i = 0; i < 12; ++i) {
    channels.add(spectrum_[i]);
  }
}
