#include "SliderController.h"

#include <math.h>

#include "AppConfig.h"

SliderController::SliderController()
    : stepper_(AccelStepper::DRIVER, AppConfig::SLIDER_STEP_PIN,
               AppConfig::SLIDER_DIR_PIN),
      speed_(AppConfig::SLIDER_DEFAULT_SPEED) {}

void SliderController::ensureMutex() {
  if (!mutex_) {
    mutex_ = xSemaphoreCreateRecursiveMutex();
  }
}

void SliderController::lock() {
  ensureMutex();
  if (mutex_) {
    xSemaphoreTakeRecursive(mutex_, portMAX_DELAY);
  }
}

void SliderController::unlock() {
  if (mutex_) {
    xSemaphoreGiveRecursive(mutex_);
  }
}

void SliderController::begin() {
  ensureMutex();
  pinMode(AppConfig::SLIDER_ENABLE_PIN, OUTPUT);
  stepper_.setMaxSpeed(speed_);
  stepper_.setAcceleration(AppConfig::SLIDER_DEFAULT_ACCEL);
  stepper_.setEnablePin(AppConfig::SLIDER_ENABLE_PIN);
  stepper_.setPinsInverted(false, false, AppConfig::SLIDER_ENABLE_ACTIVE_LOW);
  setEnabled(false);
}

void SliderController::run() {
  lock();
  const bool enabled = enabled_;
  if (enabled) {
    stepper_.run();
  }
  unlock();
}

bool SliderController::busy() {
  lock();
  const bool result = moveActive_ || stopActive_ || stepper_.distanceToGo() != 0;
  unlock();
  return result;
}

void SliderController::setEnabled(bool enabled) {
  lock();
  enabled_ = enabled;
  digitalWrite(AppConfig::SLIDER_ENABLE_PIN,
               enabled == AppConfig::SLIDER_ENABLE_ACTIVE_LOW ? LOW : HIGH);
  unlock();
}

bool SliderController::enabled() {
  lock();
  const bool result = enabled_;
  unlock();
  return result;
}

void SliderController::setSpeed(float speed) {
  lock();
  speed_ = speed;
  stepper_.setMaxSpeed(speed_);
  unlock();
}

bool SliderController::speedInRange(float speed) const {
  return speed >= AppConfig::SLIDER_MIN_SPEED && speed <= AppConfig::SLIDER_MAX_SPEED;
}

void SliderController::setAcceleration(float accel) {
  lock();
  stepper_.setAcceleration(accel);
  unlock();
}

void SliderController::moveSteps(long steps, long id) {
  lock();
  setEnabled(true);
  clearMove(true);
  stepper_.move(steps);
  moveActive_ = true;
  moveCommandId_ = id;
  unlock();
}

void SliderController::moveMm(float mm, long id) {
  moveSteps(lround(mm * AppConfig::SLIDER_STEPS_PER_MM), id);
}

bool SliderController::moveTime(float mm, float sec, long id) {
  if (sec <= 0.0f) {
    return false;
  }

  const long steps = lround(mm * AppConfig::SLIDER_STEPS_PER_MM);
  const float requiredSpeed = fabs(static_cast<float>(steps)) / sec;
  if (!speedInRange(requiredSpeed)) {
    return false;
  }

  setSpeed(requiredSpeed);
  moveSteps(steps, id);
  return true;
}

void SliderController::moveContinuous(int direction) {
  lock();
  setEnabled(true);
  clearMove(true);
  stepper_.setMaxSpeed(speed_);
  stepper_.moveTo(stepper_.currentPosition() + direction * AppConfig::SLIDER_CONTINUOUS_TRAVEL);
  unlock();
}

void SliderController::stop(long id) {
  lock();
  stepper_.stop();
  stopActive_ = true;
  stopCommandId_ = id;
  unlock();
}

void SliderController::halt() {
  lock();
  stepper_.setCurrentPosition(stepper_.currentPosition());
  stepper_.moveTo(stepper_.currentPosition());
  clearMove(true);
  unlock();
}

void SliderController::zero() {
  lock();
  stepper_.setCurrentPosition(0);
  unlock();
}

SliderEvent SliderController::updateCompletion() {
  lock();
  SliderEvent event;
  if (stopActive_ && stepper_.distanceToGo() == 0) {
    event.active = true;
    event.id = stopCommandId_;
    event.ok = true;
    stopActive_ = false;
    stopCommandId_ = -1;
    clearMove(false);
    unlock();
    return event;
  }

  if (moveActive_ && stepper_.distanceToGo() == 0) {
    event.active = true;
    event.id = moveCommandId_;
    event.ok = true;
    moveActive_ = false;
    moveCommandId_ = -1;
  }
  unlock();
  return event;
}

void SliderController::addTelemetry(JsonDocument &doc) {
  lock();
  JsonObject slider = doc["slider"].to<JsonObject>();
  slider["pos"] = stepper_.currentPosition();
  slider["target"] = stepper_.targetPosition();
  slider["distance"] = stepper_.distanceToGo();
  slider["moving"] = stepper_.distanceToGo() != 0;
  slider["enabled"] = enabled_;
  slider["speed"] = speed_;
  slider["steps_per_mm"] = AppConfig::SLIDER_STEPS_PER_MM;
  unlock();
}

float SliderController::speed() {
  lock();
  const float result = speed_;
  unlock();
  return result;
}

long SliderController::currentPosition() {
  lock();
  const long result = stepper_.currentPosition();
  unlock();
  return result;
}

long SliderController::targetPosition() {
  lock();
  const long result = stepper_.targetPosition();
  unlock();
  return result;
}

long SliderController::distanceToGo() {
  lock();
  const long result = stepper_.distanceToGo();
  unlock();
  return result;
}

void SliderController::clearMove(bool interrupted, SliderEvent *event) {
  if (interrupted && moveActive_ && event) {
    event->active = true;
    event->id = moveCommandId_;
    event->ok = false;
  }
  moveActive_ = false;
  moveCommandId_ = -1;
  stopActive_ = false;
  stopCommandId_ = -1;
}
