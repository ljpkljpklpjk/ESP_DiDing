# ESP32-S3 自动滴定仪下位机与树莓派上位机工程

## 版本信息

- 版本号：v2026.05.18.1
- 提交时间：2026-05-18 13:33:05 +0800
- 更新内容：模块化重构 ESP32 下位机代码结构，加入 AS7341 与 MLX90640 采样，将树莓派上位机替换为 PySide6 Qt 界面，并重新生成预编译 OTA 固件。

## 项目概述

本仓库是一个基于 ESP32-S3 和树莓派 3B+ 的自动滴定仪测试工程。

整体设计分为两部分：

1. **ESP32-S3 下位机**
   - 负责直接连接和控制传感器、执行器。
   - 负责采集 pH、电压、温度等数据。
   - 负责控制 PWM 输出、蠕动泵、丝杆滑台。
   - 通过串口 JSON Lines 与树莓派通信。
   - 支持 WiFi 与 ArduinoOTA 远程固件更新。

2. **树莓派上位机**
   - 运行本仓库内的 Tkinter 图形界面。
   - 通过 USB 串口与 ESP32-S3 通信。
   - 在树莓派本地屏幕上显示滴定仪状态。
   - 提供 PWM、蠕动泵、丝杆滑台控制按钮。
   - 提供 WiFi 打开/关闭、连接 WiFi、查看 IP 功能。
   - 提供从 Gitee 检查更新、拉取更新、通过 OTA 更新 ESP32 固件的功能。

当前通信方式为 **串口 JSON Lines**：树莓派上位机按行发送 JSON 控制指令，ESP32-S3 按行回传遥测、确认、完成和错误信息。

## 当前已支持功能

### 下位机功能

- ADS1220 采集 pH 电极差分电压。
- pH 电压换算。
- DS18B20 温度采集。
- AS7341 光谱传感器采样。
- MLX90640 热成像传感器平均温度采样。
- PWM1 输出控制。
- DFR0523 或兼容 PWM/PPM 蠕动泵控制。
- TMC2209 STEP/DIR 丝杆滑台控制。
- 丝杆滑台使能、关闭使能、定距移动、定时移动、停止、急停、清零。
- 串口 JSON Lines 通信。
- WiFi 自动连接。
- ArduinoOTA 远程固件更新。
- OTA 开始前自动急停。
- 运动期间优化任务调度，减少丝杆滑台卡顿。

### 上位机功能

- 树莓派本地 PySide6 图形界面。
- pH、温度、电压、PWM、蠕动泵、滑台状态实时显示。
- AS7341 强度、变化率和 MLX90640 平均温度显示。
- PWM1 和蠕动泵百分比设置。
- 丝杆滑台速度、加速度、移动距离、移动时间设置。
- 丝杆滑台使能、关闭使能、停止、立即停止、清零、急停。
- 树莓派 WiFi 状态显示。
- 树莓派 WiFi 打开、关闭、连接其他 WiFi。
- Gitee 更新源检查。
- 从 Gitee 拉取最新上位机代码和预编译固件。
- 直接上传仓库内预编译 `firmware.bin` 到 ESP32。
- OTA 实时日志显示，包括认证、上传百分比、完成或失败信息。

## 推荐使用流程总览

推荐最终实验室使用方式如下：

1. 管理者在 Windows 电脑上维护本仓库代码。
2. 管理者在 Windows 电脑上编译 ESP32 固件。
3. 管理者把生成好的预编译固件 `firmware/esp32s3box_ota/firmware.bin` 提交并推送到 Gitee/GitHub。
4. 树莓派固定从 Gitee 拉取项目更新。
5. 树莓派本地屏幕运行 `raspberry_pi/titrator_gui.py`。
6. 用户在树莓派界面点击“从 Gitee 更新代码”。
7. 用户在树莓派界面点击“更新 ESP32 固件 OTA”。
8. 树莓派直接把仓库里的预编译固件上传给 ESP32，不在树莓派上编译。

这样做的好处是：

- 树莓派不需要安装完整 PlatformIO 编译链。
- 树莓派不需要访问 GitHub，优先使用 Gitee。
- ESP32 不需要暴露到公网，只需要和树莓派在同一实验室局域网。
- 现场更新流程更稳定，适合触摸屏一体化操作。

## 仓库目录说明

