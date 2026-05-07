#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <lvgl.h>

#include "ADS1220Module.h"
#include "DS18B20Module.h"
#include "MotorPWMControl.h"

// ---------------- LCD(ST7796S) ----------------
static constexpr int PIN_LCD_SCK = 12;
static constexpr int PIN_LCD_MOSI = 11;
static constexpr int PIN_LCD_CS = 10;
static constexpr int PIN_LCD_DC = 9;
static constexpr int PIN_LCD_RST = 8;
static constexpr int PIN_LCD_BLC = 7;

// ---------------- Touch(FT6336) ----------------
static constexpr int PIN_TP_SCL = 18;
static constexpr int PIN_TP_SDA = 17;
static constexpr int PIN_TP_RST = 16;
static constexpr int PIN_TP_INT = 19;
static constexpr uint8_t FT6336_ADDR = 0x38;

static constexpr uint16_t TFT_WIDTH = 320;
static constexpr uint16_t TFT_HEIGHT = 480;

// ---------------- ADS1220 ----------------
// Note: these are default integration pins. Adjust to your real wiring if different.
static ADS1220Pins kAdsPins = {
    .cs = 21,
    .drdy = 15,
    .sclk = 4,
    .miso = 13,
    .mosi = 14,
};

static constexpr float ENV_TEMP_C = 25.0f;
static PHCalibrationTwoPoint kPhCal = {
    .ph1 = 10.00f,
    .v1 = 0.46935f,
    .ph2 = 6.86f,
    .v2 = 0.93646f,
    .tempC = ENV_TEMP_C,
};

// ---------------- Dual PWM ----------------
static constexpr uint8_t PWM1_PIN = 5;
static constexpr uint8_t PWM2_PIN = 6;
static constexpr uint8_t PWM1_CHANNEL = 0;
static constexpr uint8_t PWM2_CHANNEL = 1;
static constexpr uint32_t PWM_FREQ_HZ = 20000;
static constexpr uint8_t PWM_RES_BITS = 10;
static constexpr float PWM_STEP_PERCENT = 5.0f;
static constexpr uint8_t DS18B20_PIN = 2;

static SPIClass lcdSpi(HSPI);
static SPIClass adsSpi(FSPI);
static ADS1220Module ads(adsSpi, kAdsPins);
static DS18B20Module ds18b20(DS18B20_PIN);
static MotorPWMControl pwm1(PWM1_PIN, PWM1_CHANNEL, PWM_FREQ_HZ, PWM_RES_BITS);
static MotorPWMControl pwm2(PWM2_PIN, PWM2_CHANNEL, PWM_FREQ_HZ, PWM_RES_BITS);

static lv_disp_draw_buf_t drawBuf;
static lv_disp_drv_t dispDrv;
static lv_indev_drv_t indevDrv;
static lv_color_t *buf1 = nullptr;
static lv_color_t *buf2 = nullptr;

static lv_obj_t *phLabel = nullptr;
static lv_obj_t *voltageLabel = nullptr;
static lv_obj_t *tempLabel = nullptr;
static lv_obj_t *pwm1Label = nullptr;
static lv_obj_t *pwm2Label = nullptr;

static float gPwm1Percent = 0.0f;
static float gPwm2Percent = 0.0f;

static uint32_t gLastSampleMs = 0;
static float gLastVoltage = NAN;
static float gLastPh = NAN;
static uint32_t gLastTempSampleMs = 0;
static float gLastTempC = NAN;

static inline void lcdCsLow() { digitalWrite(PIN_LCD_CS, LOW); }
static inline void lcdCsHigh() { digitalWrite(PIN_LCD_CS, HIGH); }
static inline void lcdDcLow() { digitalWrite(PIN_LCD_DC, LOW); }
static inline void lcdDcHigh() { digitalWrite(PIN_LCD_DC, HIGH); }

static void lcdWriteCmd(uint8_t cmd) {
  lcdDcLow();
  lcdCsLow();
  lcdSpi.write(cmd);
  lcdCsHigh();
}

static void lcdWriteData(uint8_t data) {
  lcdDcHigh();
  lcdCsLow();
  lcdSpi.write(data);
  lcdCsHigh();
}

static void lcdWriteDataN(const uint8_t *data, size_t len) {
  lcdDcHigh();
  lcdCsLow();
  lcdSpi.writeBytes(data, len);
  lcdCsHigh();
}

