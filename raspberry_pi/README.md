# Raspberry Pi 上位机

这里存放树莓派 3B+ 上位机文件，用于通过串口 JSON Lines 控制 ESP32-S3 下位机。

## 安装依赖

```bash
sudo apt update
sudo apt install -y python3-tk python3-pip
pip3 install pyserial platformio
```

## 运行

上位机现在是树莓派屏幕上的一体化界面，包含：

- 滴定控制：pH、温度、电压、PWM、蠕动泵、丝杆滑台。
- 网络设置：查看树莓派 WiFi 状态、打开/关闭 WiFi、输入 SSID 和密码连接 WiFi。
- 系统更新：检查项目更新、更新上位机代码、通过 OTA 更新 ESP32 下位机固件。

ESP32 通过 USB 连接树莓派时，串口通常是 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。

```bash
python3 titrator_gui.py --port /dev/ttyACM0
```

或者：

```bash
python3 titrator_gui.py --port /dev/ttyUSB0
```

## 系统功能说明

### 网络设置

界面里的“网络设置”页依赖树莓派系统的 NetworkManager 命令 `nmcli`。如果按钮提示找不到 `nmcli`，需要在树莓派上启用或安装 NetworkManager。

### 系统更新

“检查项目更新”和“更新上位机代码”依赖 `git`，要求当前项目目录是 Git 仓库并配置了上游分支。

“更新 ESP32 下位机固件 OTA”会在界面内调用 PlatformIO，不需要打开终端。ESP32 IP 会优先从下位机遥测里的 `ip` 字段自动填入，也可以手动修改。

## 树莓派中转 OTA 更新

推荐远程更新方式是：在树莓派屏幕的一体化界面里点击更新，树莓派在实验室局域网内把固件 OTA 上传给 ESP32。这样 ESP32 不需要暴露到公网。

第一次仍需要用 USB 给 ESP32 烧录一次带 OTA 功能的固件。之后在串口遥测或 GUI 通信日志里查看：

```json
{"wifi_connected":true,"ip":"192.168.x.x","ota_ready":true}
```

把项目代码同步到树莓派后，可以在“系统更新”页点击“更新 ESP32 下位机固件 OTA”。也可以在树莓派终端手动执行：

```bash
python3 raspberry_pi/ota_update.py --host 192.168.x.x
```

如果项目目录不在脚本默认位置，可以指定：

```bash
python3 raspberry_pi/ota_update.py --host 192.168.x.x --project-dir /home/pi/ESP_DiDing
```

其中 `192.168.x.x` 换成 ESP32 遥测显示的 IP。

## 串口协议

- 波特率：115200
- 一行一个 JSON
- 每条 JSON 以换行符结束

常用命令示例：

```json
{"cmd":"slider_enable","id":1}
{"cmd":"slider_move_mm","id":2,"mm":10}
{"cmd":"slider_move_time","id":3,"mm":10,"sec":20}
{"cmd":"set_pwm1","id":4,"percent":20}
{"cmd":"set_pump","id":5,"percent":30}
{"cmd":"emergency_stop","id":6}
```