```text
.
├── include/                         # 公共头文件目录
├── lib/                             # 本项目自定义硬件模块封装
│   ├── ADS1220Module/               # ADS1220 ADC 模块
│   ├── DS18B20Module/               # DS18B20 温度模块
│   ├── DFR0523Pump/                 # 蠕动泵模块
│   └── PWMOutput/                   # PWM 输出模块
├── src/
│   └── main.cpp                     # ESP32-S3 下位机主程序
├── raspberry_pi/
│   ├── titrator_gui.py              # 树莓派 Tkinter 一体化上位机界面
│   ├── ota_update.py                # 树莓派命令行 OTA 入口
│   ├── ota_upload_bin.py            # 不依赖 PlatformIO 的 Python OTA 上传器
│   └── README.md                    # 树莓派端说明
├── tools/
│   └── release_firmware.py          # 管理者电脑生成预编译固件的脚本
├── firmware/
│   └── esp32s3box_ota/
│       ├── firmware.bin             # 已发布的 ESP32 OTA 固件
│       └── version.json             # 固件版本、构建时间、大小等信息
├── platformio.ini                   # PlatformIO 工程配置
└── README.md                        # 本说明文档
```

## 硬件选型

### 主控

- ESP32-S3 开发板。
- 当前工程 PlatformIO board 使用 `esp32s3box`。
- 实际使用的是 ESP32-S3 系列开发板。

### pH 测量

- pH 电极。
- pH 信号模块。
- ADS1220 ADC 模块。

### 温度测量

- DS18B20 温度模块。

### PWM / 蠕动泵

- PWM1 普通 PWM 输出。
- DFR0523 或兼容 PWM/PPM 信号控制的蠕动泵。

### 丝杆滑台

- 28 步进电机。
- 电机标称：1.8°/步。
- 丝杆直径：6mm。
- 丝杆螺距：2mm。
- 驱动器：TMC2209。
- 使用模式：STEP/DIR。
- 当前细分：16 细分。

## ESP32-S3 接线

### 总体供电注意事项

- ESP32-S3、ADS1220、DS18B20、TMC2209、蠕动泵控制信号必须共地。
- ESP32 的 GPIO 只能输出控制信号，不能直接驱动步进电机线圈。
- 步进电机线圈必须接到 TMC2209 的电机输出端。
- TMC2209 的 VM/VMOT 需要接电机外部电源。
- 通电时不要插拔步进电机线圈。
- 电机发热通常与驱动电流设置有关，不完全由代码决定，需要检查 TMC2209 电流设置和散热。

### ADS1220 模块与 pH 模块

```text
ADS1220 CS    -> ESP32 GPIO21
ADS1220 DRDY  -> ESP32 GPIO15
ADS1220 SCLK  -> ESP32 GPIO4
ADS1220 MISO  -> ESP32 GPIO13
ADS1220 MOSI  -> ESP32 GPIO14
ADS1220 DVDD  -> ESP32 3.3V
ADS1220 DGND  -> ESP32 GND
ADS1220 AGND  -> ADS1220 AIN1
PH P0         -> ADS1220 AIN0
PH VCC        -> ESP32 3.3V
PH GND        -> ESP32 GND
```

当前程序按 AIN0-AIN1 差分方式读取 pH 电极相关电压。

### DS18B20 模块

```text
DS18B20 DAT -> ESP32 GPIO2
DS18B20 VCC -> ESP32 3.3V
DS18B20 GND -> ESP32 GND
```

### AS7341 与 MLX90640 I2C 模块

```text
AS7341 SDA   -> ESP32 GPIO7
AS7341 SCL   -> ESP32 GPIO8
MLX90640 SDA -> ESP32 GPIO7
MLX90640 SCL -> ESP32 GPIO8
AS7341 VCC   -> ESP32 3.3V
MLX90640 VCC -> ESP32 3.3V
AS7341 GND   -> ESP32 GND
MLX90640 GND -> ESP32 GND
```

当前程序使用同一组 I2C 总线读取 AS7341 和 MLX90640。

### PWM1 输出与蠕动泵

```text
PWM1 输出       -> ESP32 GPIO5
蠕动泵信号输入 -> ESP32 GPIO6
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

TMC2209 1A / 1B -> 步进电机其中一组线圈
TMC2209 2A / 2B -> 步进电机另一组线圈
```

### 步进电机线圈判断

如果电机只有四根线，需要先判断两组线圈：

1. 用万用表电阻档测四根线之间的电阻。
2. 能测到较小电阻的一对线是同一组线圈。
3. 两组线圈分别接到 TMC2209 的 1A/1B 和 2A/2B。
4. 如果方向反了，可以交换其中一组线圈的两根线，或在代码中调整方向。

## 丝杆滑台参数

