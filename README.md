# ESP32-S3滴定仪测试固件

本仓库为基于 ESP32-S3 主控的自动滴定仪下位机测试固件。当前通信方式为串口 JSON Lines：树莓派上位机按行下发 JSON 控制指令，ESP32 按行回传遥测、确认和错误信息。

## 已支持功能

- ADS1220 + pH 电极电压采集与 pH 换算
- DS18B20 温度采集
- PWM1 输出控制
- DFR0523 蠕动泵控制
- TMC2209 STEP/DIR 丝杆滑台控制
- 串口 JSON 通信

## 硬件选型

**主控**：ESP32-S3 开发板

**PH计模块**：PH 计配合 ADS1220 ADC 模块

**温度测量模块**：DS18B20 模块

**蠕动泵**：DFR0523 或兼容 PWM/PPM 信号控制蠕动泵

**丝杆滑台**：28 步进电机，1.8°/步，丝杆直径 6mm，螺距 2mm

**步进驱动**：TMC2209，STEP/DIR 模式，16 细分

## 接线

### ESP32-S3

5Vin 接 5V，所有外设 GND 必须与 ESP32 GND 共地。

### ADS1220 模块与 PH 模块

```text
CS    -> GPIO21
DRDY  -> GPIO15
SCLK  -> GPIO4
MISO  -> GPIO13
MOSI  -> GPIO14
DVDD  -> 3.3V
DGND  -> GND
AGND  -> AIN1
PH P0 -> AIN0
PH VCC -> 3.3V
PH GND -> GND
```

### DS18B20 模块

```text
DAT -> GPIO2
VCC -> 3.3V
GND -> GND
```

### PWM / 蠕动泵

```text
PWM1 输出       -> GPIO5
蠕动泵信号输入 -> GPIO6
```

### TMC2209 丝杆滑台

```text
ESP32 GPIO10 -> TMC2209 STEP
ESP32 GPIO11 -> TMC2209 DIR
ESP32 GPIO12 -> TMC2209 EN
ESP32 3.3V   -> TMC2209 VIO / VCC
ESP32 GND    -> TMC2209 GND
外部电源 +    -> TMC2209 VM / VMOT
外部电源 -    -> TMC2209 GND

TMC2209 1A / 1B -> 电机其中一组线圈
TMC2209 2A / 2B -> 电机另一组线圈
```

> 注意：ESP32 不能直接驱动步进电机线圈，必须经过 TMC2209。通电时不要插拔电机线。

## 丝杆滑台参数

```text
电机：1.8°/步 = 200 整步/圈
TMC2209：16 细分
丝杆：2mm/圈
换算：1mm = 200 * 16 / 2 = 1600 脉冲
推荐稳定速度：1000 steps/s
推荐稳定加速度：500 steps/s²
```

## 串口 JSON 协议

- 波特率：115200
- 一行一个 JSON
- 每条 JSON 以换行符 `\n` 结束

### ESP32 自动上报

ESP32 每 1 秒上报一次：

```json
{"type":"telemetry","ph":7.123,"temperature_c":25.6,"pwm1_percent":0,"pump_percent":0,"slider":{"pos":0,"target":0,"distance":0,"moving":false,"enabled":false,"speed":1000,"steps_per_mm":1600}}
```

### 设置 PWM 和蠕动泵

兼容旧字段：

```json
{"pwm1_percent":20,"pump_percent":30}
```

推荐新格式：

```json
{"cmd":"set_pwm1","id":1,"percent":20}
{"cmd":"set_pump","id":2,"percent":30}
{"cmd":"pump_stop","id":3}
```

### 丝杆滑台控制

```json
{"cmd":"slider_enable","id":10}
{"cmd":"slider_disable","id":11}
{"cmd":"slider_speed","id":12,"speed":1000}
{"cmd":"slider_accel","id":13,"accel":500}
{"cmd":"slider_move_mm","id":14,"mm":10}
{"cmd":"slider_move_time","id":15,"mm":10,"sec":20}
{"cmd":"slider_stop","id":16}
{"cmd":"slider_halt","id":17}
{"cmd":"slider_zero","id":18}
```

### 急停

```json
{"cmd":"emergency_stop","id":99}
```

急停会立即停止滑台、关闭滑台驱动、停止 PWM1 和蠕动泵。

### 回传格式

确认：

```json
{"type":"ack","id":14,"ok":true}
```

滑台运动完成：

```json
{"type":"done","id":14,"ok":true}
```

错误：

```json
{"type":"error","id":14,"code":"missing_mm"}
```

## 树莓派上位机

树莓派 Tkinter 上位机文件放在：

```text
raspberry_pi/titrator_gui.py
```

安装依赖：

```bash
pip3 install pyserial
```

运行示例：

```bash
python3 raspberry_pi/titrator_gui.py --port /dev/ttyUSB0
```

如果 ESP32 通过 USB 连接，也可能是：

```bash
python3 raspberry_pi/titrator_gui.py --port /dev/ttyACM0
```

## OTA 远程上传

当前测试阶段固件会连接 WiFi `Lab807_2.4G`，OTA 主机名为 `esp-diding`，OTA 密码为测试密码。每次 OTA 开始前，下位机会自动执行急停：停止滑台、关闭滑台驱动、停止 PWM1 和蠕动泵。

第一次仍需要 USB 烧录带 OTA 功能的固件；之后 ESP32 和电脑在同一 WiFi 下即可远程上传。

串口遥测会包含：

```json
{"wifi_connected":true,"ip":"192.168.x.x","ota_ready":true}
```

远程上传示例，优先使用串口遥测里显示的 IP：

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -e esp32s3box_ota -t upload --upload-port 192.168.x.x
```

如果电脑能解析 mDNS，也可以尝试：

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -e esp32s3box_ota -t upload --upload-port esp-diding.local
```

### 树莓派中转 OTA

更推荐的远程方式是让树莓派作为中转：用户在树莓派连接的屏幕界面上点击更新，树莓派在实验室局域网内给 ESP32 OTA 上传。这样 ESP32 不需要暴露到公网。

在树莓派安装依赖：

```bash
pip3 install platformio
```

同步项目代码到树莓派后执行：

```bash
python3 raspberry_pi/ota_update.py --host 192.168.x.x
```

其中 `192.168.x.x` 换成 ESP32 遥测中显示的 IP。

## 编译

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature
```
