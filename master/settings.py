"""Persistent, validated settings (JSON file on flash).

SCHEMA drives validation *and* the settings form of the web interface.
"""
import json
import os

from config import N

SETTINGS_FILE = "settings.json"

MODE_IDS = ("sequence", "reflex", "timed", "multi", "demo")

# key, kind, default, a, b, group, label
#   int:    a=min, b=max     bool: -      str: a=min length, b=max length
#   choice: a=choices
SCHEMA = (
    ("default_mode", "choice", "sequence", MODE_IDS, None, "game", "Modalità predefinita"),
    ("countdown_enabled", "bool", True, None, None, "game", "Semaforo di partenza"),
    ("countdown_step_ms", "int", 800, 100, 3000, "game", "Semaforo: durata di ogni riga (ms)"),
    ("countdown_rand_ms", "int", 1000, 0, 5000, "game", "Semaforo: attesa casuale massima (ms)"),
    ("finish_blink", "bool", True, None, None, "game", "Lampeggio a fine partita"),

    ("seq_timeout_ms", "int", 5000, 300, 60000, "sequence", "Tempo massimo per bersaglio (ms)"),
    ("seq_wrong_penalty_ms", "int", 0, 0, 10000, "sequence", "Penalità colpo errato (ms)"),
    ("seq_miss_penalty_ms", "int", 0, 0, 10000, "sequence", "Penalità bersaglio mancato (ms)"),

    ("reflex_rounds", "int", 10, 1, 100, "reflex", "Numero di round"),
    ("reflex_timeout_ms", "int", 2000, 200, 20000, "reflex", "Tempo massimo di reazione (ms)"),
    ("reflex_min_delay_ms", "int", 500, 0, 10000, "reflex", "Attesa minima prima del bersaglio (ms)"),
    ("reflex_max_delay_ms", "int", 2500, 0, 20000, "reflex", "Attesa massima prima del bersaglio (ms)"),

    ("timed_duration_s", "int", 30, 5, 600, "timed", "Durata (s)"),
    ("timed_timeout_ms", "int", 0, 0, 20000, "timed", "Tempo massimo per bersaglio (ms, 0 = nessuno)"),

    ("multi_simultaneous", "int", 3, 2, 8, "multi", "Bersagli accesi insieme"),
    ("multi_timeout_ms", "int", 8000, 0, 60000, "multi", "Tempo massimo per bersaglio (ms, 0 = nessuno)"),

    ("demo_timeout_ms", "int", 10000, 300, 60000, "demo", "Tempo massimo per bersaglio (ms)"),

    ("scan_ms", "int", 2, 1, 20, "input", "Periodo di scansione tastiera (ms)"),
    ("debounce_ms", "int", 8, 1, 100, "input", "Antirimbalzo (ms)"),
    ("settle_us", "int", 30, 0, 500, "input", "Assestamento colonna (µs)"),
    ("ghost_filter", "bool", True, None, None, "input", "Filtro tasti fantasma"),
    ("stuck_ms", "int", 3000, 500, 60000, "input", "Bersaglio bloccato dopo (ms)"),

    ("ap_ssid", "str", "2FastTarget", 1, 32, "wifi", "Nome rete WiFi (access point)"),
    ("ap_password", "str", "2fasttarget", 0, 63, "wifi", "Password WiFi (min. 8 caratteri, vuota = rete aperta)"),
    ("ap_channel", "int", 1, 1, 13, "wifi", "Canale WiFi / ESP-NOW"),
    ("sta_ssid", "str", "", 0, 32, "wifi", "Collegati anche a questa rete (opzionale)"),
    ("sta_password", "str", "", 0, 63, "wifi", "Password della rete"),

    ("remote_secret", "str", "2fast", 1, 16, "remote", "Codice di abbinamento telecomando"),
)

KEYS = tuple(s[0] for s in SCHEMA)
_BY_KEY = {s[0]: s for s in SCHEMA}
# keys that need a reboot to take effect
REBOOT_KEYS = ("ap_ssid", "ap_password", "ap_channel", "sta_ssid", "sta_password")


