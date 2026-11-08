"""WiFi: access point (always on) + optional station connection."""
import asyncio
import binascii

import network


def wlan(kind):
    """WLAN interface "STA" or "AP" on MicroPython 1.29+ (network.WLAN.IF_*)
    and on older firmware (network.STA_IF / AP_IF)."""
    const = getattr(network.WLAN, "IF_" + kind, None)
    if const is None:
        const = getattr(network, kind + "_IF")
    return network.WLAN(const)


def config_ap(ap, ssid, password, channel):
    """Configure the access point with the 1.29 API (key=, security=), falling
    back to the older one (password=, authmode=)."""
    W = network.WLAN
    if hasattr(W, "SEC_OPEN"):
        kw = {"ssid": ssid, "channel": channel}
        if password:
            kw["key"] = password
            kw["security"] = W.SEC_WPA2
        else:
            kw["security"] = W.SEC_OPEN
        ap.config(**kw)
        return
    kw = {"ssid": ssid, "channel": channel}
    if password:
        kw["password"] = password
        kw["authmode"] = getattr(network, "AUTH_WPA_WPA2_PSK", None) or getattr(network, "AUTH_WPA2_PSK", 3)
    else:
        kw["authmode"] = getattr(network, "AUTH_OPEN", 0)
    ap.config(**kw)


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
        sta = wlan("STA")
        sta.active(True)
        ap = wlan("AP")
        ap.active(True)
        config_ap(ap, s["ap_ssid"], s["ap_password"], s["ap_channel"])
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
