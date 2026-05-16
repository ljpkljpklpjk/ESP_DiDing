#include "DS18B20Module.h"

#include <OneWire.h>
#include <DallasTemperature.h>

class DS18B20Module::Impl {
 public:
  explicit Impl(uint8_t pin) : oneWire(pin), dallas(&oneWire) {}

  OneWire oneWire;
  DallasTemperature dallas;
};

DS18B20Module::DS18B20Module(uint8_t dataPin)
    : dataPin_(dataPin), ready_(false), impl_(new Impl(dataPin)) {}

bool DS18B20Module::begin() {
  if (!impl_) {
    ready_ = false;
    return false;
  }

  impl_->dallas.begin();
  const uint8_t count = impl_->dallas.getDeviceCount();
  ready_ = (count > 0);

  impl_->dallas.setWaitForConversion(false);
  return ready_;
}

float DS18B20Module::readCelsius() {
  if (!ready_ || !impl_) {
    return NAN;
  }

  impl_->dallas.requestTemperatures();
  const float t = impl_->dallas.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C) {
    return NAN;
  }
  return t;
}
