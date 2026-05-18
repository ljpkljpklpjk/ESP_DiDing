#pragma once

#include <Arduino.h>

#include <Adafruit_AS7341.h>
#include <Adafruit_MLX90640.h>
#include <ArduinoJson.h>

class OpticalThermalSampler {
 public:
  bool begin();
  void update();
  void addTelemetry(JsonDocument &doc) const;

  bool mlxReady() const { return mlxReady_; }
  bool as7341Ready() const { return as7341Ready_; }
  float mlxAverageTempC() const { return mlxAverageTempC_; }
  int colorIntensity() const { return colorIntensity_; }
  float colorRate() const { return colorRate_; }

 private:
  void updateMlx();
  void updateAs7341();

  Adafruit_MLX90640 mlx_;
  Adafruit_AS7341 as7341_;
  bool mlxReady_ = false;
  bool as7341Ready_ = false;
  uint32_t lastMlxSampleMs_ = 0;
  uint32_t lastAs7341SampleMs_ = 0;
  uint32_t lastColorTimeMs_ = 0;
  float mlxAverageTempC_ = NAN;
  uint16_t spectrum_[12] = {};
  int colorIntensity_ = 0;
  float colorRate_ = 0.0f;
};
