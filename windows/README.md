# ESP32 自动滴定仪 — Windows 上位机

本目录包含 Windows 版上位机脚本，与 `raspberry_pi/` 中的 Linux（SH800）版本功能一致。

## 与 Linux 版的区别

| 模块 | Linux (`raspberry_pi/`) | Windows (`windows/`) |
|---|---|---|
| 串口检测 | `/dev/ttyUSB*`, `/dev/ttyACM*` 等 | `COM1`–`COM255`，自动匹配 CP210x/CH340/ESP32 |
| WiFi 管理 | `nmcli` (NetworkManager) | `netsh wlan` |
| IP 获取 | `hostname -I` | `netsh interface ip show addresses` + `ipconfig` |
| 系统管理类 | `LinuxSystemManager` | `WindowsSystemManager` |

其余模块（GUI、协议、遥测日志、OTA 上传）直接从 `raspberry_pi/` 复用，无差异。

## 环境要求

- Windows 10 / 11
- Python 3.10+（推荐 3.12）
- Git for Windows（用于 Gitee 代码更新）

## 安装

```powershell
# 1. 克隆项目
git clone -b codex/new_feature https://gitee.com/bidi2004/diding.git
cd diding

# 2. 安装 Python 依赖
pip install pyserial PySide6

# 3. (可选) 如需 Gitee 更新功能，安装 Git for Windows
#    GUI 会优先使用 PATH 中的 git，也会尝试常见安装路径
```

## Gitee 更新

Windows 端“检查 Gitee 更新”和“从 Gitee 更新代码”默认使用 `https://gitee.com/bidi2004/diding.git` 的 `codex/new_feature` 分支。

点击“从 Gitee 更新代码”时，程序会先确认或切换到 `codex/new_feature`，再执行 fast-forward 更新。若当前分支有未提交的跟踪文件改动，程序会停止切换并提示先提交或备份本地修改，避免覆盖现场改动。

## 运行

```powershell
# 自动检测串口（推荐）
python windows/titrator_gui.py

# 手动指定串口
python windows/titrator_gui.py --port COM3

# 指定实验参数
python windows/titrator_gui.py --run-id run_G1_01 --group G1 --repeat 1
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--port` | `auto` | 串口名，`auto` 自动检测，手动如 `COM3` |
| `--baudrate` | `115200` | 波特率 |
| `--project-dir` | 仓库根目录 | 项目路径 |
| `--log-dir` | 自动 | 数据日志输出目录 |
| `--run-id` | 自动生成 | 实验运行 ID |
| `--group` | 自动推断 | 实验组名 |
| `--repeat` | 自动推断 | 重复编号 |
| `--control-mode` | `normal_dosing` | 控制模式 |
| `--target-ph-low` | `6.8` | 目标 pH 下限 |
| `--target-ph-high` | `7.2` | 目标 pH 上限 |
| `--target-tds-mg-l` | `350.0` | 目标 TDS (mg/L) |
| `--target-concentration-mg-l` | `8.0` | 目标浓度 (mg/L) |

## 注意事项

1. **串口驱动**：确保已安装 CP210x 或 CH340 USB 转串口驱动
2. **WiFi 管理**：需要以管理员权限运行才能使用 netsh 管理 WiFi（如不需要 WiFi 管理可忽略）
3. **管理员权限**：WiFi 开关/连接功能可能需要管理员权限，普通权限下仍可查看状态
4. **防火墙**：OTA 固件更新使用 UDP+TCP 端口，首次运行时 Windows 防火墙可能弹窗询问，请允许
