"""WiFi start-up on both the MicroPython 1.29 API and the older one."""
import sys
import types
import unittest

import fakehw  # noqa: F401
import settings


def fake_network(new_api):
    log = []

    class WLAN:
        def __init__(self, iface):
            self.iface = iface
            self.cfg = {}
            self.on = False

        def active(self, v=None):
            if v is None:
                return self.on
            self.on = v

        def config(self, *a, **kw):
            if a:
                return b"\x01\x02\x03\x04\x05\x06"
            if new_api and ("password" in kw or "authmode" in kw):
                raise ValueError("unknown config param")
            if not new_api and ("key" in kw or "security" in kw):
                raise ValueError("unknown config param")
            self.cfg.update(kw)
            log.append((self.iface, kw))

        def ifconfig(self):
            return ("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8")

        def isconnected(self):
            return False

    m = types.ModuleType("network")
    m.WLAN = WLAN
    m.hostname = lambda n=None: None
    if new_api:
        WLAN.IF_STA, WLAN.IF_AP = 0, 1
        WLAN.SEC_OPEN, WLAN.SEC_WPA2 = 0, 3
    else:
        m.STA_IF, m.AP_IF = 0, 1
        m.AUTH_OPEN, m.AUTH_WPA_WPA2_PSK = 0, 4
    return m, log


class WifiTests(unittest.TestCase):
    def run_start(self, new_api, **over):
        m, log = fake_network(new_api)
        sys.modules["network"] = m
        sys.modules.pop("net", None)
        import net
        s = settings.Settings("/nonexistent.json")
        s.update(over, persist=False)
        return net.start_wifi(s), log

    def test_micropython_1_29_api(self):
        info, log = self.run_start(True, ap_channel=6)
        self.assertEqual(info["error"], "")
        self.assertEqual(info["ap_ip"], "192.168.4.1")
        iface, kw = log[0]
        self.assertEqual((iface, kw["ssid"], kw["key"], kw["security"], kw["channel"]), (1, "2FastTarget", "2fasttarget", 3, 6))
        self.assertNotIn("password", kw)

    def test_open_network_1_29(self):
        info, log = self.run_start(True, ap_password="")
        self.assertEqual(info["error"], "")
        self.assertEqual(log[0][1]["security"], 0)
        self.assertNotIn("key", log[0][1])

    def test_legacy_api(self):
        info, log = self.run_start(False)
        self.assertEqual(info["error"], "")
        kw = log[0][1]
        self.assertEqual((kw["password"], kw["authmode"]), ("2fasttarget", 4))


if __name__ == "__main__":
    unittest.main()
