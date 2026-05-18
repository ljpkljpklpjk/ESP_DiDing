#include "OpticalThermalSampler.h"

#include <Wire.h>

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

  return mlxReady_ || as7341Ready_;
}

void OpticalThermalSampler::update() {
  updateMlx();
  updateAs7341();
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
  for (int i = 0; i < 32 * 24; ++i) {
    sum += frame[i];
  }
  mlxAverageTempC_ = sum / static_cast<float>(32 * 24);
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
}

void OpticalThermalSampler::addTelemetry(JsonDocument &doc) const {
  doc["mlx90640_ok"] = mlxReady_;
  doc["as7341_ok"] = as7341Ready_;
  SerialProtocol::setFloatOrNull(doc, "mlx90640_avg_temp_c", mlxAverageTempC_);
  doc["as7341_intensity"] = colorIntensity_;
  SerialProtocol::setFloatOrNull(doc, "as7341_rate", colorRate_);

  JsonArray channels = doc["as7341_channels"].to<JsonArray>();
  for (uint8_t i = 0; i < 12; ++i) {
    channels.add(spectrum_[i]);
  }
}
