#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

struct SliderEvent {
  bool active = false;
  long id = -1;
  bool ok = true;
};

class SliderController {
 public:
  SliderController();

  void begin();
  void run();
  bool busy();
  void setEnabled(bool enabled);
  bool enabled();
  void setSpeed(float speed);
  bool speedInRange(float speed) const;
  void setAcceleration(float accel);
  void moveSteps(long steps, long id);
  void moveMm(float mm, long id);
  bool moveTime(float mm, float sec, long id);
  void moveContinuous(int direction);
  void stop(long id);
  void halt();
  void zero();
  SliderEvent updateCompletion();
  void addTelemetry(JsonDocument &doc);

  float speed();
  long currentPosition();
  long targetPosition();
  long distanceToGo();

 private:
  void clearMove(bool interrupted, SliderEvent *event = nullptr);
  void ensureMutex();
  void lock();
  void unlock();

  AccelStepper stepper_;
  bool enabled_ = false;
  float speed_;
  bool moveActive_ = false;
  long moveCommandId_ = -1;
  bool stopActive_ = false;
  long stopCommandId_ = -1;
  SemaphoreHandle_t mutex_ = nullptr;
};
