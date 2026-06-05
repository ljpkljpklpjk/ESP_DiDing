#include <Arduino.h>

#include "TitratorApp.h"

static TitratorApp app;

void setup() {
  app.begin();
}

void loop() {
  app.loop();
}
