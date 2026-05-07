#pragma once

#include <Arduino.h>
#include <SPI.h>

struct ADS1220Pins {
  int cs;
  int drdy;
  int sclk;
  int miso;
  int mosi;
};

struct PHCalibrationTwoPoint {
  float ph1;
  float v1;
  float ph2;
  float v2;
  float tempC;
};

class ADS1220Module {
 public:
  enum MuxChannel : uint8_t {
    AIN0_AIN1 = 0x00,
    AIN2_AIN3 = 0x30,
  };

  ADS1220Module(SPIClass& spi, const ADS1220Pins& pins);

  void begin();
  uint8_t readRegister(uint8_t reg);
  float readVoltage(uint8_t muxSetting, uint32_t timeoutMs = 200);

  void setPHCalibration(const PHCalibrationTwoPoint& cal);
  float voltageToPH(float voltage) const;

  float getPHSlope() const { return phSlope_; }
  float getPHIntercept() const { return phIntercept_; }
  float getCalTempC() const { return calTempC_; }

 private:
  static constexpr uint8_t ADS_CMD_RESET = 0x06;
  static constexpr uint8_t ADS_CMD_START_SYNC = 0x08;
  static constexpr uint8_t ADS_CMD_RDATA = 0x10;
  static constexpr uint8_t ADS_CMD_RREG_BASE = 0x20;
  static constexpr uint8_t ADS_CMD_WREG_BASE = 0x40;

  SPIClass& spi_;
  ADS1220Pins pins_;
  float phSlope_ = 0.0f;
  float phIntercept_ = 7.0f;
  float calTempC_ = 25.0f;

  void sendCommand(uint8_t cmd);
  void writeRegister(uint8_t reg, uint8_t value);
  int32_t read24();
  bool waitDrdyLow(uint32_t timeoutMs) const;
};

