#include "OutputController.h"

#include "AppConfig.h"

OutputController::OutputController()
    : pwm1_(AppConfig::PWM1_PIN, AppConfig::PWM1_CHANNEL,
            AppConfig::PWM_FREQ_HZ, AppConfig::PWM_RES_BITS),
      pump_(AppConfig::PUMP_SIGNAL_PIN, AppConfig::PUMP_PWM_CHANNEL,
            AppConfig::PUMP_PPM_FREQ_HZ, AppConfig::PUMP_PWM_RES_BITS) {}

void OutputController::ensureMutex() {
  if (!mutex_) {
    mutex_ = xSemaphoreCreateRecursiveMutex();
  }
}

void OutputController::lock() {
  ensureMutex();
  if (mutex_) {
    xSemaphoreTakeRecursive(mutex_, portMAX_DELAY);
  }
}

void OutputController::unlock() {
  if (mutex_) {
    xSemaphoreGiveRecursive(mutex_);
  }
}

bool OutputController::begin() {
  ensureMutex();
  if (!pwm1_.begin() || !pump_.begin()) {
    return false;
  }
  lastDoseUpdateMs_ = millis();
  stopAll();
  return true;
}

void OutputController::setPwm1Percent(float percent) {
  lock();
  pwm1Percent_ = clampPercent(percent);
  pwm1_.setSpeedPercent(pwm1Percent_);
  unlock();
}

void OutputController::setPumpPercent(float percent) {
  lock();
  updateDoseLocked(millis());
  pumpPercent_ = clampPercent(percent);
  pump_.setSpeedPercent(pumpPercent_);
  unlock();
}

void OutputController::stopAll() {
  lock();
  setPwm1Percent(0.0f);
  setPumpPercent(0.0f);
  unlock();
}

void OutputController::resetDosingVolume() {
  lock();
  dosingVolumeMl_ = 0.0f;
  lastDoseUpdateMs_ = millis();
  unlock();
}

float OutputController::pwm1Percent() {
  lock();
  const float result = pwm1Percent_;
  unlock();
  return result;
}

float OutputController::pumpPercent() {
  lock();
  const float result = pumpPercent_;
  unlock();
  return result;
}

float OutputController::flowMlPerMin() {
  lock();
  const float result = pumpPercent_ * AppConfig::PUMP_MAX_FLOW_ML_MIN / 100.0f;
  unlock();
  return result;
}

float OutputController::dosingVolumeMl() {
  lock();
  updateDoseLocked(millis());
  const float result = dosingVolumeMl_;
  unlock();
  return result;
}

float OutputController::clampPercent(float percent) {
  if (percent < 0.0f) return 0.0f;
  if (percent > 100.0f) return 100.0f;
  return percent;
}

void OutputController::updateDoseLocked(uint32_t nowMs) {
  if (lastDoseUpdateMs_ == 0) {
    lastDoseUpdateMs_ = nowMs;
    return;
  }
  const uint32_t elapsedMs = nowMs - lastDoseUpdateMs_;
  if (elapsedMs == 0) {
    return;
  }
  const float flowMlPerMin =
      pumpPercent_ * AppConfig::PUMP_MAX_FLOW_ML_MIN / 100.0f;
  dosingVolumeMl_ += flowMlPerMin * static_cast<float>(elapsedMs) / 60000.0f;
  lastDoseUpdateMs_ = nowMs;
}