static void lcdSetAddrWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  lcdWriteCmd(0x2A);
  uint8_t col[4] = {
      static_cast<uint8_t>(x0 >> 8),
      static_cast<uint8_t>(x0 & 0xFF),
      static_cast<uint8_t>(x1 >> 8),
      static_cast<uint8_t>(x1 & 0xFF),
  };
  lcdWriteDataN(col, sizeof(col));

  lcdWriteCmd(0x2B);
  uint8_t row[4] = {
      static_cast<uint8_t>(y0 >> 8),
      static_cast<uint8_t>(y0 & 0xFF),
      static_cast<uint8_t>(y1 >> 8),
      static_cast<uint8_t>(y1 & 0xFF),
  };
  lcdWriteDataN(row, sizeof(row));

  lcdWriteCmd(0x2C);
}

static void lcdWriteRgb565LEBlock(const uint16_t *pixels, uint32_t count) {
  const uint8_t *raw = reinterpret_cast<const uint8_t *>(pixels);
  constexpr size_t CHUNK_PIXELS = 64;
  uint8_t swapped[CHUNK_PIXELS * 2];

  while (count > 0) {
    const uint32_t batch = (count > CHUNK_PIXELS) ? CHUNK_PIXELS : count;
    for (uint32_t i = 0; i < batch; ++i) {
      const uint8_t lo = raw[0];
      const uint8_t hi = raw[1];
      swapped[i * 2] = hi;
      swapped[i * 2 + 1] = lo;
      raw += 2;
    }
    lcdSpi.writeBytes(swapped, batch * 2);
    count -= batch;
  }
}

static void initLcd() {
  digitalWrite(PIN_LCD_RST, LOW);
  delay(20);
  digitalWrite(PIN_LCD_RST, HIGH);
  delay(120);

  lcdWriteCmd(0x11);
  delay(120);

  lcdWriteCmd(0xF0);
  lcdWriteData(0xC3);
  lcdWriteCmd(0xF0);
  lcdWriteData(0x96);

  lcdWriteCmd(0x36);
  lcdWriteData(0x48);

  lcdWriteCmd(0x3A);
  lcdWriteData(0x55);

  lcdWriteCmd(0xB1);
  lcdWriteData(0x90);
  lcdWriteData(0x10);

  lcdWriteCmd(0xB4);
  lcdWriteData(0x00);

  lcdWriteCmd(0xB7);
  lcdWriteData(0xC6);

  lcdWriteCmd(0xC0);
  lcdWriteData(0x80);
  lcdWriteData(0x64);

  lcdWriteCmd(0xC1);
  lcdWriteData(0x13);

  lcdWriteCmd(0xC2);
  lcdWriteData(0xA7);

  lcdWriteCmd(0xC5);
  lcdWriteData(0x08);

  lcdWriteCmd(0xE8);
  uint8_t e8[] = {0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33};
  lcdWriteDataN(e8, sizeof(e8));

  lcdWriteCmd(0xE0);
  uint8_t e0[] = {0xF0, 0x06, 0x0B, 0x07, 0x06, 0x05, 0x2E, 0x33, 0x47, 0x3A, 0x17, 0x16, 0x2E, 0x31};
  lcdWriteDataN(e0, sizeof(e0));

  lcdWriteCmd(0xE1);
  uint8_t e1[] = {0xF0, 0x09, 0x0D, 0x09, 0x08, 0x23, 0x2E, 0x33, 0x46, 0x38, 0x13, 0x13, 0x2C, 0x32};
  lcdWriteDataN(e1, sizeof(e1));

  lcdWriteCmd(0xF0);
  lcdWriteData(0x3C);
  lcdWriteCmd(0xF0);
  lcdWriteData(0x69);

  lcdWriteCmd(0x34);
  lcdWriteCmd(0x21);
  lcdWriteCmd(0x29);
  delay(50);
}

static bool readTouchPoint(uint16_t &x, uint16_t &y) {
  Wire.beginTransmission(FT6336_ADDR);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(static_cast<int>(FT6336_ADDR), 5) != 5) {
    return false;
  }

  uint8_t tdStatus = Wire.read();
  if ((tdStatus & 0x0F) == 0) {
    return false;
  }

  uint8_t xh = Wire.read();
  uint8_t xl = Wire.read();
  uint8_t yh = Wire.read();
  uint8_t yl = Wire.read();

  x = static_cast<uint16_t>(((xh & 0x0F) << 8) | xl);
  y = static_cast<uint16_t>(((yh & 0x0F) << 8) | yl);
  if (x >= TFT_WIDTH || y >= TFT_HEIGHT) {
    return false;
  }

  x = static_cast<uint16_t>(TFT_WIDTH - 1 - x);
  return true;
}

