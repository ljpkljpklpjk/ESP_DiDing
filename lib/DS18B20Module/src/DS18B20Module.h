#pragma once

#include <Arduino.h>

class DS18B20Module {
 public:
  explicit DS18B20Module(uint8_t dataPin);

  bool begin();
  void requestTemperature();
  float readLastCelsius();
  float readCelsius();

 private:
  uint8_t dataPin_;
  bool ready_;

  class Impl;
  Impl* impl_;
};
