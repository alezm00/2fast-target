"""Minimal asynchronous HTTP server + JSON API for the web interface."""
import asyncio
import gc
import json
import os
from time import ticks_ms, ticks_diff

import config
import games
import settings as settings_mod

MAX_BODY = 4096
MAX_CONN = 6
CHUNK = 1024

REASONS = {200: "OK", 204: "No Content", 400: "Bad Request", 404: "Not Found",
           405: "Method Not Allowed", 409: "Conflict", 413: "Payload Too Large",
           500: "Internal Server Error", 503: "Service Unavailable"}


class WebServer:
    def __init__(self, app, net_info, port=config.HTTP_PORT, root="web", reboot=None):
        self.app = app
        self.net = net_info
        self.port = port
        self.root = root
        self.reboot = reboot or (lambda: None)
        self.active = 0
        self.server = None
        self.routes = {
            ("GET", "/api/state"): self.api_state,
            ("GET", "/api/result"): self.api_result,
            ("GET", "/api/info"): self.api_info,
            ("GET", "/api/config"): self.api_config,
            ("POST", "/api/config"): self.api_config_set,
            ("POST", "/api/config/reset"): self.api_config_reset,
            ("POST", "/api/start"): self.api_start,
            ("POST", "/api/stop"): self.api_stop,
            ("POST", "/api/appmode"): self.api_appmode,
            ("POST", "/api/test/led"): self.api_test_led,
            ("POST", "/api/test/learn"): self.api_test_learn,
            ("POST", "/api/test/reset"): self.api_test_reset,
            ("GET", "/api/results"): self.api_results,
            ("POST", "/api/results/clear"): self.api_results_clear,
            ("POST", "/api/reboot"): self.api_reboot,
        }

    # ---- server -----------------------------------------------------------
    async def serve(self):
        self.server = await asyncio.start_server(self._client, "0.0.0.0", self.port)
        print("HTTP server on port", self.port)
        while True:
            await asyncio.sleep(3600)

    async def _client(self, reader, writer):
        if self.active >= MAX_CONN:
            try:
                await self._send(writer, 503, b'{"error":"busy"}')
            except Exception:
                pass
            await self._close(writer)
            return
        self.active += 1
        try:
            await asyncio.wait_for(self._request(reader, writer), 10)
        except Exception as err:   # timeout, reset by peer, malformed request...
            if not isinstance(err, OSError):
                print("http:", repr(err))
        finally:
            self.active -= 1
            await self._close(writer)

    @staticmethod
    async def _close(writer):
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    async def _send(self, writer, code, body, ctype="application/json", extra=""):
        head = "HTTP/1.0 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n%s\r\n" % (
            code, REASONS.get(code, "OK"), ctype, len(body), extra)
        writer.write(head.encode())
        if body:
            writer.write(body)
        await writer.drain()

    async def _request(self, reader, writer):
        line = await reader.readline()
        if not line:
            return
        try:
            method, target, _ = line.decode().split(" ", 2)
        except ValueError:
            await self._send(writer, 400, b'{"error":"bad request"}')
            return
        length = 0
        for _ in range(40):
            h = await reader.readline()
            if h in (b"\r\n", b"\n", b""):
                break
            if h[:15].lower() == b"content-length:":
                try:
                    length = int(h[15:].strip())
                except ValueError:
                    length = -1
        if length < 0 or length > MAX_BODY:
            await self._send(writer, 413, b'{"error":"too large"}')
            return
        body = b""
        if length:
            body = await reader.readexactly(length)
        path = target.split("?", 1)[0]

        if method == "GET" and path in ("/", "/index.html"):
            await self._static(writer, "index.html")
            return
        if method == "GET" and path == "/favicon.ico":
            await self._send(writer, 204, b"")
            return
        handler = self.routes.get((method, path))
        if handler is None:
            known = [p for (m, p) in self.routes if p == path]
            await self._send(writer, 405 if known else 404, b'{"error":"not found"}')
            return
        data = {}
        if method == "POST" and body:
            try:
                data = json.loads(body)
            except ValueError:
                await self._send(writer, 400, b'{"error":"invalid JSON"}')
                return
            if not isinstance(data, dict):
                await self._send(writer, 400, b'{"error":"JSON object expected"}')
                return
        try:
            code, obj = handler(data)
        except Exception as err:
            print("api error:", path, repr(err))
            code, obj = 500, {"error": "internal error"}
        await self._send(writer, code, json.dumps(obj).encode())

    async def _static(self, writer, name):
        path = self.root + "/" + name
        try:
            size = os.stat(path)[6]
            f = open(path, "rb")
        except OSError:
            await self._send(writer, 404, b"missing web/index.html")
            return
        try:
            head = "HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n" % size
            writer.write(head.encode())
            buf = bytearray(CHUNK)
            mv = memoryview(buf)
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                writer.write(mv[:n])
                await writer.drain()
        finally:
            f.close()

    # ---- API ----------------------------------------------------------------
    def api_state(self, d):
        return 200, self.app.state()

    def api_result(self, d):
        return 200, {"rid": self.app.session.rid, "result": self.app.session.result}

    def api_info(self, d):
        n = self.net
        mods = [{"id": m[0], "name": m[1], "desc": m[2], "params": list(m[3])} for m in games.MODES]
        schema = [list(s) for s in settings_mod.SCHEMA]
        return 200, {
            "version": config.VERSION,
            "rows": config.ROWS, "cols": config.COLS,
            "modes": mods, "schema": schema,
            "reboot_keys": list(settings_mod.REBOOT_KEYS),
            "net": {k: n.get(k, "") for k in ("ap_ssid", "ap_ip", "sta_ssid", "sta_ip", "channel", "ap_mac", "sta_mac", "error")},
            "free": self.app.free_mem(),
            "uptime": ticks_diff(ticks_ms(), self.app.boot_ms) // 1000,
        }

    def api_config(self, d):
        s = self.app.settings
        return 200, {"values": s.v, "keymap": s.keymap, "enabled": s.enabled}

    def api_config_set(self, d):
        s = self.app.settings
        changed, errors = s.update(d)
        if errors:
            return 400, {"errors": errors}
        self.app.apply_settings()
        reboot = any(k in settings_mod.REBOOT_KEYS for k in changed)
        return 200, {"ok": True, "changed": changed, "reboot": reboot}

    def api_config_reset(self, d):
        self.app.settings.factory_reset()
        self.app.apply_settings()
        return 200, {"ok": True, "reboot": True}

    def api_start(self, d):
        mode = d.get("mode")
        if mode is not None and mode not in games.MODE_IDS:
            return 400, {"error": "modalità sconosciuta"}
        ok, msg = self.app.cmd_start(mode, "web")
        return (200, {"ok": True}) if ok else (409, {"error": msg})

    def api_stop(self, d):
        ok, msg = self.app.cmd_stop("web")
        return (200, {"ok": True}) if ok else (409, {"error": msg})

    def api_appmode(self, d):
        ok, msg = self.app.set_app_mode(d.get("mode"))
        return (200, {"ok": True}) if ok else (400, {"error": msg})

    def api_test_led(self, d):
        a = self.app
        if "pattern" in d:
            ok = a.test_pattern(d["pattern"])
        elif "mask" in d and isinstance(d["mask"], int):
            ok = a.test_set_mask(d["mask"])
        elif isinstance(d.get("i"), int):
            ok = a.test_set_led(d["i"], bool(d.get("on", True)))
        else:
            ok = False
        return (200, {"ok": True}) if ok else (409, {"error": "richiede la modalità test"})

    def api_test_learn(self, d):
        ok, msg = self.app.learn_cmd(d.get("action"))
        return (200, {"ok": True}) if ok else (409, {"error": msg})

    def api_test_reset(self, d):
        self.app.keypad.clear_stats()
        return 200, {"ok": True}

    def api_results(self, d):
        return 200, self.app.board.snapshot()

    def api_results_clear(self, d):
        self.app.board.clear()
        return 200, {"ok": True}

    def api_reboot(self, d):
        asyncio.create_task(self._delayed_reboot())
        return 200, {"ok": True}

    async def _delayed_reboot(self):
        await asyncio.sleep_ms(500)
        self.reboot()