static void lvglFlush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *colorP) {
  const uint16_t w = static_cast<uint16_t>(area->x2 - area->x1 + 1);
  const uint16_t h = static_cast<uint16_t>(area->y2 - area->y1 + 1);
  const uint32_t pxCount = static_cast<uint32_t>(w) * static_cast<uint32_t>(h);

  lcdSetAddrWindow(static_cast<uint16_t>(area->x1), static_cast<uint16_t>(area->y1),
                   static_cast<uint16_t>(area->x2), static_cast<uint16_t>(area->y2));
  lcdDcHigh();
  lcdCsLow();
  lcdWriteRgb565LEBlock(reinterpret_cast<const uint16_t *>(colorP), pxCount);
  lcdCsHigh();

  lv_disp_flush_ready(disp);
}

static void lvglTouchRead(lv_indev_drv_t *drv, lv_indev_data_t *data) {
  (void)drv;
  uint16_t x = 0;
  uint16_t y = 0;
  if (readTouchPoint(x, y)) {
    data->state = LV_INDEV_STATE_PRESSED;
    data->point.x = static_cast<lv_coord_t>(x);
    data->point.y = static_cast<lv_coord_t>(y);
  } else {
    data->state = LV_INDEV_STATE_RELEASED;
  }
}

static float clampPercent(float p) {
  if (p < 0.0f) return 0.0f;
  if (p > 100.0f) return 100.0f;
  return p;
}

static void formatFixed(char *out, size_t outSize, float value, int decimals) {
  if (!out || outSize == 0) {
    return;
  }

  if (isnan(value) || isinf(value)) {
    snprintf(out, outSize, "--");
    return;
  }

  int scale = 1;
  for (int i = 0; i < decimals; ++i) {
    scale *= 10;
  }

  long scaled = lroundf(value * static_cast<float>(scale));
  bool neg = scaled < 0;
  if (neg) {
    scaled = -scaled;
  }

  long ip = scaled / scale;
  long fp = scaled % scale;

  if (decimals <= 0) {
    snprintf(out, outSize, "%s%ld", neg ? "-" : "", ip);
    return;
  }

  snprintf(out, outSize, "%s%ld.%0*ld", neg ? "-" : "", ip, decimals, fp);
}

static void refreshPwmLabels() {
  char pwm1Text[32];
  char pwm2Text[32];
  char v1[16];
  char v2[16];
  formatFixed(v1, sizeof(v1), gPwm1Percent, 1);
  formatFixed(v2, sizeof(v2), gPwm2Percent, 1);
  snprintf(pwm1Text, sizeof(pwm1Text), "PWM1 Duty: %s%%", v1);
  snprintf(pwm2Text, sizeof(pwm2Text), "PWM2 Duty: %s%%", v2);
  lv_label_set_text(pwm1Label, pwm1Text);
  lv_label_set_text(pwm2Label, pwm2Text);
}

static void applyPwm1(float delta) {
  gPwm1Percent = clampPercent(gPwm1Percent + delta);
  pwm1.setSpeedPercent(gPwm1Percent);
  refreshPwmLabels();
}

static void applyPwm2(float delta) {
  gPwm2Percent = clampPercent(gPwm2Percent + delta);
  pwm2.setSpeedPercent(gPwm2Percent);
  refreshPwmLabels();
}

static void onPwm1Minus(lv_event_t *e) {
  (void)e;
  applyPwm1(-PWM_STEP_PERCENT);
}

static void onPwm1Plus(lv_event_t *e) {
  (void)e;
  applyPwm1(PWM_STEP_PERCENT);
}

static void onPwm2Minus(lv_event_t *e) {
  (void)e;
  applyPwm2(-PWM_STEP_PERCENT);
}

static void onPwm2Plus(lv_event_t *e) {
  (void)e;
  applyPwm2(PWM_STEP_PERCENT);
}