def _coerce(spec, value):
    """Return (ok, value). Never raises."""
    kind = spec[1]
    try:
        if kind == "int":
            if isinstance(value, bool) or isinstance(value, float) and value != int(value):
                return False, None
            if isinstance(value, str):
                value = int(value.strip())
            value = int(value)
            if spec[3] <= value <= spec[4]:
                return True, value
            return False, None
        if kind == "bool":
            if isinstance(value, bool):
                return True, value
            if value in (0, 1):
                return True, bool(value)
            if isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
                return True, value.lower() in ("true", "1")
            return False, None
        if kind == "str":
            if not isinstance(value, str):
                return False, None
            if spec[3] <= len(value) <= spec[4]:
                if spec[0] == "ap_password" and 0 < len(value) < 8:
                    return False, None
                return True, value
            return False, None
        if kind == "choice":
            if value in spec[3]:
                return True, value
            return False, None
    except (ValueError, TypeError):
        pass
    return False, None


def _valid_keymap(v):
    return (
        isinstance(v, list) and len(v) == N
        and all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x < N for x in v)
        and len(set(v)) == N
    )


def _valid_enabled(v):
    return isinstance(v, list) and len(v) == N and all(isinstance(x, bool) for x in v)


class Settings:
    def __init__(self, path=SETTINGS_FILE):
        self.path = path
        self.v = {}
        self.keymap = list(range(N))      # target (LED) index -> key index
        self.enabled = [True] * N         # per target
        self.reset_values()

    # ---- access -----------------------------------------------------------
    def __getitem__(self, key):
        return self.v[key]

    def get(self, key):
        return self.v[key]

    def reset_values(self):
        self.v = {s[0]: s[2] for s in SCHEMA}
        self.keymap = list(range(N))
        self.enabled = [True] * N

    def key_to_target(self):
        inv = [0] * N
        for t, k in enumerate(self.keymap):
            inv[k] = t
        return inv

    def enabled_targets(self):
        return [i for i in range(N) if self.enabled[i]]

    # ---- persistence ------------------------------------------------------
    def load(self):
        """Load from flash. A missing/corrupt file falls back to defaults;
        individually invalid values fall back to their default."""
        self.reset_values()
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict):
            return False
        for spec in SCHEMA:
            if spec[0] in data:
                ok, val = _coerce(spec, data[spec[0]])
                if ok:
                    self.v[spec[0]] = val
        if _valid_keymap(data.get("keymap")):
            self.keymap = list(data["keymap"])
        if _valid_enabled(data.get("enabled")):
            self.enabled = list(data["enabled"])
        return True

    def save(self):
        data = dict(self.v)
        data["keymap"] = self.keymap
        data["enabled"] = self.enabled
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(data, f)
            try:
                os.remove(self.path)
            except OSError:
                pass
            os.rename(tmp, self.path)
            return True
        except OSError as err:
            print("settings save failed:", err)
            return False

    # ---- updates ----------------------------------------------------------
    def validate(self, changes):
        """Return (clean, errors) without applying anything."""
        clean, errors = {}, {}
        for key, value in changes.items():
            if key == "keymap":
                if _valid_keymap(value):
                    clean[key] = list(value)
                else:
                    errors[key] = "mappa non valida"
            elif key == "enabled":
                if _valid_enabled(value) and any(value):
                    clean[key] = list(value)
                else:
                    errors[key] = "serve almeno un bersaglio attivo"
            elif key in _BY_KEY:
                ok, val = _coerce(_BY_KEY[key], value)
                if ok:
                    clean[key] = val
                else:
                    errors[key] = "valore non valido"
            else:
                errors[key] = "parametro sconosciuto"
        # cross-field rules
        merged = dict(self.v)
        merged.update({k: v for k, v in clean.items() if k in _BY_KEY})
        if merged["reflex_min_delay_ms"] > merged["reflex_max_delay_ms"]:
            errors["reflex_min_delay_ms"] = "il minimo supera il massimo"
        return clean, errors

    def update(self, changes, persist=True):
        """Apply valid changes atomically. Returns (changed_keys, errors)."""
        clean, errors = self.validate(changes)
        if errors:
            return [], errors
        changed = []
        for key, val in clean.items():
            if key == "keymap":
                cur = self.keymap
            elif key == "enabled":
                cur = self.enabled
            else:
                cur = self.v[key]
            if cur != val:
                changed.append(key)
            if key == "keymap":
                self.keymap = val
            elif key == "enabled":
                self.enabled = val
            else:
                self.v[key] = val
        if changed and persist:
            self.save()
        return changed, {}

    def factory_reset(self):
        self.reset_values()
        try:
            os.remove(self.path)
        except OSError:
            pass
