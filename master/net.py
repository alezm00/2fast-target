"""WiFi (access point + optional station) and the ESP-NOW radio remote."""
import asyncio
import binascii

import network

PREFIX = "2FT"


def _mac(wlan):
    try:
        return binascii.hexlify(wlan.config("mac"), ":").decode()
    except Exception:
        return ""


def start_wifi(s):
    """Bring up the access point (always) and the station interface.
    Returns an info dict used by the web UI. Never raises."""
    info = {"ap_ssid": s["ap_ssid"], "ap_ip": "", "sta_ip": "", "sta_ssid": s["sta_ssid"],
            "channel": s["ap_channel"], "ap_mac": "", "sta_mac": "", "error": ""}
    try:
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        pw = s["ap_password"]
        kw = {"ssid": s["ap_ssid"], "channel": s["ap_channel"]}
        if pw:
            kw["password"] = pw
            auth = getattr(network, "AUTH_WPA_WPA2_PSK", None) or getattr(network, "AUTH_WPA2_PSK", 3)
        else:
            auth = getattr(network, "AUTH_OPEN", 0)
        try:
            ap.config(authmode=auth, **kw)
        except (ValueError, TypeError):
            ap.config(security=auth, **kw)
        try:
            network.hostname("2fast-target")
        except Exception:
            pass
        info["ap_ip"] = ap.ifconfig()[0]
        info["ap_mac"] = _mac(ap)
        info["sta_mac"] = _mac(sta)
        info["sta"] = sta
        info["ap"] = ap
        print("AP", s["ap_ssid"], info["ap_ip"], "channel", s["ap_channel"])
    except Exception as err:
        info["error"] = repr(err)
        print("WiFi start failed:", err)
    return info


async def sta_supervisor(info, s):
    """Keep trying to join the configured network (if any)."""
    sta = info.get("sta")
    if sta is None or not s["sta_ssid"]:
        return
    while True:
        try:
            if not sta.isconnected():
                sta.connect(s["sta_ssid"], s["sta_password"])
                for _ in range(20):
                    await asyncio.sleep(1)
                    if sta.isconnected():
                        break
            info["sta_ip"] = sta.ifconfig()[0] if sta.isconnected() else ""
        except Exception as err:
            print("STA error:", err)
        await asyncio.sleep(10)


class RemoteListener:
    """Receives START/STOP/TOGGLE commands from the radio remote (ESP-NOW,
    broadcast frames "2FT|code|id|command"). Frames are repeated by the sender,
    so duplicates (same id) are dropped here."""

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.seen = []

    def handle(self, text):
        parts = text.split("|")
        if len(parts) != 4 or parts[0] != PREFIX:
            return None
        if parts[1] != self.settings["remote_secret"]:
            return None
        if parts[2] in self.seen:
            return None
        self.seen.append(parts[2])
        del self.seen[:-8]
        cmd = parts[3]
        app = self.app
        if cmd == "STOP":
            app.cmd_stop("remote")
        elif cmd == "TOGGLE":
            app.cmd_toggle("remote")
        elif cmd.startswith("START"):
            mode = cmd[6:] if cmd.startswith("START:") else None
            app.cmd_start(mode or None, None, "remote")
        else:
            return None
        return cmd

    async def run(self):
        import aioespnow
        e = aioespnow.AIOESPNow()
        e.active(True)
        print("ESP-NOW remote receiver ready")
        try:
            while True:
                try:
                    async for mac, msg in e:
                        try:
                            cmd = self.handle(msg.decode())
                            if cmd:
                                print("remote command:", cmd)
                        except Exception as err:
                            print("remote message error:", repr(err))
                except OSError as err:
                    print("ESP-NOW receive error:", err)
                    await asyncio.sleep(1)
        finally:
            e.active(False)
