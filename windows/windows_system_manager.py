import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_OTA_PASSWORD = "lab80700"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTROLLER_NAME = "Windows PC"
FIRMWARE_RELATIVE_PATH = Path("firmware/esp32s3box_ota/firmware.bin")
FIRMWARE_VERSION_RELATIVE_PATH = Path("firmware/esp32s3box_ota/version.json")
GITEE_REPO_URL = "https://gitee.com/bidi2004/diding.git"
GITEE_BRANCH = "codex/new_feature"
GITEE_REMOTE = "gitee"

_WIFI_INTERFACE_CACHE = None


def _wifi_interface_name() -> str | None:
    """Detect the primary Wi-Fi interface name (e.g. 'Wi-Fi' or 'WLAN')."""
    global _WIFI_INTERFACE_CACHE
    if _WIFI_INTERFACE_CACHE is not None:
        return _WIFI_INTERFACE_CACHE

    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            encoding="gbk",
            errors="replace",
            check=False,
        ).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Name"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    _WIFI_INTERFACE_CACHE = parts[1].strip()
                    return _WIFI_INTERFACE_CACHE
    except Exception:
        pass

    _WIFI_INTERFACE_CACHE = "Wi-Fi"  # default fallback
    return _WIFI_INTERFACE_CACHE


class WindowsSystemManager:
    """System operations for Windows: WiFi via netsh, Git, OTA firmware."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _run(self, cmd, cwd=None):
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            encoding="gbk",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()

    def _require_netsh(self):
        if not shutil.which("netsh"):
            return False, "未找到 netsh，请确保在 Windows 上运行"
        return True, ""

    # ------------------------------------------------------------------
    # WiFi 状态
    # ------------------------------------------------------------------

    def wifi_status(self):
        ok, err = self._require_netsh()
        if not ok:
            return err

        radio = "未知"
        connected_ssid = ""
        ip_addr = ""

        # Check interface admin state
        iface = _wifi_interface_name()
        if iface:
            code, out = self._run(
                ["netsh", "interface", "show", "interface", iface]
            )
            if code == 0:
                for line in out.splitlines():
                    if "已启用" in line or "Enabled" in line.lower():
                        radio = "已启用"
                        break
                    elif "已禁用" in line or "Disabled" in line.lower():
                        radio = "已禁用"
                        break

        # Get connected SSID via netsh wlan show interfaces
        code, out = self._run(["netsh", "wlan", "show", "interfaces"])
        if code == 0:
            in_connected = False
            for line in out.splitlines():
                stripped = line.strip()
                if stripped.startswith("SSID"):
                    parts = stripped.split(":", 1)
                    if len(parts) == 2:
                        ssid = parts[1].strip()
                        if ssid:
                            connected_ssid = ssid
                elif stripped.startswith("State"):
                    parts = stripped.split(":", 1)
                    if len(parts) == 2:
                        state = parts[1].strip().lower()
                        in_connected = state == "connected"

        # Get IP address
        ip_addr = self._get_ip_address(iface)

        if connected_ssid:
            ip_text = f"，IP: {ip_addr}" if ip_addr else ""
            return f"WiFi: {radio}，当前连接: {connected_ssid}{ip_text}"
        return f"WiFi: {radio}，当前未连接"

    def _get_ip_address(self, iface: str | None = None) -> str:
        """Get IPv4 address of the Wi-Fi interface."""
        if iface:
            code, out = self._run(
                ["netsh", "interface", "ip", "show", "addresses", iface]
            )
            if code == 0:
                for line in out.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("IP 地址") or stripped.startswith("IP Address"):
                        parts = stripped.split(":", 1)
                        if len(parts) == 2:
                            ip = parts[1].strip()
                            if ip and not ip.startswith("127.") and not ip.startswith("169.254"):
                                return ip

        # Fallback: parse ipconfig
        try:
            out = subprocess.run(
                ["ipconfig"], capture_output=True, encoding="gbk", errors="replace", check=False
            ).stdout
            lines = out.splitlines()
            for i, line in enumerate(lines):
                if "IPv4" in line or "IPv4" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        ip = parts[1].strip()
                        if ip and not ip.startswith("127.") and not ip.startswith("169.254"):
                            # Look backwards to find the adapter name
                            return ip
        except Exception:
            pass

        return ""

    # ------------------------------------------------------------------
    # WiFi 开关
    # ------------------------------------------------------------------

    def wifi_on(self):
        ok, err = self._require_netsh()
        if not ok:
            return 1, err
        iface = _wifi_interface_name()
        if not iface:
            return 1, "未找到 Wi-Fi 网卡"
        return self._run(
            ["netsh", "interface", "set", "interface", iface, "admin=enabled"]
        )

    def wifi_off(self):
        ok, err = self._require_netsh()
        if not ok:
            return 1, err
        iface = _wifi_interface_name()
        if not iface:
            return 1, "未找到 Wi-Fi 网卡"
        return self._run(
            ["netsh", "interface", "set", "interface", iface, "admin=disabled"]
        )

    # ------------------------------------------------------------------
    # 连接 WiFi
    # ------------------------------------------------------------------

    def connect_wifi(self, ssid: str, password: str):
        if not ssid:
            return 1, "请输入 WiFi 名称"

        ok, err = self._require_netsh()
        if not ok:
            return 1, err

        if password:
            # Create an XML WLAN profile and import it
            profile_path = self._create_wlan_profile_xml(ssid, password)
            if not profile_path:
                return 1, "无法创建 WiFi 配置文件"

            # Remove existing profile if any (ignore errors)
            self._run(["netsh", "wlan", "delete", "profile", f"name={ssid}"])

            # Import the profile
            code, out = self._run(
                ["netsh", "wlan", "add", "profile", f"filename={profile_path}"]
            )
            try:
                os.unlink(profile_path)
            except OSError:
                pass

            if code != 0:
                return code, f"导入 WiFi 配置失败: {out}"

        # Connect
        return self._run(["netsh", "wlan", "connect", f"name={ssid}"])

    @staticmethod
    def _create_wlan_profile_xml(ssid: str, password: str) -> str | None:
        """Write a temporary WLAN profile XML and return its path."""
        xml = (
            '<?xml version="1.0"?>\n'
            '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
            f"    <name>{_xml_escape(ssid)}</name>\n"
            "    <SSIDConfig>\n"
            "        <SSID>\n"
            f"            <name>{_xml_escape(ssid)}</name>\n"
            "        </SSID>\n"
            "    </SSIDConfig>\n"
            "    <connectionType>ESS</connectionType>\n"
            "    <connectionMode>auto</connectionMode>\n"
            "    <MSM>\n"
            "        <security>\n"
            "            <authEncryption>\n"
            "                <authentication>WPA2PSK</authentication>\n"
            "                <encryption>AES</encryption>\n"
            "                <useOneX>false</useOneX>\n"
            "            </authEncryption>\n"
            "            <sharedKey>\n"
            "                <keyType>passPhrase</keyType>\n"
            "                <protected>false</protected>\n"
            f"                <keyMaterial>{_xml_escape(password)}</keyMaterial>\n"
            "            </sharedKey>\n"
            "        </security>\n"
            "    </MSM>\n"
            "</WLANProfile>\n"
        )
        try:
            fd, path = tempfile.mkstemp(suffix=".xml", prefix="wifi_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(xml)
            return path
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Git / Gitee 更新
    # ------------------------------------------------------------------

    def ensure_gitee_remote(self):
        if not shutil.which("git"):
            return 1, "未找到 git，请安装 Git for Windows"
        if not (self.project_dir / ".git").exists():
            return 1, f"当前项目路径不是 Git 仓库：{self.project_dir}"

        code, remotes = self._run(["git", "remote"], cwd=self.project_dir)
        if code != 0:
            return code, remotes

        remote_names = set(remotes.split())
        if GITEE_REMOTE in remote_names:
            code, out = self._run(
                ["git", "remote", "set-url", GITEE_REMOTE, GITEE_REPO_URL],
                cwd=self.project_dir,
            )
        else:
            code, out = self._run(
                ["git", "remote", "add", GITEE_REMOTE, GITEE_REPO_URL],
                cwd=self.project_dir,
            )
        if code != 0:
            return code, out

        self._run(
            ["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir
        )
        self._run(
            [
                "git",
                "branch",
                "--set-upstream-to",
                f"{GITEE_REMOTE}/{GITEE_BRANCH}",
                GITEE_BRANCH,
            ],
            cwd=self.project_dir,
        )
        return 0, f"已设置 Gitee 更新源：{GITEE_REPO_URL} 分支 {GITEE_BRANCH}"

    def check_git_update(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        self.ensure_gitee_remote()
        code, out = self._run(
            ["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir
        )
        if code != 0:
            return code, out
        _, local = self._run(["git", "rev-parse", "HEAD"], cwd=self.project_dir)
        _, remote = self._run(
            ["git", "rev-parse", f"{GITEE_REMOTE}/{GITEE_BRANCH}"],
            cwd=self.project_dir,
        )
        if local == remote:
            return 0, "当前已经是 Gitee 最新版本"
        return 0, f"Gitee 发现新版本：{local[:7]} -> {remote[:7]}"

    def update_project(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        code, out = self.ensure_gitee_remote()
        if code != 0:
            return code, out
        return self._run(
            ["git", "pull", "--ff-only", GITEE_REMOTE, GITEE_BRANCH],
            cwd=self.project_dir,
        )

    # ------------------------------------------------------------------
    # OTA 固件
    # ------------------------------------------------------------------

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


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