当前默认换算关系如下：

```text
步进电机：1.8°/步
一圈整步数：360 / 1.8 = 200 步/圈
TMC2209 细分：16 细分
丝杆螺距：2mm/圈
每圈脉冲数：200 * 16 = 3200 steps
每毫米脉冲数：3200 / 2 = 1600 steps/mm
```

因此：

```text
1 mm = 1600 steps
10 mm = 16000 steps
50 mm = 80000 steps
```

当前推荐偏稳定参数：

```text
推荐速度：1000 steps/s
推荐加速度：500 steps/s²
```

如果追求更稳定，可以适当降低速度和加速度，例如：

```text
速度：600 到 1000 steps/s
加速度：300 到 500 steps/s²
```

如果出现明显丢步、卡顿、噪声大、发热严重，需要优先检查：

- TMC2209 细分设置是否为 16。
- TMC2209 电流是否过大或过小。
- 电机供电电压是否合适。
- 滑台机械阻力是否过大。
- STEP/DIR/EN 接线是否稳定。
- 所有 GND 是否共地。

## ESP32 下位机任务调度说明

ESP32 主循环中最需要高频调用的是丝杆滑台的 `AccelStepper::run()`。

为了减少滑台运动时“一下一下地走”或“转一下停一下”的问题，当前固件做了以下调度优化：

- 滑台运动中优先调用 `runSlider()`。
- 滑台运动中继续处理串口指令，保证可以及时停止或急停。
- 滑台运动中降低 OTA 处理频率。
- 滑台运动中跳过 pH 读取、温度读取和普通遥测上报。
- ADS1220 DRDY 等待超时时间缩短，避免长时间阻塞。
- DS18B20 温度读取拆成请求转换和读取结果两个阶段，减少阻塞。
- 串口接收每轮限制处理字节数，避免一次处理过多串口数据影响步进脉冲。

这意味着：

- 滑台运动时，传感器遥测可能暂时不刷新。
- 滑台停止后，pH、温度和普通遥测会继续更新。
- 急停、停止等控制指令在运动中仍会被处理。

## 串口 JSON Lines 协议

### 基本参数

```text
波特率：115200
格式：一行一个 JSON 对象
结尾：每条 JSON 必须以换行符 \n 结束
编码：UTF-8
```

### 通信方向

```text
树莓派 / 串口调试工具  ->  ESP32：控制命令
ESP32                 ->  树莓派 / 串口调试工具：遥测、确认、完成、错误
```

### 命令 id 说明

推荐每条命令带 `id` 字段，例如：

```json
{"cmd":"slider_move_mm","id":14,"mm":10}
```

ESP32 回传 `ack`、`done` 或 `error` 时会带回同一个 `id`，方便上位机判断是哪一条命令的结果。

## ESP32 自动遥测

ESP32 每 1 秒左右上报一次遥测。滑台运动时为了保证运动平滑，普通遥测可能暂停，停止后恢复。

示例：

```json
{"type":"telemetry","ph":7.123,"temperature_c":25.6,"pwm1_percent":0,"pump_percent":0,"slider":{"pos":0,"target":0,"distance":0,"moving":false,"enabled":false,"speed":1000,"steps_per_mm":1600},"wifi_connected":true,"ip":"192.168.1.50","ota_ready":true}
```

常见字段说明：

| 字段 | 含义 |
| --- | --- |
| `type` | 消息类型，遥测为 `telemetry` |
| `ph` | 换算后的 pH 值 |
| `temperature_c` | DS18B20 温度，单位 ℃ |
| `mlx90640_ok` | MLX90640 是否初始化成功 |
| `mlx90640_avg_temp_c` | MLX90640 32x24 热成像帧平均温度，单位 ℃ |
| `as7341_ok` | AS7341 是否初始化成功 |
| `as7341_intensity` | AS7341 绿、黄、红通道合成强度 |
| `as7341_rate` | AS7341 合成强度变化率 |
| `as7341_channels` | AS7341 12 个原始通道值数组 |
| `pwm1_percent` | PWM1 当前百分比 |
| `pump_percent` | 蠕动泵当前百分比 |
| `slider.pos` | 滑台当前位置，单位 steps |
| `slider.target` | 滑台目标位置，单位 steps |
| `slider.distance` | 距离目标剩余 steps |
| `slider.moving` | 滑台是否正在运动 |
| `slider.enabled` | TMC2209 使能状态 |
| `slider.speed` | 当前最大速度，单位 steps/s |
| `slider.steps_per_mm` | 每毫米脉冲数 |
| `wifi_connected` | ESP32 WiFi 是否已连接 |
| `ip` | ESP32 当前 IP |
| `ota_ready` | OTA 是否已启动 |

