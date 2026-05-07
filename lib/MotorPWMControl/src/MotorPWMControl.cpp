#include "MotorPWMControl.h"

MotorPWMControl::MotorPWMControl(uint8_t pwmPin, uint8_t pwmChannel,
                                 uint32_t pwmFreqHz,
                                 uint8_t pwmResolutionBits)
    : _pwmPin(pwmPin),
      _pwmChannel(pwmChannel),
      _pwmFreqHz(pwmFreqHz),
      _pwmResolutionBits(pwmResolutionBits),
      _maxDuty((1UL << pwmResolutionBits) - 1),
      _currentPercent(0.0f) {}

bool MotorPWMControl::begin() {
  const bool setupOk = ledcSetup(_pwmChannel, _pwmFreqHz, _pwmResolutionBits) >
                       0.0;
  if (!setupOk) {
    return false;
  }

  ledcAttachPin(_pwmPin, _pwmChannel);
  stop();
  return true;
}

void MotorPWMControl::setSpeedPercent(float percent) {
  if (percent < 0.0f) {
    percent = 0.0f;
  } else if (percent > 100.0f) {
    percent = 100.0f;
  }

  const uint32_t duty =
      static_cast<uint32_t>((percent / 100.0f) * static_cast<float>(_maxDuty));
  ledcWrite(_pwmChannel, duty);
  _currentPercent = percent;
}

void MotorPWMControl::stop() { setSpeedPercent(0.0f); }

float MotorPWMControl::getSpeedPercent() const { return _currentPercent; }
