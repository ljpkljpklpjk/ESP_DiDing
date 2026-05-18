#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>

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
  bool enabled() const { return enabled_; }
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

  float speed() const { return speed_; }
  long currentPosition() { return stepper_.currentPosition(); }
  long targetPosition() { return stepper_.targetPosition(); }
  long distanceToGo() { return stepper_.distanceToGo(); }

 private:
  void clearMove(bool interrupted, SliderEvent *event = nullptr);

  AccelStepper stepper_;
  bool enabled_ = false;
  float speed_;
  bool moveActive_ = false;
  long moveCommandId_ = -1;
  bool stopActive_ = false;
  long stopCommandId_ = -1;
};
