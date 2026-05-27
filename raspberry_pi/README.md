# SH800 / Ubuntu 上位机

这里存放有人 SH800 上位机文件，用于在 RK3568 + Ubuntu 20.04 上通过串口 JSON Lines 控制 ESP32-S3 下位机。

目录名仍保留 `raspberry_pi`，是为了兼容旧脚本和 OTA 命令路径；代码已经按通用 Linux/Ubuntu 上位机运行。

## 安装依赖

```bash
sudo apt update
sudo apt install -y git network-manager
python3.12 -m pip install --user pyserial PySide6
```

如果 SH800 的 Ubuntu 镜像没有启用 NetworkManager，需要先启用它，否则界面里的 WiFi 打开、关闭、连接功能不可用：

```bash
sudo systemctl enable --now NetworkManager
```

## 建立工程路径

推荐把完整工程放在当前用户目录：

```bash
cd ~
git clone -b codex/new_feature https://gitee.com/bidi2004/diding.git diding
cd ~/diding
python3.12 -m pip install --user pyserial PySide6
```

如果已经从 GitHub 或其他地址克隆过，也可以在项目目录内改成 Gitee 更新源：

```bash
cd ~/diding
git remote add gitee https://gitee.com/bidi2004/diding.git 2>/dev/null || git remote set-url gitee https://gitee.com/bidi2004/diding.git
git fetch gitee codex/new_feature
git branch --set-upstream-to=gitee/codex/new_feature codex/new_feature
```

之后界面里的“检查 Gitee 更新”和“从 Gitee 更新代码”都会使用 Gitee，不需要访问 GitHub。

## 运行

上位机使用 Python 3.12 + PySide6 / Qt6 界面，包含：

- 滴定控制：pH、温度、电压、PWM、蠕动泵、丝杆滑台、AS7341、MLX90640。
- 网络设置：查看 SH800 WiFi 状态、打开/关闭 WiFi、输入 SSID 和密码连接 WiFi。
- 系统更新：检查项目更新、更新上位机代码、通过 OTA 更新 ESP32 下位机固件。

ESP32 现在默认通过 RS485 连接 SH800。SH800 的 RS485 串口在 Ubuntu 中通常是 `/dev/ttyS*`、`/dev/ttyAMA*` 或 `/dev/ttyFIQ*`；如果使用 USB-RS485 转换器，也可能是 `/dev/ttyUSB0`。程序默认会自动选择这些串口：

```bash
cd ~/diding
python3.12 raspberry_pi/titrator_gui.py --project-dir ~/diding
```

也可以手动指定串口：

```bash
python3.12 raspberry_pi/titrator_gui.py --port /dev/ttyS1 --project-dir ~/diding
python3.12 raspberry_pi/titrator_gui.py --port /dev/ttyAMA0 --project-dir ~/diding
python3.12 raspberry_pi/titrator_gui.py --port /dev/ttyUSB0 --project-dir ~/diding
```

ESP32 端默认 RS485 引脚：

```text
ESP32 GPIO43 TX -> RS485 模块 DI
ESP32 GPIO44 RX -> RS485 模块 RO
ESP32 GPIO16 DE -> RS485 模块 DE/RE
ESP32 GND       -> RS485 模块 GND
RS485 A         -> SH800 RS485 A
RS485 B         -> SH800 RS485 B
```

ESP32 上电后会先连续输出约 3 秒 `OK`，用于确认 RS485 发送链路。看到 `OK` 后，才会进入正常 JSON Lines 遥测。

如果串口没有权限，把当前用户加入 `dialout` 组后重新登录：

```bash
sudo usermod -aG dialout "$USER"
```

## PySide6 / Qt6 界面说明

`raspberry_pi/titrator_gui.py` 默认启动 PySide6 / Qt6 界面，适合 SH800 升级到 Python 3.12 后使用。界面包含状态卡片、控制按钮、实时日志窗口和后台线程任务，避免 OTA、Gitee 更新、WiFi 操作阻塞界面。

检查 PySide6 是否可用：

```bash
python3.12 -c "from PySide6.QtWidgets import QApplication; print('PySide6 ok')"
```

如果提示找不到 PySide6，在启动 GUI 的同一个 Python 3.12 环境里安装：

```bash
python3.12 -m pip install --user PySide6
```

## 系统功能说明

### 网络设置

界面里的“网络设置”页依赖 Ubuntu 的 NetworkManager 命令 `nmcli`。如果按钮提示找不到 `nmcli`，需要在 SH800 上安装并启用 NetworkManager。

### 系统更新

“检查 Gitee 更新”和“从 Gitee 更新代码”依赖 `git`，推荐当前项目目录为 `~/diding`，并使用 Gitee 仓库 `https://gitee.com/bidi2004/diding.git` 的 `codex/new_feature` 分支作为更新源。

“更新 ESP32 下位机固件 OTA”会在界面内上传仓库里的预编译固件，不需要在 SH800 上安装 PlatformIO 或现场编译。ESP32 IP 会优先从下位机遥测里的 `ip` 字段自动填入，也可以手动修改。OTA 执行时“系统更新”页会实时显示固件版本、连接、认证、上传百分比、完成或失败状态。

## SH800 中转 OTA 更新

推荐远程更新方式是：在 SH800 屏幕的一体化界面里点击更新，SH800 在实验室局域网内把固件 OTA 上传给 ESP32。这样 ESP32 不需要暴露到公网。

第一次仍需要用 USB 给 ESP32 烧录一次带 OTA 功能的固件。之后在串口遥测或 GUI 通信日志里查看：

```json
{"wifi_connected":true,"ip":"192.168.x.x","ota_ready":true}
```

把项目代码同步到 SH800 后，可以在“系统更新”页点击“更新 ESP32 下位机固件 OTA”。该按钮会上传：

```text
firmware/esp32s3box_ota/firmware.bin
```

管理者在电脑上更新该固件文件：

```bash
python tools/release_firmware.py --project-dir D:/galgame/ESP_DiDing_codex_new_feature
```

之后提交并推送到 Gitee。SH800 点击“从 Gitee 更新代码”即可拉到最新预编译固件。

也可以在 SH800 终端手动执行：

```bash
python3.12 raspberry_pi/ota_update.py --host 192.168.x.x
```

如果项目目录不在脚本默认位置，可以指定：

```bash
python3.12 raspberry_pi/ota_update.py --host 192.168.x.x --project-dir ~/diding
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
