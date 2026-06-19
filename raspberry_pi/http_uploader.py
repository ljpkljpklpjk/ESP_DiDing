"""HTTP telemetry uploader — POSTs JSON telemetry to the remote server.

Usage:
    uploader = HttpTelemetryUploader("http://47.xx.xx.xx")
    uploader.start()
    ...
    uploader.enqueue({"type": "telemetry", "ph": 7.0, ...})
    ...
    status = uploader.status        # "已上传" or "上传失败: ..."
    success = uploader.last_success
"""

import json
import queue
import threading
import time
import urllib.error
import urllib.request


class HttpTelemetryUploader:
    """Non-blocking HTTP uploader with an internal queue + background thread.

    Call ``enqueue(payload)`` from any thread; the uploader sends them one
    at a time to the remote server endpoint.
    """

    def __init__(self, server_url: str, timeout: float = 5.0):
        base = server_url.rstrip("/")
        self._endpoint = f"{base}/api/devices/titrator/telemetry"
        self._timeout = timeout
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None

        # --- status (read from the main thread, written from the worker) ---
        self._lock = threading.Lock()
        self._last_status = "等待上传"
        self._last_success = False
        self._last_upload_time = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def status(self) -> str:
        with self._lock:
            return self._last_status

    @property
    def last_success(self) -> bool:
        with self._lock:
            return self._last_success

    @property
    def last_upload_time(self) -> float:
        with self._lock:
            return self._last_upload_time

    def start(self):
        """Start the background upload worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, payload: dict):
        """Enqueue a telemetry payload for upload (non-blocking)."""
        self._queue.put(payload)

    def stop(self):
        """Signal the worker to stop by enqueuing a sentinel."""
        self._queue.put(None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self):
        """Worker loop — consumes the queue and uploads one at a time."""
        while True:
            payload = self._queue.get()
            if payload is None:  # sentinel
                break

            success, msg = self._do_upload(payload)
            with self._lock:
                if success:
                    self._last_status = "已上传"
                    self._last_success = True
                    self._last_upload_time = time.time()
                else:
                    self._last_status = f"上传失败: {msg}"
                    self._last_success = False

    def _do_upload(self, payload: dict) -> tuple[bool, str]:
        """Synchronous HTTP POST.  Returns (success, human-readable message)."""
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                return True, body
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code} {exc.reason}"
        except urllib.error.URLError as exc:
            return False, f"连接失败: {exc.reason}"
        except OSError as exc:
            return False, str(exc)