## 控制命令示例

### 设置 PWM1

```json
{"cmd":"set_pwm1","id":1,"percent":20}
```

说明：

- `percent` 范围通常为 0 到 100。
- 0 表示关闭输出。
- 100 表示满输出。

### 设置蠕动泵

```json
{"cmd":"set_pump","id":2,"percent":30}
```

### 停止蠕动泵

```json
{"cmd":"pump_stop","id":3}
```

### 兼容旧格式 PWM / 泵命令

旧格式仍兼容：

```json
{"pwm1_percent":20,"pump_percent":30}
```

新代码推荐使用带 `cmd` 和 `id` 的格式。

## 丝杆滑台控制命令

### 使能滑台

```json
{"cmd":"slider_enable","id":10}
```

使能后 TMC2209 会锁住电机，电机有保持力。

### 关闭滑台使能

```json
{"cmd":"slider_disable","id":11}
```

关闭后电机不再保持位置，滑台可能可以被手动推动。

### 设置速度

```json
{"cmd":"slider_speed","id":12,"speed":1000}
```

单位：`steps/s`。

### 设置加速度

```json
{"cmd":"slider_accel","id":13,"accel":500}
```

单位：`steps/s²`。

### 按距离移动

```json
{"cmd":"slider_move_mm","id":14,"mm":10}
```

说明：

- `mm` 为正数时向一个方向移动。
- `mm` 为负数时向反方向移动。
- 当前换算为 `1mm = 1600 steps`。

### 按指定时间移动指定距离

```json
{"cmd":"slider_move_time","id":15,"mm":10,"sec":20}
```

说明：

- 表示希望滑台在约 20 秒内移动 10mm。
- 程序会根据距离和时间计算需要的速度。
- 如果计算速度太低或太高，可能会被程序限制到安全范围。

### 平滑停止

```json
{"cmd":"slider_stop","id":16}
```

通常表示按 AccelStepper 的方式减速停止。

### 立即停止

```json
{"cmd":"slider_halt","id":17}
```

立即停止更适合紧急场景。

### 当前位置清零

```json
{"cmd":"slider_zero","id":18}
```

把当前所在位置设置为 0。

## 急停命令

```json
{"cmd":"emergency_stop","id":99}
```

急停会立即执行：

- 停止滑台。
- 关闭滑台驱动使能。
- 停止 PWM1。
- 停止蠕动泵。

OTA 开始前，ESP32 也会自动执行急停，避免固件更新过程中执行器继续动作。

## ESP32 回传格式

### 确认消息

ESP32 收到并接受命令后回传：

```json
{"type":"ack","id":14,"ok":true}
```

### 滑台运动完成消息

滑台运动结束后回传：

```json
{"type":"done","id":14,"ok":true}
```

### 错误消息

命令缺少参数或参数错误时回传：

```json
{"type":"error","id":14,"code":"missing_mm"}
```

常见错误含义：

| code | 含义 |
| --- | --- |
| `missing_mm` | 缺少 `mm` 参数 |
| `missing_sec` | 缺少 `sec` 参数 |
| `invalid_speed` | 速度参数无效 |
| `invalid_accel` | 加速度参数无效 |
| `unknown_cmd` | 未知命令 |

## Windows 管理者电脑环境

### 安装要求

管理者电脑需要：

- Python 3。
- PlatformIO。
- 能通过 USB 首次烧录 ESP32。
- 能访问 Gitee/GitHub 用于推送代码。

当前常用 PlatformIO 路径：

```text
C:/Users/MI/.platformio/penv/Scripts/platformio.exe
```

### 编译默认 USB 固件

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature
```

### USB 烧录

第一次使用 OTA 前，必须通过 USB 烧录一次带 OTA 功能的固件。

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -t upload
```

如果有多个串口设备，可以指定上传端口：

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -t upload --upload-port COMx
```

把 `COMx` 换成实际串口号。

### 编译 OTA 环境

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -e esp32s3box_ota
```

## 预编译固件发布流程

树莓派现场不推荐编译 ESP32 固件。推荐由管理者电脑生成预编译固件并提交到仓库。

### 一键生成发布固件

在 Windows 管理者电脑执行：

```bash
python D:/galgame/ESP_DiDing_codex_new_feature/tools/release_firmware.py --project-dir D:/galgame/ESP_DiDing_codex_new_feature
```

