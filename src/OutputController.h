#pragma once

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include "MotorPWMControl.h"
#include "PeristalticPumpControl.h"

class OutputController {
 public:
  OutputController();

  bool begin();
  void setPwm1Percent(float percent);
  void setPumpPercent(float percent);
  void stopAll();
  void resetDosingVolume();

  float pwm1Percent();
  float pumpPercent();
  float flowMlPerMin();
  float dosingVolumeMl();

 private:
  static float clampPercent(float percent);
  void ensureMutex();
  void lock();
  void unlock();
  void updateDoseLocked(uint32_t nowMs);

  MotorPWMControl pwm1_;
  PeristalticPumpControl pump_;
  float pwm1Percent_ = 0.0f;
  float pumpPercent_ = 0.0f;
  float dosingVolumeMl_ = 0.0f;
  uint32_t lastDoseUpdateMs_ = 0;
  SemaphoreHandle_t mutex_ = nullptr;
};
