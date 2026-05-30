#include "ADS1220Module.h"

ADS1220Module::ADS1220Module(SPIClass& spi, const ADS1220Pins& pins)
    : spi_(spi), pins_(pins) {}

void ADS1220Module::begin() {
  pinMode(pins_.cs, OUTPUT);
  digitalWrite(pins_.cs, HIGH);
  pinMode(pins_.drdy, INPUT_PULLUP);

  spi_.begin(pins_.sclk, pins_.miso, pins_.mosi, -1);
  delay(10);

  sendCommand(ADS_CMD_RESET);
  delay(2);

  // Ground-referenced pH/TDS inputs need the PGA bypassed. Use 90 SPS so
  // single-shot conversions finish well within the normal read timeout.
  writeRegister(0, AIN0_AIN1 | ADS_REG0_PGA_BYPASS);
  writeRegister(1, ADS_REG1_DR_90SPS);
  delay(2);
}

uint8_t ADS1220Module::readRegister(uint8_t reg) {
  spi_.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(pins_.cs, LOW);
  spi_.transfer(registerCommand(ADS_CMD_RREG_BASE, reg, 1));
  uint8_t v = spi_.transfer(0x00);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();
  return v;
}

float ADS1220Module::readVoltage(uint8_t muxSetting, uint32_t timeoutMs) {
  writeRegister(0, muxSetting | ADS_REG0_PGA_BYPASS);

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
  spi_.transfer(registerCommand(ADS_CMD_WREG_BASE, reg, 1));
  spi_.transfer(value);
  digitalWrite(pins_.cs, HIGH);
  spi_.endTransaction();
}

uint8_t ADS1220Module::registerCommand(uint8_t base, uint8_t reg, uint8_t count) {
  return base | ((reg & 0x03) << 2) | ((count - 1) & 0x03);
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
    yield();
  }
  return true;
}