static lv_obj_t *makeButton(lv_obj_t *parent, const char *txt, lv_event_cb_t cb) {
  lv_obj_t *btn = lv_btn_create(parent);
  lv_obj_set_size(btn, 100, 50);
  lv_obj_add_event_cb(btn, cb, LV_EVENT_CLICKED, nullptr);

  lv_obj_t *label = lv_label_create(btn);
  lv_label_set_text(label, txt);
  lv_obj_center(label);
  return btn;
}

static void buildUi() {
  lv_obj_set_style_bg_color(lv_scr_act(), lv_color_hex(0x101820), 0);

  lv_obj_t *title = lv_label_create(lv_scr_act());
  lv_label_set_text(title, "PH & Dual PWM Control");
  lv_obj_set_style_text_color(title, lv_color_hex(0xF2AA4C), 0);
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 14);

  phLabel = lv_label_create(lv_scr_act());
  lv_label_set_text(phLabel, "PH: --");
  lv_obj_set_style_text_color(phLabel, lv_color_white(), 0);
  lv_obj_align(phLabel, LV_ALIGN_TOP_LEFT, 20, 55);

  voltageLabel = lv_label_create(lv_scr_act());
  lv_label_set_text(voltageLabel, "Voltage: -- V");
  lv_obj_set_style_text_color(voltageLabel, lv_color_hex(0x88E1F2), 0);
  lv_obj_align(voltageLabel, LV_ALIGN_TOP_LEFT, 20, 85);

  tempLabel = lv_label_create(lv_scr_act());
  lv_label_set_text(tempLabel, "Temp: -- C");
  lv_obj_set_style_text_color(tempLabel, lv_color_hex(0x8FD98F), 0);
  lv_obj_align(tempLabel, LV_ALIGN_TOP_LEFT, 20, 115);

  pwm1Label = lv_label_create(lv_scr_act());
  lv_label_set_text(pwm1Label, "PWM1 Duty: 0.0%");
  lv_obj_set_style_text_color(pwm1Label, lv_color_hex(0xD0D8E0), 0);
  lv_obj_align(pwm1Label, LV_ALIGN_TOP_LEFT, 20, 175);

  pwm2Label = lv_label_create(lv_scr_act());
  lv_label_set_text(pwm2Label, "PWM2 Duty: 0.0%");
  lv_obj_set_style_text_color(pwm2Label, lv_color_hex(0xD0D8E0), 0);
  lv_obj_align(pwm2Label, LV_ALIGN_TOP_LEFT, 20, 290);

  lv_obj_t *btn1Minus = makeButton(lv_scr_act(), "PWM1 -", onPwm1Minus);
  lv_obj_align(btn1Minus, LV_ALIGN_TOP_LEFT, 20, 210);

  lv_obj_t *btn1Plus = makeButton(lv_scr_act(), "PWM1 +", onPwm1Plus);
  lv_obj_align(btn1Plus, LV_ALIGN_TOP_LEFT, 140, 210);

  lv_obj_t *btn2Minus = makeButton(lv_scr_act(), "PWM2 -", onPwm2Minus);
  lv_obj_align(btn2Minus, LV_ALIGN_TOP_LEFT, 20, 325);

  lv_obj_t *btn2Plus = makeButton(lv_scr_act(), "PWM2 +", onPwm2Plus);
  lv_obj_align(btn2Plus, LV_ALIGN_TOP_LEFT, 140, 325);
}

static void updatePhReading() {
  const uint32_t now = millis();
  if (now - gLastSampleMs < 500) {
    return;
  }
  gLastSampleMs = now;

  const float v = ads.readVoltage(ADS1220Module::AIN0_AIN1);
  if (isnan(v)) {
    gLastVoltage = NAN;
    gLastPh = NAN;
    lv_label_set_text(phLabel, "PH: ADS timeout");
    lv_label_set_text(voltageLabel, "Voltage: -- V");
    Serial.println("ADS1220 timeout (check DRDY pin/wiring)");
    return;
  }

  const float ph = ads.voltageToPH(v);
  gLastVoltage = v;
  gLastPh = ph;

  char phText[32];
  char voltageText[48];
  char phVal[16];
  char voltageVal[24];

  formatFixed(phVal, sizeof(phVal), gLastPh, 3);
  formatFixed(voltageVal, sizeof(voltageVal), gLastVoltage, 6);

  snprintf(phText, sizeof(phText), "PH: %s", phVal);
  snprintf(voltageText, sizeof(voltageText), "Voltage: %s V", voltageVal);

  lv_label_set_text(phLabel, phText);
  lv_label_set_text(voltageLabel, voltageText);

  Serial.printf("PH voltage=%.6f V, pH=%.3f, PWM1=%.1f%%, PWM2=%.1f%%\n",
                gLastVoltage, gLastPh, gPwm1Percent, gPwm2Percent);
}

