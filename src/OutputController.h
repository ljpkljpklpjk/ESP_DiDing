#pragma once

#include <Arduino.h>
#include "MotorPWMControl.h"
#include "PeristalticPumpControl.h"

class OutputController {
 public:
  OutputController();

  bool begin();
  void setPwm1Percent(float percent);
  void setPumpPercent(float percent);
  void stopAll();

  float pwm1Percent() const { return pwm1Percent_; }
  float pumpPercent() const { return pumpPercent_; }

 private:
  static float clampPercent(float percent);

  MotorPWMControl pwm1_;
  PeristalticPumpControl pump_;
  float pwm1Percent_ = 0.0f;
  float pumpPercent_ = 0.0f;
};
