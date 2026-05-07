# ESP32-S3滴定仪测试固件

本仓库为基于ESP32-S3主控的滴定仪测试固件，用于测试PH计测量、温度测量、触摸屏的显示与触摸功能和两路PWM信号输出功能

## 原件选型

**主控**：ESP32-S3开发板

**LCD触控屏**：3.5英寸IPS触摸屏，分辨率320*480，支持SPI协议

**PH计模块**：PH计配合ADS1220 ADC模块

**温度测量模块**：DS18B20模块

## 接线

### ESP32-S3

5Vin接5V

### ADS1220模块与PH模块

CS接开发板21号引脚

DRDY接开发板15号引脚

SCDLK接开发板4号引脚

MISO接开发板13号引脚

MOSI接开发板14号引脚

DVDD接3.3V，DGND接地

AGND接AIN1

AIN0接PH计P0

PH计GND接地，VCC接3.3V

### LCD触摸屏

VCC接3.3V，GND接地

LCD-CS接开发板10号引脚

LCD-RES接开发板8号引脚

LCD-DC接开发板9号引脚

LCD-SDI接开发板11号引脚

SCK接开发板12号引脚

BLC接开发板7号引脚

T-SCL接开发板18号引脚

T-RST接开发板16号引脚

T-SDA接开发板17号引脚

T-INT接开发板19号引脚

### DS18B20模块

VCC接3.3V，GND接地

DAT接开发板2号引脚

### PWM输出

PWM1输出为开发板5号引脚

PWM2输出为开发板6号引脚