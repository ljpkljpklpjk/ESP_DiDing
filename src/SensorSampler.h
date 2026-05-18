#pragma once

#include <Arduino.h>
#include <SPI.h>

#include "ADS1220Module.h"
#include "DS18B20Module.h"

class SensorSampler {
 public:
  SensorSampler();

  bool begin();
  void updatePh();
  void updateTemperature();

  float voltage() const { return voltage_; }
  float ph() const { return ph_; }
  float temperatureC() const { return temperatureC_; }
  bool ds18b20Ready() const { return ds18b20Ready_; }

 private:
  SPIClass adsSpi_;
  ADS1220Module ads_;
  DS18B20Module ds18b20_;
  uint32_t lastPhSampleMs_ = 0;
  uint32_t lastTempSampleMs_ = 0;
  uint32_t lastTempRequestMs_ = 0;
  bool tempConversionPending_ = false;
  float voltage_ = NAN;
  float ph_ = NAN;
  float temperatureC_ = NAN;
  bool ds18b20Ready_ = false;
};
