# Raspberry Pi 上位机

这里存放树莓派 3B+ 上位机文件，用于通过串口 JSON Lines 控制 ESP32-S3 下位机。

## 安装依赖

```bash
sudo apt update
sudo apt install -y python3-pip
pip3 install pyserial PySide6
```

## 建立树莓派系统工程路径

树莓派端推荐固定把完整工程放在：

```bash
/home/pi/diding
```

第一次部署时执行：

```bash
cd /home/pi
git clone -b codex/new_feature https://gitee.com/bidi2004/diding.git diding
cd /home/pi/diding
pip3 install pyserial PySide6
```

如果已经从 GitHub 或其他地址克隆过，也可以在项目目录内改成 Gitee 更新源：

```bash
cd /home/pi/diding
git remote add gitee https://gitee.com/bidi2004/diding.git 2>/dev/null || git remote set-url gitee https://gitee.com/bidi2004/diding.git
git fetch gitee codex/new_feature
git branch --set-upstream-to=gitee/codex/new_feature codex/new_feature
```

之后树莓派界面里的“检查 Gitee 更新”和“从 Gitee 更新代码”都会使用 Gitee，不需要访问 GitHub。

## 运行

上位机现在是树莓派屏幕上的 PySide6 一体化界面，包含：

- 滴定控制：pH、温度、电压、PWM、蠕动泵、丝杆滑台、AS7341、MLX90640。
- 网络设置：查看树莓派 WiFi 状态、打开/关闭 WiFi、输入 SSID 和密码连接 WiFi。
- 系统更新：检查项目更新、更新上位机代码、通过 OTA 更新 ESP32 下位机固件。

ESP32 通过 USB 连接树莓派时，串口通常是 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。

```bash
python3 raspberry_pi/titrator_gui.py --port /dev/ttyACM0 --project-dir /home/pi/diding
```

或者：

```bash
python3 raspberry_pi/titrator_gui.py --port /dev/ttyUSB0 --project-dir /home/pi/diding
```

## PySide6 界面说明

`raspberry_pi/titrator_gui.py` 现在默认启动 PySide6 Qt 界面，不再使用 Tkinter 作为主界面。Qt 界面使用大字号状态卡片、触摸友好的按钮、实时日志窗口和后台线程任务，避免 OTA、Gitee 更新、WiFi 操作阻塞界面。

如果安装 PySide6 后仍提示找不到模块，先检查当前 Python 环境：

```bash
python3 -c "from PySide6.QtWidgets import QApplication; print('PySide6 ok')"
```

如果这条命令失败，需要在启动 GUI 的同一个 Python 环境里重新安装 PySide6。

## 系统功能说明

### 网络设置

界面里的“网络设置”页依赖树莓派系统的 NetworkManager 命令 `nmcli`。如果按钮提示找不到 `nmcli`，需要在树莓派上启用或安装 NetworkManager。

### 系统更新

“检查 Gitee 更新”和“从 Gitee 更新代码”依赖 `git`，推荐当前项目目录为 `/home/pi/diding`，并使用 Gitee 仓库 `https://gitee.com/bidi2004/diding.git` 的 `codex/new_feature` 分支作为更新源。

“更新 ESP32 下位机固件 OTA”会在界面内上传仓库里的预编译固件，不需要在树莓派安装 PlatformIO 或现场编译。ESP32 IP 会优先从下位机遥测里的 `ip` 字段自动填入，也可以手动修改。OTA 执行时“系统更新”页会实时显示固件版本、连接、认证、上传百分比、完成或失败状态。

## 树莓派中转 OTA 更新

推荐远程更新方式是：在树莓派屏幕的一体化界面里点击更新，树莓派在实验室局域网内把固件 OTA 上传给 ESP32。这样 ESP32 不需要暴露到公网。

第一次仍需要用 USB 给 ESP32 烧录一次带 OTA 功能的固件。之后在串口遥测或 GUI 通信日志里查看：

```json
{"wifi_connected":true,"ip":"192.168.x.x","ota_ready":true}
```

把项目代码同步到树莓派后，可以在“系统更新”页点击“更新 ESP32 下位机固件 OTA”。该按钮会上传：

```text
firmware/esp32s3box_ota/firmware.bin
```

管理者在电脑上更新该固件文件：

```bash
python tools/release_firmware.py --project-dir D:/galgame/ESP_DiDing_codex_new_feature
```

之后提交并推送到 Gitee。树莓派点击“从 Gitee 更新代码”即可拉到最新预编译固件。

也可以在树莓派终端手动执行：

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
