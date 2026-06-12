"""TCP server that relays JSON Lines data to LAN clients.

Usage:
    server = TcpRelayServer(port=9000)
    server.start()
    ...
    server.broadcast({"type": "telemetry", "ph": 7.0, ...})
    ...
    server.stop()
"""

import json
import socket
import threading


class TcpRelayServer:
    """Accept TCP clients and broadcast JSON Lines messages to all of them."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self._host = host
        self._port = port
        self._server_sock: socket.socket | None = None
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._accept_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start listening and accepting client connections."""
        if self._running.is_set():
            return

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self._host, self._port))
        self._server_sock.listen(4)
        self._server_sock.settimeout(1.0)

        self._running.set()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True
        )
        self._accept_thread.start()

    def stop(self):
        """Stop the server and close all client connections."""
        self._running.clear()

        if self._accept_thread:
            self._accept_thread.join(timeout=2.0)

        with self._lock:
            for client in self._clients:
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                client.close()
            self._clients.clear()

        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None

    def broadcast(self, payload: dict):
        """Send a JSON Lines message to every connected client.

        Silently drops clients that have disconnected.
        """
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")

        with self._lock:
            # Snapshot to avoid mutating while iterating
            clients = list(self._clients)

        dead = []
        for client in clients:
            try:
                client.sendall(data)
            except OSError:
                dead.append(client)

        if dead:
            with self._lock:
                for client in dead:
                    if client in self._clients:
                        self._clients.remove(client)
                    try:
                        client.close()
                    except OSError:
                        pass

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    @property
    def port(self) -> int:
        return self._port

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _accept_loop(self):
        while self._running.is_set():
            try:
                conn, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            conn.settimeout(5.0)
            with self._lock:
                self._clients.append(conn)

            # Spawn a lightweight keep-alive reader so we can detect
            # disconnected clients even when we aren't broadcasting.
            threading.Thread(
                target=self._read_discard, args=(conn, addr),
                daemon=True,
            ).start()

    def _read_discard(self, client: socket.socket, addr):
        """Read (and discard) from client — only used for disconnect detection."""
        try:
            while self._running.is_set():
                data = client.recv(1024)
                if not data:
                    break
        except OSError:
            pass
        finally:
            with self._lock:
                if client in self._clients:
                    self._clients.remove(client)
            try:
                client.close()
            except OSError:
                pass
