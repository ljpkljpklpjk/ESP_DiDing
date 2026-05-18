#include "Telemetry.h"

#include <Arduino.h>

#include "SerialProtocol.h"

void buildTelemetry(JsonDocument &doc, const SensorSampler &sensors,
                    const OpticalThermalSampler &opticalThermal,
                    const OutputController &outputs,
                    SliderController &slider,
                    const NetworkOtaManager &network) {
  doc["type"] = "telemetry";
  doc["ms"] = millis();
  SerialProtocol::setFloatOrNull(doc, "ph", sensors.ph());
  SerialProtocol::setFloatOrNull(doc, "voltage", sensors.voltage());
  SerialProtocol::setFloatOrNull(doc, "temperature_c", sensors.temperatureC());
  opticalThermal.addTelemetry(doc);
  doc["pwm1_percent"] = outputs.pwm1Percent();
  doc["pump_percent"] = outputs.pumpPercent();
  doc["wifi_connected"] = network.wifiConnected();
  doc["ip"] = network.ipText();
  doc["ota_ready"] = network.otaReady();
  slider.addTelemetry(doc);
}