脚本会执行：

1. 编译 PlatformIO 环境 `esp32s3box_ota`。
2. 从 `.pio/build/esp32s3box_ota/firmware.bin` 复制固件。
3. 写入仓库发布目录。
4. 生成固件版本信息。

输出文件：

```text
firmware/esp32s3box_ota/firmware.bin
firmware/esp32s3box_ota/version.json
```

### 指定固件版本和说明

```bash
python D:/galgame/ESP_DiDing_codex_new_feature/tools/release_firmware.py --project-dir D:/galgame/ESP_DiDing_codex_new_feature --version v2026.05.16.x --description "这里写本次固件说明"
```

### 提交固件

当 ESP32 端代码有变化时，需要把以下内容一起提交：

```text
src/main.cpp
lib/...
firmware/esp32s3box_ota/firmware.bin
firmware/esp32s3box_ota/version.json
README.md
```

如果只修改树莓派上位机 Python 代码，不需要重新生成 `firmware.bin`。

## ESP32 OTA 说明

### 当前 OTA 参数

测试阶段当前固件会连接实验室 WiFi，并启用 ArduinoOTA：

```text
OTA 主机名：esp-diding
OTA 端口：3232
OTA 密码：测试密码
```

ESP32 启动后，如果 WiFi 连接成功，串口遥测会包含：

```json
{"wifi_connected":true,"ip":"192.168.x.x","ota_ready":true}
```

其中 `192.168.x.x` 就是 OTA 上传时要填写的 ESP32 IP。

### 管理者电脑直接 OTA

如果 Windows 电脑和 ESP32 在同一 WiFi 下，可以用 PlatformIO 直接 OTA：

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -e esp32s3box_ota -t upload --upload-port 192.168.x.x
```

如果电脑能解析 mDNS，也可以尝试：

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature -e esp32s3box_ota -t upload --upload-port esp-diding.local
```

### 树莓派直接上传预编译固件

树莓派不需要 PlatformIO。树莓派只需要运行本仓库里的 Python 上传脚本。

```bash
python3 raspberry_pi/ota_update.py --host 192.168.x.x
```

其中 `192.168.x.x` 换成 ESP32 遥测显示的 IP。

如果项目目录不是默认目录，可以指定：

```bash
python3 raspberry_pi/ota_update.py --host 192.168.x.x --project-dir /home/pi/diding
```

底层实际会调用：

```bash
python3 raspberry_pi/ota_upload_bin.py --host 192.168.x.x --file firmware/esp32s3box_ota/firmware.bin --password <OTA密码>
```

`ota_upload_bin.py` 使用 Python 标准库 socket 实现 ArduinoOTA 上传流程，不依赖 PlatformIO。

## 树莓派上位机部署

### 推荐项目路径

树莓派端推荐固定放在：

```bash
/home/pi/diding
```

### 第一次克隆项目

```bash
cd /home/pi
git clone -b codex/new_feature https://gitee.com/bidi2004/diding.git diding
cd /home/pi/diding
```