static void updateTemperatureReading() {
  const uint32_t now = millis();
  if (now - gLastTempSampleMs < 1000) {
    return;
  }
  gLastTempSampleMs = now;

  gLastTempC = ds18b20.readCelsius();
  if (isnan(gLastTempC)) {
    lv_label_set_text(tempLabel, "Temp: sensor offline");
    Serial.println("DS18B20 read failed");
    return;
  }

  char val[16];
  char text[32];
  formatFixed(val, sizeof(val), gLastTempC, 2);
  snprintf(text, sizeof(text), "Temp: %s C", val);
  lv_label_set_text(tempLabel, text);
  Serial.printf("Temp: %.2f C\n", gLastTempC);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_LCD_CS, OUTPUT);
  pinMode(PIN_LCD_DC, OUTPUT);
  pinMode(PIN_LCD_RST, OUTPUT);
  pinMode(PIN_LCD_BLC, OUTPUT);
  digitalWrite(PIN_LCD_CS, HIGH);

  pinMode(PIN_TP_RST, OUTPUT);
  if (PIN_TP_INT >= 0) {
    pinMode(PIN_TP_INT, INPUT_PULLUP);
  }
  digitalWrite(PIN_TP_RST, LOW);
  delay(10);
  digitalWrite(PIN_TP_RST, HIGH);
  delay(50);

  Wire.begin(PIN_TP_SDA, PIN_TP_SCL);
  Wire.setClock(400000);

  lcdSpi.begin(PIN_LCD_SCK, -1, PIN_LCD_MOSI, PIN_LCD_CS);
  lcdSpi.beginTransaction(SPISettings(20000000, MSBFIRST, SPI_MODE0));

  ledcSetup(7, 5000, 8);
  ledcAttachPin(PIN_LCD_BLC, 7);
  ledcWrite(7, 255);

  initLcd();

  lv_init();
  buf1 = static_cast<lv_color_t *>(heap_caps_malloc(TFT_WIDTH * 40 * sizeof(lv_color_t), MALLOC_CAP_SPIRAM));
  buf2 = static_cast<lv_color_t *>(heap_caps_malloc(TFT_WIDTH * 40 * sizeof(lv_color_t), MALLOC_CAP_SPIRAM));
  if (!buf1 || !buf2) {
    Serial.println("LVGL draw buffer alloc failed");
    while (true) {
      delay(1000);
    }
  }

  lv_disp_draw_buf_init(&drawBuf, buf1, buf2, TFT_WIDTH * 40);
  lv_disp_drv_init(&dispDrv);
  dispDrv.hor_res = TFT_WIDTH;
  dispDrv.ver_res = TFT_HEIGHT;
  dispDrv.flush_cb = lvglFlush;
  dispDrv.draw_buf = &drawBuf;
  lv_disp_drv_register(&dispDrv);

  lv_indev_drv_init(&indevDrv);
  indevDrv.type = LV_INDEV_TYPE_POINTER;
  indevDrv.read_cb = lvglTouchRead;
  lv_indev_drv_register(&indevDrv);

  buildUi();

  if (!pwm1.begin() || !pwm2.begin()) {
    Serial.println("PWM init failed");
    while (true) {
      delay(1000);
    }
  }
  pwm1.setSpeedPercent(0.0f);
  pwm2.setSpeedPercent(0.0f);

  ads.begin();
  ads.setPHCalibration(kPhCal);
  const bool dsReady = ds18b20.begin();

  Serial.printf("ADS1220 cfg: R0=0x%02X R1=0x%02X R2=0x%02X R3=0x%02X\n",
                ads.readRegister(0), ads.readRegister(1), ads.readRegister(2), ads.readRegister(3));
  Serial.printf("PH calib: slope=%.6f intercept=%.6f\n", ads.getPHSlope(), ads.getPHIntercept());
  Serial.printf("DS18B20 init: %s (pin=%u)\n", dsReady ? "OK" : "FAIL", DS18B20_PIN);
}

void loop() {
  lv_timer_handler();
  updatePhReading();
  updateTemperatureReading();
  delay(5);
}
