#ifndef PERISTALTIC_PUMP_CONTROL_H
#define PERISTALTIC_PUMP_CONTROL_H

#include <Arduino.h>

class PeristalticPumpControl {
 public:
  PeristalticPumpControl(uint8_t signalPin, uint8_t pwmChannel,
                         uint32_t ppmFreqHz, uint8_t pwmResolutionBits);

  bool begin();
  void setSpeedPercent(float percent);
  void stop();
  float getSpeedPercent() const;

 private:
  void writePulseWidthUs(uint16_t pulseWidthUs);

  uint8_t _signalPin;
  uint8_t _pwmChannel;
  uint32_t _ppmFreqHz;
  uint8_t _pwmResolutionBits;
  uint32_t _maxDuty;
  uint32_t _periodUs;
  float _currentPercent;
};

#endif