### 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3-pip git network-manager
pip3 install pyserial PySide6
```

说明：

- `PySide6` 用于 Qt 图形界面。
- `pyserial` 用于串口通信。
- `git` 用于从 Gitee 更新项目。
- `network-manager` 和 `nmcli` 用于界面里的 WiFi 管理。

如果系统默认没有启用 NetworkManager，需要根据树莓派系统版本启用 NetworkManager。

### 如果已经从 GitHub 克隆过

可以在项目目录添加或修正 Gitee 远程源：

```bash
cd /home/pi/diding
git remote add gitee https://gitee.com/bidi2004/diding.git 2>/dev/null || git remote set-url gitee https://gitee.com/bidi2004/diding.git
git fetch gitee codex/new_feature
git branch --set-upstream-to=gitee/codex/new_feature codex/new_feature
```

## 启动树莓派上位机

ESP32 通过 USB 接到树莓派后，串口一般是以下两种之一：

```text
/dev/ttyACM0
/dev/ttyUSB0
```

### 查看串口设备

插拔 ESP32 USB 前后分别执行：

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

也可以查看内核日志：

```bash
dmesg | tail -n 30
```

### 启动 GUI

如果串口是 `/dev/ttyACM0`：

```bash
cd /home/pi/diding
python3 raspberry_pi/titrator_gui.py --port /dev/ttyACM0 --project-dir /home/pi/diding
```

如果串口是 `/dev/ttyUSB0`：

```bash
cd /home/pi/diding
python3 raspberry_pi/titrator_gui.py --port /dev/ttyUSB0 --project-dir /home/pi/diding
```

### PySide6 界面说明

当前 `raspberry_pi/titrator_gui.py` 默认启动 PySide6 Qt 界面。界面采用大字号卡片、触摸友好的按钮和深色日志窗口，适合树莓派本地屏幕操作。

如果树莓派安装 PySide6 较慢，建议先确认网络稳定，再执行：

```bash
pip3 install PySide6
```

如果使用系统包管理器安装 Qt/PySide6，也可以，只要 `python3 -c "from PySide6.QtWidgets import QApplication"` 能正常通过即可。

## 树莓派 GUI 页面说明

### 滴定控制页

该页面用于日常控制实验设备。

显示内容包括：

- pH。
- DS18B20 温度。
- pH 电极电压。
- MLX90640 32x24 热成像帧平均温度。
- AS7341 绿、黄、红合成强度。
- AS7341 强度变化率。
- AS7341 12 个原始通道值。
- PWM1 当前百分比。
- 蠕动泵当前百分比。
- 串口连接状态。
- 滑台当前位置。
- 滑台目标位置。
- 滑台剩余步数。
- 滑台是否使能。
- 滑台是否运动中。
- 当前速度。

控制内容包括：

- 设置 PWM1 百分比。
- 设置蠕动泵百分比。
- 停止蠕动泵。
- 设置滑台速度。
- 设置滑台加速度。
- 按距离移动滑台。
- 按时间移动滑台。
- 使能滑台。
- 关闭滑台使能。
- 停止滑台。
- 立即停止滑台。
- 当前位置清零。
- 急停。

### 网络设置页

该页面用于管理树莓派自身 WiFi。

功能包括：

- 显示树莓派 WiFi 状态。
- 显示当前连接的 WiFi 名称。
- 显示树莓派 IP 地址。
- 打开 WiFi。
- 关闭 WiFi。
- 输入 SSID 和密码连接 WiFi。

连接加密 WiFi 时，程序会显式配置 NetworkManager 的：

```text
802-11-wireless-security.key-mgmt = wpa-psk
802-11-wireless-security.psk = 输入的密码
```

这样可以避免某些树莓派系统上出现：

```text
802-11-wireless-security.key-mgmt: 缺少属性
```

### 系统更新页

该页面用于更新树莓派项目代码和 ESP32 固件。

功能包括：

- 查看当前项目路径。
- 检查 Gitee 是否有新版本。
- 从 Gitee 拉取最新代码。
- 显示 ESP32 IP。
- 显示 OTA 密码输入框。
- 上传预编译固件到 ESP32。
- 显示 OTA 实时输出日志。

推荐使用顺序：

1. 确认树莓派已连接 WiFi。
2. 确认 ESP32 已连接同一个实验室局域网。
3. 在滴定控制页或通信日志里查看 ESP32 遥测中的 IP。
4. 到系统更新页点击“检查 Gitee 更新”。
5. 如果有更新，点击“从 Gitee 更新代码”。
6. 确认 `firmware/esp32s3box_ota/firmware.bin` 已随项目更新。
7. 点击“更新 ESP32 固件 OTA”。
8. 等待日志显示上传百分比和完成信息。
9. ESP32 OTA 完成后会自动重启。

## Gitee / GitHub 远程仓库

树莓派现场优先使用 Gitee：

```text
https://gitee.com/bidi2004/diding.git
```

开发备份也推送到 GitHub：

```text
https://github.com/ljpkljpklpjk/ESP_DiDing.git
```

当前分支：

```text
codex/new_feature
```

树莓派 GUI 中的“检查 Gitee 更新”和“从 Gitee 更新代码”默认使用：

```text
远程名：gitee
仓库：https://gitee.com/bidi2004/diding.git
分支：codex/new_feature
```

## 串口手动测试方法

如果不启动树莓派 GUI，也可以用串口工具直接测试 ESP32。

### 串口参数

```text
波特率：115200
换行：发送时必须带 \n
编码：UTF-8
```

### 基础测试顺序

1. 打开串口。
2. 等待 ESP32 自动输出 `telemetry`。
3. 发送滑台使能：

```json
{"cmd":"slider_enable","id":1}
```

4. 设置速度：

```json
{"cmd":"slider_speed","id":2,"speed":1000}
```

5. 设置加速度：

```json
{"cmd":"slider_accel","id":3,"accel":500}
```

6. 移动 10mm：

```json
{"cmd":"slider_move_mm","id":4,"mm":10}
```

7. 反向移动 10mm：

```json
{"cmd":"slider_move_mm","id":5,"mm":-10}
```

8. 测试按时间移动：

```json
{"cmd":"slider_move_time","id":6,"mm":10,"sec":20}
```

9. 测试急停：

```json
{"cmd":"emergency_stop","id":99}
```

## 常见问题排查

### 1. 树莓派 GUI 没有数据

检查：

- ESP32 是否通过 USB 连接树莓派。
- 串口号是否正确。
- 是否使用了 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。
- ESP32 固件是否已经烧录。
- 是否有其他程序占用了串口。

### 2. 不确定串口是 ACM0 还是 USB0

执行：

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

插拔 ESP32 后观察新增的是哪个设备。

### 3. 滑台使能后没有锁力

检查：

- EN 是否接到 ESP32 GPIO12。
- TMC2209 EN 逻辑是否与当前代码一致。
- TMC2209 是否有电机电源。
- ESP32 GND 是否和 TMC2209 GND 共地。
- 电机线圈是否接到正确的 1A/1B、2A/2B。
- TMC2209 电流是否设置太小。

### 4. 电机有锁力但不动

检查：

- STEP 是否接 GPIO10。
- DIR 是否接 GPIO11。
- TMC2209 模式是否是 STEP/DIR。
- 细分设置是否正确。
- 速度是否太低导致肉眼看起来很慢。
- 机械结构是否卡住。

### 5. 电机移动距离不准

当前理论值是：

```text
1mm = 1600 steps
```

如果实测 50mm 约为 50.1mm，这个误差已经很小，通常不需要改换算。

如果误差很大，检查：

- TMC2209 细分是否真的是 16。
- 丝杆螺距是否真的是 2mm。
- 电机是否真的是 1.8°/步。
- 是否存在丢步。
- 滑台是否有机械间隙。

### 6. 电机很烫

步进电机发热常见原因：

- TMC2209 电流设置过大。
- 长时间保持使能。
- 散热不足。
- 电机本身体积较小。

可以尝试：

- 降低 TMC2209 电流。
- 不运动时关闭使能。
- 给驱动器加散热片或风扇。
- 降低保持时间。

### 7. 滑台一下一下地动

可能原因：

- 主循环被传感器读取阻塞。
- 串口输出太频繁。
- OTA/WiFi 处理太频繁。
- 速度或加速度设置不合适。
- 驱动电流不足导致丢步。

当前代码已经做了调度优化。如果仍明显卡顿，优先尝试：

```text
速度：600 steps/s
加速度：300 steps/s²
```

并检查电源、驱动电流和机械阻力。

### 8. 树莓派连接 WiFi 报 key-mgmt 缺少属性

当前 GUI 已针对加密 WiFi 显式写入：

```text
802-11-wireless-security.key-mgmt = wpa-psk
```

如果仍失败，可以在树莓派终端检查：

```bash
nmcli connection show
nmcli dev wifi list
```

必要时删除旧的错误连接配置后重新在 GUI 中连接：

```bash
nmcli connection delete "WiFi名称"
```

### 9. 树莓派 OTA 没有进度

当前 GUI 的系统更新页有 OTA 实时输出框。

如果长时间没有输出，检查：

- ESP32 和树莓派是否在同一个局域网。
- ESP32 遥测里是否有 `wifi_connected:true`。
- ESP32 遥测里是否有正确 IP。
- OTA IP 是否填写正确。
- OTA 密码是否正确。
- `firmware/esp32s3box_ota/firmware.bin` 是否存在。

### 10. OTA 报 ESP32 响应 1024

ESP32 在 OTA 过程中可能返回每个数据块的确认值，例如：

```text
1024
```

这是正常块确认，不是错误。当前上传脚本已经兼容这种响应。

### 11. 树莓派拉取 GitHub 很慢或失败

现场树莓派优先使用 Gitee，不需要访问 GitHub。

确认远程源：

```bash
cd /home/pi/diding
git remote -v
```

如果没有 `gitee`，执行：

```bash
git remote add gitee https://gitee.com/bidi2004/diding.git 2>/dev/null || git remote set-url gitee https://gitee.com/bidi2004/diding.git
```

## 开发注意事项

### 修改 ESP32 固件后

如果修改了以下内容：

- `src/main.cpp`
- `lib/` 下的模块
- `platformio.ini`
- ESP32 引脚、协议、OTA、传感器或执行器逻辑

则提交前应该：

1. 编译 ESP32 固件。
2. 运行 `tools/release_firmware.py` 生成新的 `firmware.bin`。
3. 更新 README 版本信息。
4. 提交源码和预编译固件。
5. 推送到 Gitee/GitHub。

### 只修改树莓派上位机后

如果只修改：

- `raspberry_pi/titrator_gui.py`
- `raspberry_pi/ota_update.py`
- `raspberry_pi/ota_upload_bin.py`
- 文档

通常不需要重新生成 ESP32 `firmware.bin`。

但仍建议运行 Python 语法检查：

```bash
python -m py_compile raspberry_pi/titrator_gui.py raspberry_pi/ota_update.py raspberry_pi/ota_upload_bin.py tools/release_firmware.py
```

### README 版本信息

每次正式提交前，根目录 README 顶部的“版本信息”应更新：

```text
版本号
提交时间
更新内容
```

版本和时间放在 README 中，不放在 git commit body 中。

## 当前 PlatformIO 配置

当前 `platformio.ini` 主要内容：

```ini
[platformio]
default_envs = esp32s3box

