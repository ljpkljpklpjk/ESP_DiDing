#include "PeristalticPumpControl.h"

namespace {
constexpr uint16_t PUMP_MAX_FORWARD_US = 500;
constexpr uint16_t PUMP_STOP_US = 1500;
}  // namespace

PeristalticPumpControl::PeristalticPumpControl(uint8_t signalPin,
                                               uint8_t pwmChannel,
                                               uint32_t ppmFreqHz,
                                               uint8_t pwmResolutionBits)
    : _signalPin(signalPin),
      _pwmChannel(pwmChannel),
      _ppmFreqHz(ppmFreqHz),
      _pwmResolutionBits(pwmResolutionBits),
      _maxDuty((1UL << pwmResolutionBits) - 1),
      _periodUs(1000000UL / ppmFreqHz),
      _currentPercent(0.0f) {}

bool PeristalticPumpControl::begin() {
  const bool setupOk = ledcSetup(_pwmChannel, _ppmFreqHz, _pwmResolutionBits) >
                       0.0;
  if (!setupOk) {
    return false;
  }

  ledcAttachPin(_signalPin, _pwmChannel);
  stop();
  return true;
}

void PeristalticPumpControl::setSpeedPercent(float percent) {
  if (percent < 0.0f) {
    percent = 0.0f;
  } else if (percent > 100.0f) {
    percent = 100.0f;
  }

  const float pulseWidthUs =
      static_cast<float>(PUMP_STOP_US) -
      (percent / 100.0f) *
          static_cast<float>(PUMP_STOP_US - PUMP_MAX_FORWARD_US);
  writePulseWidthUs(static_cast<uint16_t>(pulseWidthUs + 0.5f));
  _currentPercent = percent;
}

void PeristalticPumpControl::stop() { setSpeedPercent(0.0f); }

float PeristalticPumpControl::getSpeedPercent() const { return _currentPercent; }

void PeristalticPumpControl::writePulseWidthUs(uint16_t pulseWidthUs) {
  const uint32_t duty =
      (static_cast<uint32_t>(pulseWidthUs) * _maxDuty) / _periodUs;
  ledcWrite(_pwmChannel, duty);
}
