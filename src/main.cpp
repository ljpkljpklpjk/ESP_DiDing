#include <Arduino.h>

#include "TitratorApp.h"

static TitratorApp app;

void setup() {
  Serial.begin(115200);
  app.begin();
}

void loop() {
  app.loop();
}
