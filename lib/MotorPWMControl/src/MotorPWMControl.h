#ifndef MOTOR_PWM_CONTROL_H
#define MOTOR_PWM_CONTROL_H

#include <Arduino.h>

class MotorPWMControl {
 public:
  MotorPWMControl(uint8_t pwmPin, uint8_t pwmChannel, uint32_t pwmFreqHz,
                  uint8_t pwmResolutionBits);

  bool begin();
  void setSpeedPercent(float percent);
  void stop();
  float getSpeedPercent() const;

 private:
  uint8_t _pwmPin;
  uint8_t _pwmChannel;
  uint32_t _pwmFreqHz;
  uint8_t _pwmResolutionBits;
  uint32_t _maxDuty;
  float _currentPercent;
};

#endif
