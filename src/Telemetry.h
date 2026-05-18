#pragma once

#include <ArduinoJson.h>

#include "NetworkOtaManager.h"
#include "OpticalThermalSampler.h"
#include "OutputController.h"
#include "SensorSampler.h"
#include "SliderController.h"

void buildTelemetry(JsonDocument &doc, const SensorSampler &sensors,
                    const OpticalThermalSampler &opticalThermal,
                    OutputController &outputs,
                    SliderController &slider,
                    const NetworkOtaManager &network);
