"""Results history and personal bests, persisted on flash."""
import json
import os

RESULTS_FILE = "results.json"
KEEP = 15

# mode -> (field, True if lower is better)
METRIC = {
    "sequence": ("total", True),
    "multi": ("total", True),
    "reflex": ("avg", True),
    "timed": ("hits", False),
}
COMPACT = ("mode", "total", "hits", "miss", "err", "avg", "best", "aborted")


class Scoreboard:
    def __init__(self, path=RESULTS_FILE):
        self.path = path
        self.recent = []
        self.best = {}
        self.next_n = 1

    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.recent = [r for r in d.get("recent", []) if isinstance(r, dict)][-KEEP:]
            self.best = d.get("best", {}) if isinstance(d.get("best"), dict) else {}
            self.next_n = int(d.get("next", 1))
        except (OSError, ValueError, TypeError):
            self.recent, self.best, self.next_n = [], {}, 1

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"recent": self.recent, "best": self.best, "next": self.next_n}, f)
            try:
                os.remove(self.path)
            except OSError:
                pass
            os.rename(tmp, self.path)
        except OSError as err:
            print("results save failed:", err)

    def record(self, result):
        """Store a finished game. Returns (n, is_new_record)."""
        n = self.next_n
        self.next_n += 1
        entry = {k: result.get(k) for k in COMPACT}
        entry["n"] = n
        self.recent.append(entry)
        del self.recent[:-KEEP]

        record = False
        metric = METRIC.get(result["mode"])
        if metric and not result["aborted"]:
            field, lower = metric
            value = result.get(field)
            if value is not None:
                cur = self.best.get(result["mode"])
                if cur is None or (value < cur["v"] if lower else value > cur["v"]):
                    self.best[result["mode"]] = {"v": value, "n": n}
                    record = True
        self.save()
        return n, record

    def clear(self):
        self.recent, self.best = [], {}
        self.save()

    def snapshot(self):
        return {"recent": self.recent, "best": self.best}
