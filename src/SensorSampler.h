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
  void updateTds();

  float voltage() const { return voltage_; }
  float ph() const { return ph_; }
  float temperatureC() const { return temperatureC_; }
  float tdsVoltage() const { return tdsVoltage_; }
  float tdsPpm() const { return tdsPpm_; }
  float tdsSlopeMgLMin() const { return tdsSlopeMgLMin_; }
  bool ds18b20Ready() const { return ds18b20Ready_; }

 private:
  SPIClass adsSpi_;
  ADS1220Module ads_;
  DS18B20Module ds18b20_;
  uint32_t lastPhSampleMs_ = 0;
  uint32_t lastTdsSampleMs_ = 0;
  uint32_t lastTempSampleMs_ = 0;
  uint32_t lastTempRequestMs_ = 0;
  bool tempConversionPending_ = false;
  float voltage_ = NAN;
  float ph_ = NAN;
  float temperatureC_ = NAN;
  float tdsVoltage_ = NAN;
  float tdsPpm_ = NAN;
  float lastTdsPpm_ = NAN;
  uint32_t lastTdsRateMs_ = 0;
  float tdsSlopeMgLMin_ = NAN;
  bool ds18b20Ready_ = false;
};
