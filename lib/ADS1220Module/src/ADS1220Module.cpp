#include "ADS1220Module.h"

ADS1220Module::ADS1220Module(SPIClass& spi, const ADS1220Pins& pins)
    : spi_(spi), pins_(pins) {}

void ADS1220Module::begin() {
  pinMode(pins_.cs, OUTPUT);
  digitalWrite(pins_.cs, HIGH);
  pinMode(pins_.drdy, INPUT);

  spi_.begin(pins_.sclk, pins_.miso, pins_.mosi, -1);
  delay(10);

  sendCommand(ADS_CMD_RESET);
  delay(2);

  // Minimal deterministic init: MUX=AIN0-AIN1, gain=1, PGA enabled.
  writeRegister(0, 0x00);
  delay(2);
}

uint8_t ADS1220Module::readRegister(uint8_t reg) {
  spi_.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(pins_.cs, LOW);
  spi_.transfer((uint8_t)(ADS_CMD_RREG_BASE | (reg & 0x03)));
  spi_.transfer(0x00);
  uint8_t v = spi_.transfer(0x00);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();
  return v;
}

float ADS1220Module::readVoltage(uint8_t muxSetting, uint32_t timeoutMs) {
  writeRegister(0, muxSetting);

  sendCommand(ADS_CMD_START_SYNC);
  if (!waitDrdyLow(timeoutMs)) {
    return NAN;
  }

  int32_t raw = read24();
  if (raw & 0x00800000) {
    raw |= 0xFF000000;
  }

  const float vref = 2.048f;
  const float fullScale = 8388607.0f;  // 2^23 - 1
  return ((float)raw) * (vref / fullScale);
}

void ADS1220Module::setPHCalibration(const PHCalibrationTwoPoint& cal) {
  calTempC_ = cal.tempC;
  phSlope_ = (cal.ph1 - cal.ph2) / (cal.v1 - cal.v2);
  phIntercept_ = cal.ph1 - phSlope_ * cal.v1;
}

float ADS1220Module::voltageToPH(float voltage) const {
  float ph = phSlope_ * voltage + phIntercept_;
  if (ph < 0.0f) ph = 0.0f;
  if (ph > 14.0f) ph = 14.0f;
  return ph;
}

void ADS1220Module::sendCommand(uint8_t cmd) {
  spi_.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(pins_.cs, LOW);
  spi_.transfer(cmd);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();
}

void ADS1220Module::writeRegister(uint8_t reg, uint8_t value) {
  spi_.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(pins_.cs, LOW);
  spi_.transfer((uint8_t)(ADS_CMD_WREG_BASE | (reg & 0x03)));
  spi_.transfer(0x00);
  spi_.transfer(value);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();
}

int32_t ADS1220Module::read24() {
  spi_.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(pins_.cs, LOW);
  spi_.transfer(ADS_CMD_RDATA);
  uint8_t b2 = spi_.transfer(0x00);
  uint8_t b1 = spi_.transfer(0x00);
  uint8_t b0 = spi_.transfer(0x00);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();

  return ((int32_t)b2 << 16) | ((int32_t)b1 << 8) | (int32_t)b0;
}

bool ADS1220Module::waitDrdyLow(uint32_t timeoutMs) const {
  uint32_t start = millis();
  while (digitalRead(pins_.drdy) == HIGH) {
    if (millis() - start > timeoutMs) return false;
    delay(1);
  }
  return true;
}

