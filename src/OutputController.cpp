#include "OutputController.h"

#include "AppConfig.h"

OutputController::OutputController()
    : pwm1_(AppConfig::PWM1_PIN, AppConfig::PWM1_CHANNEL,
            AppConfig::PWM_FREQ_HZ, AppConfig::PWM_RES_BITS),
      pump_(AppConfig::PUMP_SIGNAL_PIN, AppConfig::PUMP_PWM_CHANNEL,
            AppConfig::PUMP_PPM_FREQ_HZ, AppConfig::PUMP_PWM_RES_BITS) {}

bool OutputController::begin() {
  if (!pwm1_.begin() || !pump_.begin()) {
    return false;
  }
  stopAll();
  return true;
}

void OutputController::setPwm1Percent(float percent) {
  pwm1Percent_ = clampPercent(percent);
  pwm1_.setSpeedPercent(pwm1Percent_);
}

void OutputController::setPumpPercent(float percent) {
  pumpPercent_ = clampPercent(percent);
  pump_.setSpeedPercent(pumpPercent_);
}

void OutputController::stopAll() {
  setPwm1Percent(0.0f);
  setPumpPercent(0.0f);
}

float OutputController::clampPercent(float percent) {
  if (percent < 0.0f) return 0.0f;
  if (percent > 100.0f) return 100.0f;
  return percent;
}
