# Raspberry Pi 上位机

这里存放树莓派 3B+ 上位机文件，用于通过串口 JSON Lines 控制 ESP32-S3 下位机。

## 安装依赖

```bash
sudo apt update
sudo apt install -y python3-tk python3-pip
pip3 install pyserial
```

## 运行

ESP32 通过 USB 连接树莓派时，串口通常是 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。

```bash
python3 titrator_gui.py --port /dev/ttyACM0
```

或者：

```bash
python3 titrator_gui.py --port /dev/ttyUSB0
```

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
