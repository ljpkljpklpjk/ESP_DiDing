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

  float pwm1Percent();
  float pumpPercent();

 private:
  static float clampPercent(float percent);
  void ensureMutex();
  void lock();
  void unlock();

  MotorPWMControl pwm1_;
  PeristalticPumpControl pump_;
  float pwm1Percent_ = 0.0f;
  float pumpPercent_ = 0.0f;
  SemaphoreHandle_t mutex_ = nullptr;
};
