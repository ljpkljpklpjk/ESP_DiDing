/**
 * Minimal LVGL 8.x config for ESP32 + PlatformIO.
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

#define LV_COLOR_DEPTH 16
#define LV_COLOR_16_SWAP 0

#define LV_MEM_CUSTOM 0
#if LV_MEM_CUSTOM == 0
  #define LV_MEM_SIZE (64U * 1024U)
  #define LV_MEM_ADR 0
#else
  #define LV_MEM_CUSTOM_INCLUDE <stdlib.h>
  #define LV_MEM_CUSTOM_ALLOC malloc
  #define LV_MEM_CUSTOM_FREE free
  #define LV_MEM_CUSTOM_REALLOC realloc
#endif

#define LV_MEMCPY_MEMSET_STD 0

#define LV_DISP_DEF_REFR_PERIOD 16
#define LV_INDEV_DEF_READ_PERIOD 10

#define LV_TICK_CUSTOM 1
#if LV_TICK_CUSTOM
  #define LV_TICK_CUSTOM_INCLUDE "Arduino.h"
  #define LV_TICK_CUSTOM_SYS_TIME_EXPR (millis())
#endif

#define LV_DPI_DEF 130

#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_DEFAULT &lv_font_montserrat_14

#define LV_USE_LOG 0

#endif /* LV_CONF_H */