[env:esp32s3box]
platform = espressif32
board = esp32s3box
framework = arduino
lib_ldf_mode = chain
build_flags =
  -I include
lib_deps =
  paulstoffregen/OneWire@^2.3.8
  milesburton/DallasTemperature@^4.0.5
  bblanchon/ArduinoJson@^7.0.0
  waspinator/AccelStepper @ ^1.64

[env:esp32s3box_ota]
extends = env:esp32s3box
upload_protocol = espota
upload_flags =
  --auth=lab80700
```

## 快速命令汇总

### Windows 编译

```bash
C:/Users/MI/.platformio/penv/Scripts/platformio.exe run -d D:/galgame/ESP_DiDing_codex_new_feature
```

### Windows 生成预编译 OTA 固件

```bash
python D:/galgame/ESP_DiDing_codex_new_feature/tools/release_firmware.py --project-dir D:/galgame/ESP_DiDing_codex_new_feature
```

### 树莓派首次克隆

```bash
cd /home/pi
git clone -b codex/new_feature https://gitee.com/bidi2004/diding.git diding
cd /home/pi/diding
pip3 install pyserial PySide6
```

### 树莓派启动 GUI

```bash
cd /home/pi/diding
python3 raspberry_pi/titrator_gui.py --port /dev/ttyACM0 --project-dir /home/pi/diding
```

或：

```bash
cd /home/pi/diding
python3 raspberry_pi/titrator_gui.py --port /dev/ttyUSB0 --project-dir /home/pi/diding
```

### 树莓派命令行 OTA

```bash
cd /home/pi/diding
python3 raspberry_pi/ota_update.py --host 192.168.x.x
```

### 检查 Python 文件语法

```bash
python -m py_compile raspberry_pi/titrator_gui.py raspberry_pi/ota_update.py raspberry_pi/ota_upload_bin.py tools/release_firmware.py
```

## 当前推荐现场操作步骤

### 第一次部署

1. Windows 电脑通过 USB 给 ESP32 烧录一次固件。
2. 确认 ESP32 串口输出正常。
3. 确认 ESP32 能连接实验室 WiFi。
4. 在树莓派上克隆 Gitee 仓库到 `/home/pi/diding`。
5. 安装 `PySide6`、`pyserial`、`git`、`network-manager`。
6. ESP32 USB 接到树莓派。
7. 启动树莓派 PySide6 GUI。
8. 在 GUI 中确认 pH、温度、电压、MLX90640、AS7341、PWM、滑台状态能显示。
9. 在 GUI 中测试滑台使能、移动、停止、急停。
10. 在 GUI 系统更新页测试 OTA。

### 日常更新

1. 管理者修改代码。
2. 如果改了 ESP32 固件，管理者生成新的预编译 `firmware.bin`。
3. 管理者提交并推送到 Gitee/GitHub。
4. 实验室用户在树莓派 GUI 点击“从 Gitee 更新代码”。
5. 如果有新固件，点击“更新 ESP32 固件 OTA”。
6. 等待 ESP32 重启并恢复遥测。

## 安全与实验注意事项

- OTA 前 ESP32 会自动急停，但仍建议现场确认执行器处于安全状态。
- 测试泵和滑台时不要让机构撞限位。
- 第一次测试滑台时使用低速度和低加速度。
- 不要在通电状态下插拔步进电机线。
- 蠕动泵和 PWM 输出接真实设备前，先用低百分比测试。
- 如果设备行为异常，优先点击 GUI 的“急停”，或断开执行器电源。
