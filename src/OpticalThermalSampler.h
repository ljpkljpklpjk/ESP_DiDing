#pragma once

#include <Arduino.h>

#include <Adafruit_AS7341.h>
#include <Adafruit_BME280.h>
#include <Adafruit_MLX90640.h>
#include <Adafruit_VL53L0X.h>
#include <ArduinoJson.h>

class OpticalThermalSampler {
 public:
  bool begin();
  void update();
  void addTelemetry(JsonDocument &doc) const;

  bool mlxReady() const { return mlxReady_; }
  bool as7341Ready() const { return as7341Ready_; }
  bool bme280Ready() const { return bme280Ready_; }
  bool tofReady() const { return tofReady_; }
  float mlxAverageTempC() const { return mlxAverageTempC_; }
  int colorIntensity() const { return colorIntensity_; }
  float colorRate() const { return colorRate_; }
  float bmeTemperatureC() const { return bmeTemperatureC_; }
  float bmeHumidityPercent() const { return bmeHumidityPercent_; }
  float bmePressureHpa() const { return bmePressureHpa_; }
  float tofDistanceMm() const { return tofDistanceMm_; }
  float mlxMaxTempC() const { return mlxMaxTempC_; }
  float mlxMinTempC() const { return mlxMinTempC_; }
  float thermalGradientC() const { return thermalGradientC_; }
  int tofConfidence() const { return tofConfidence_; }
  float absorbanceAu() const { return absorbanceAu_; }
  float concentration() const { return concentration_; }

 private:
  void updateMlx();
  void updateAs7341();
  void updateBme280();
  void updateTof();
  void updateDerivedColorMetrics();

  Adafruit_MLX90640 mlx_;
  Adafruit_AS7341 as7341_;
  Adafruit_BME280 bme280_;
  Adafruit_VL53L0X tof_;
  bool mlxReady_ = false;
  bool as7341Ready_ = false;
  bool bme280Ready_ = false;
  bool tofReady_ = false;
  uint32_t lastMlxSampleMs_ = 0;
  uint32_t lastAs7341SampleMs_ = 0;
  uint32_t lastBmeSampleMs_ = 0;
  uint32_t lastTofSampleMs_ = 0;
  uint32_t lastColorTimeMs_ = 0;
  float mlxAverageTempC_ = NAN;
  float mlxMaxTempC_ = NAN;
  float mlxMinTempC_ = NAN;
  float thermalGradientC_ = NAN;
  float bmeTemperatureC_ = NAN;
  float bmeHumidityPercent_ = NAN;
  float bmePressureHpa_ = NAN;
  float tofDistanceMm_ = NAN;
  int tofConfidence_ = 0;
  float absorbanceAu_ = NAN;
  float concentration_ = NAN;
  uint16_t spectrum_[12] = {};
  int colorIntensity_ = 0;
  float colorRate_ = 0.0f;
};
