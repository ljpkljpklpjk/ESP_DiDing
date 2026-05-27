#pragma once

#include <Arduino.h>
#include "ADS1220Module.h"

namespace AppConfig {

enum class CommInterface {
  UsbSerial,
  Rs485Uart,
};

inline ADS1220Pins adsPins() {
  return ADS1220Pins{
      .cs = 21,
      .drdy = 15,
      .sclk = 4,
      .miso = 13,
      .mosi = 14,
  };
}

inline PHCalibrationTwoPoint phCalibration() {
  return PHCalibrationTwoPoint{
      .ph1 = 10.00f,
      .v1 = 0.46935f,
      .ph2 = 6.86f,
      .v2 = 0.93646f,
      .tempC = 25.0f,
  };
}

static constexpr uint8_t PWM1_PIN = 5;
static constexpr uint8_t PWM1_CHANNEL = 0;
static constexpr uint32_t PWM_FREQ_HZ = 20000;
static constexpr uint8_t PWM_RES_BITS = 10;
static constexpr uint8_t PUMP_SIGNAL_PIN = 6;
static constexpr uint8_t PUMP_PWM_CHANNEL = 1;
static constexpr uint32_t PUMP_PPM_FREQ_HZ = 500;
static constexpr uint8_t PUMP_PWM_RES_BITS = 10;

static constexpr bool SERIAL_DEBUG_TEXT = false;
static constexpr CommInterface COMM_INTERFACE = CommInterface::Rs485Uart;
static constexpr uint32_t COMM_BAUDRATE = 115200;
static constexpr uint8_t RS485_UART_NUM = 1;
static constexpr int8_t RS485_RX_PIN = 44;
static constexpr int8_t RS485_TX_PIN = 43;
static constexpr int8_t RS485_DE_PIN = 16;
static constexpr int8_t RS485_RE_PIN = -1;
static constexpr bool RS485_ENABLE_ACTIVE_HIGH = true;
static constexpr uint32_t RS485_TX_SETTLE_US = 100;
static constexpr uint32_t COMM_BOOT_OK_DURATION_MS = 3000;
static constexpr uint32_t COMM_BOOT_OK_INTERVAL_MS = 250;
static constexpr uint32_t TELEMETRY_INTERVAL_MS = 1000;
static constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 10000;
static constexpr size_t SERIAL_RX_BUF_SIZE = 320;
static constexpr size_t SERIAL_BYTES_PER_LOOP = 32;
static constexpr uint32_t OTA_HANDLE_INTERVAL_MS = 10;
static constexpr uint32_t OTA_HANDLE_MOVING_INTERVAL_MS = 50;
static constexpr uint32_t ADS1220_READ_TIMEOUT_MS = 40;
static constexpr uint32_t TEMP_REQUEST_INTERVAL_MS = 1000;
static constexpr uint32_t TEMP_CONVERSION_DELAY_MS = 800;
static constexpr uint8_t DS18B20_PIN = 2;
static constexpr uint8_t I2C_SDA_PIN = 7;
static constexpr uint8_t I2C_SCL_PIN = 8;
static constexpr uint32_t MLX90640_SAMPLE_INTERVAL_MS = 500;
static constexpr uint32_t AS7341_SAMPLE_INTERVAL_MS = 200;
static constexpr uint32_t TDS_SAMPLE_INTERVAL_MS = 1000;
static constexpr uint32_t BME280_SAMPLE_INTERVAL_MS = 1000;
static constexpr uint32_t TOF_SAMPLE_INTERVAL_MS = 250;
static constexpr uint8_t BME280_I2C_ADDR_PRIMARY = 0x76;
static constexpr uint8_t BME280_I2C_ADDR_SECONDARY = 0x77;
static constexpr uint8_t TOF_I2C_ADDR = 0x29;
static constexpr float TDS_TEMP_COEFFICIENT = 0.02f;
static constexpr float TDS_CALIBRATION_FACTOR = 0.5f;
static constexpr float ABSORBANCE_REFERENCE_INTENSITY = 65535.0f;
static constexpr float CONCENTRATION_SLOPE = 1.0f;
static constexpr float CONCENTRATION_INTERCEPT = 0.0f;
static constexpr float PUMP_MAX_FLOW_ML_MIN = 100.0f;

static constexpr const char *WIFI_SSID = "Lab807_2.4G";
static constexpr const char *WIFI_PASSWORD = "lab80700";
static constexpr const char *OTA_HOSTNAME = "esp-diding";
static constexpr const char *OTA_PASSWORD = "lab80700";

static constexpr uint8_t SLIDER_STEP_PIN = 10;
static constexpr uint8_t SLIDER_DIR_PIN = 11;
static constexpr uint8_t SLIDER_ENABLE_PIN = 12;
static constexpr bool SLIDER_ENABLE_ACTIVE_LOW = true;
static constexpr float SLIDER_DEFAULT_SPEED = 1000.0f;
static constexpr float SLIDER_DEFAULT_ACCEL = 500.0f;
static constexpr float SLIDER_MIN_SPEED = 1.0f;
static constexpr float SLIDER_MAX_SPEED = 5000.0f;
static constexpr long SLIDER_CONTINUOUS_TRAVEL = 1000000000L;
static constexpr float SLIDER_MOTOR_FULL_STEPS_PER_REV = 200.0f;
static constexpr float SLIDER_MICROSTEPS = 16.0f;
static constexpr float SLIDER_LEAD_SCREW_PITCH_MM = 2.0f;
static constexpr float SLIDER_STEPS_PER_MM =
    SLIDER_MOTOR_FULL_STEPS_PER_REV * SLIDER_MICROSTEPS /
    SLIDER_LEAD_SCREW_PITCH_MM;

}  // namespace AppConfig
