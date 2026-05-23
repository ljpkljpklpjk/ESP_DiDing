import json
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_OTA_PASSWORD = "lab80700"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTROLLER_NAME = "有人 SH800"
FIRMWARE_RELATIVE_PATH = Path("firmware/esp32s3box_ota/firmware.bin")
FIRMWARE_VERSION_RELATIVE_PATH = Path("firmware/esp32s3box_ota/version.json")
GITEE_REPO_URL = "https://gitee.com/bidi2004/diding.git"
GITEE_BRANCH = "codex/new_feature"
GITEE_REMOTE = "gitee"


class LinuxSystemManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def _run(self, cmd, cwd=None):
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()

    def wifi_status(self):
        radio = "未知"
        connected_ssid = ""
        ip_addr = ""

        if shutil.which("nmcli"):
            radio_code, radio_out = self._run(["nmcli", "radio", "wifi"])
            if radio_code == 0 and radio_out:
                radio = radio_out

            code, out = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"])
            if code == 0:
                for line in out.splitlines():
                    parts = line.split(":", 3)
                    if len(parts) == 4:
                        _, dev_type, state, connection = parts
                        if dev_type == "wifi" and state in ("connected", "已连接") and connection:
                            connected_ssid = connection
                            break

            if not connected_ssid:
                code, out = self._run(["nmcli", "-t", "-f", "ACTIVE,SSID", "connection", "show", "--active"])
                if code == 0:
                    for line in out.splitlines():
                        active, _, ssid = line.partition(":")
                        if active == "yes" and ssid:
                            connected_ssid = ssid
                            break

        if shutil.which("iwgetid"):
            code, out = self._run(["iwgetid", "-r"])
            if code == 0 and out:
                connected_ssid = out

        if shutil.which("hostname"):
            code, out = self._run(["hostname", "-I"])
            if code == 0 and out:
                ip_addr = out.split()[0]

        if connected_ssid:
            ip_text = f"，IP: {ip_addr}" if ip_addr else ""
            return f"WiFi: {radio}，当前连接: {connected_ssid}{ip_text}"
        return f"WiFi: {radio}，当前未连接"

    def wifi_on(self):
        return self._require_nmcli(["nmcli", "radio", "wifi", "on"])

    def wifi_off(self):
        return self._require_nmcli(["nmcli", "radio", "wifi", "off"])

    def connect_wifi(self, ssid: str, password: str):
        if not ssid:
            return 1, "请输入 WiFi 名称"
        if password:
            code, _ = self._require_nmcli(["nmcli", "connection", "show", ssid])
            if code == 0:
                code, out = self._require_nmcli([
                    "nmcli",
                    "connection",
                    "modify",
                    ssid,
                    "connection.type",
                    "802-11-wireless",
                    "802-11-wireless.ssid",
                    ssid,
                    "802-11-wireless-security.key-mgmt",
                    "wpa-psk",
                    "802-11-wireless-security.psk",
                    password,
                ])
            else:
                code, out = self._require_nmcli([
                    "nmcli",
                    "connection",
                    "add",
                    "type",
                    "wifi",
                    "ifname",
                    "*",
                    "con-name",
                    ssid,
                    "ssid",
                    ssid,
                    "wifi-sec.key-mgmt",
                    "wpa-psk",
                    "wifi-sec.psk",
                    password,
                ])
            if code != 0:
                return code, out
            return self._require_nmcli(["nmcli", "connection", "up", ssid])
        return self._require_nmcli(["nmcli", "dev", "wifi", "connect", ssid])

    def ensure_gitee_remote(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        if not (self.project_dir / ".git").exists():
            return 1, f"当前项目路径不是 Git 仓库：{self.project_dir}"

        code, remotes = self._run(["git", "remote"], cwd=self.project_dir)
        if code != 0:
            return code, remotes

        remote_names = set(remotes.split())
        if GITEE_REMOTE in remote_names:
            code, out = self._run(["git", "remote", "set-url", GITEE_REMOTE, GITEE_REPO_URL], cwd=self.project_dir)
        else:
            code, out = self._run(["git", "remote", "add", GITEE_REMOTE, GITEE_REPO_URL], cwd=self.project_dir)
        if code != 0:
            return code, out

        self._run(["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)
        self._run(["git", "branch", "--set-upstream-to", f"{GITEE_REMOTE}/{GITEE_BRANCH}", GITEE_BRANCH], cwd=self.project_dir)
        return 0, f"已设置 Gitee 更新源：{GITEE_REPO_URL} 分支 {GITEE_BRANCH}"

    def check_git_update(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        self.ensure_gitee_remote()
        code, out = self._run(["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)
        if code != 0:
            return code, out
        _, local = self._run(["git", "rev-parse", "HEAD"], cwd=self.project_dir)
        _, remote = self._run(["git", "rev-parse", f"{GITEE_REMOTE}/{GITEE_BRANCH}"], cwd=self.project_dir)
        if local == remote:
            return 0, "当前已经是 Gitee 最新版本"
        return 0, f"Gitee 发现新版本：{local[:7]} -> {remote[:7]}"

    def update_project(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        code, out = self.ensure_gitee_remote()
        if code != 0:
            return code, out
        return self._run(["git", "pull", "--ff-only", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)

    def firmware_path(self):
        return self.project_dir / FIRMWARE_RELATIVE_PATH

    def firmware_version_path(self):
        return self.project_dir / FIRMWARE_VERSION_RELATIVE_PATH

    def firmware_version_text(self):
        path = self.firmware_version_path()
        if not path.exists():
            return "未找到固件版本信息"
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"固件版本信息读取失败: {exc}"
        version = info.get("version", "未知版本")
        built_at = info.get("built_at", "未知时间")
        size = info.get("size_bytes", "未知大小")
        desc = info.get("description", "")
        return f"固件 {version}，构建时间 {built_at}，大小 {size} bytes，{desc}"

    def ota_command(self, host: str, password: str):
        return [
            sys.executable,
            str(self.project_dir / "raspberry_pi" / "ota_upload_bin.py"),
            "--host",
            host,
            "--file",
            str(self.firmware_path()),
            "--password",
            password,
        ]

    def ota_update(self, host: str, password: str):
        if not host:
            return 1, "请输入 ESP32 IP"
        if not self.firmware_path().exists():
            return 1, f"未找到预编译固件：{self.firmware_path()}"
        return self._run(self.ota_command(host, password))

    def _require_nmcli(self, cmd):
        if not shutil.which("nmcli"):
            return 1, "未找到 nmcli，请在 Ubuntu 20.04 上安装并启用 NetworkManager"
        return self._run(cmd)
