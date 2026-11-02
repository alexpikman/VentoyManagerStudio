"""Small standard-library HTTP server for the local desktop application."""
from __future__ import annotations

import json
import logging
import mimetypes
import platform
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.services.disks import DiskDiscoveryError, discover_disks


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
HOST = "127.0.0.1"
PORT = 5454

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ventoy_manager")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "VentoyManagerStudio/0.1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path

        if path == "/api/health":
            self._send_json(200, {
                "ok": True,
                "application": "Ventoy Manager Studio",
                "version": "0.1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return

        if path == "/api/system":
            self._send_json(200, {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "supported_platform": platform.system() == "Windows",
            })
            return

        if path == "/api/disks":
            try:
                self._send_json(200, discover_disks())
            except DiskDiscoveryError as exc:
                logger.warning("Disk discovery failed: %s", exc)
                self._send_json(503, {
                    "supported": platform.system() == "Windows",
                    "message": "Не удалось получить список дисков.",
                    "error": str(exc),
                    "disks": [],
                })
            return

        if path == "/" or path == "/index.html":
            self._send_file(FRONTEND_DIR / "index.html")
            return

        # Only files inside frontend/ can be served. Resolve + relative_to blocks traversal.
        relative = path.lstrip("/")
        candidate = (FRONTEND_DIR / relative).resolve()
        try:
            candidate.relative_to(FRONTEND_DIR.resolve())
        except ValueError:
            self.send_error(403, "Forbidden")
            return

        if candidate.is_file():
            self._send_file(candidate)
        else:
            self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        self._send_json(405, {
            "error": "Методы изменения данных пока не подключены.",
            "read_only": True,
        })


class LocalThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server() -> None:
    try:
        server = LocalThreadingHTTPServer((HOST, PORT), AppHandler)
    except OSError as exc:
        logger.error("Не удалось запустить сервер на %s:%s: %s", HOST, PORT, exc)
        raise SystemExit(
            f"Порт {PORT} недоступен. Закройте другое приложение, использующее этот порт, "
            "или измените PORT в backend/server.py."
        ) from exc

    logger.info("Ventoy Manager Studio запущена: http://%s:%s", HOST, PORT)
    logger.info("Режим первого этапа: локальный интерфейс и диагностика (только чтение).")
    threading.Timer(1.0, webbrowser.open, args=(f"http://{HOST}:{PORT}",)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Получена команда остановки.")
    finally:
        server.server_close()
        logger.info("Сервер остановлен.")
