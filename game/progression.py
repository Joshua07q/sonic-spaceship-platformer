"""World/level tracking, unlocks, save/load."""
import json
import os
from settings import SAVE_FILE


class Progression:
    def __init__(self):
        self.character = "sonic"
        self.current_world = 1
        self.current_level = 1
        self.lives = 3
        self.total_rings = 0
        self.best_times = {}
        self.bosses_defeated = []

    def advance_level(self):
        """Move to the next level. Returns True if game completed."""
        if self.current_level < 4:
            self.current_level += 1
        elif self.current_world < 5:
            self.current_world += 1
            self.current_level = 1
        else:
            return True  # Game complete!
        return False

    def is_boss_level(self):
        return self.current_level == 4

    def is_chase_level(self):
        return self.current_level == 3

    def record_time(self, time_seconds):
        key = f"{self.current_world}-{self.current_level}"
        if key not in self.best_times or time_seconds < self.best_times[key]:
            self.best_times[key] = time_seconds

    def record_boss_defeated(self, world):
        boss_name = f"boss_{world}"
        if boss_name not in self.bosses_defeated:
            self.bosses_defeated.append(boss_name)

    def save(self):
        data = {
            "character": self.character,
            "current_world": self.current_world,
            "current_level": self.current_level,
            "lives": self.lives,
            "total_rings": self.total_rings,
            "best_times": self.best_times,
            "bosses_defeated": self.bosses_defeated,
        }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load(self):
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                self.character = data.get("character", "sonic")
                self.current_world = data.get("current_world", 1)
                self.current_level = data.get("current_level", 1)
                self.lives = data.get("lives", 3)
                self.total_rings = data.get("total_rings", 0)
                self.best_times = data.get("best_times", {})
                self.bosses_defeated = data.get("bosses_defeated", [])
                return True
        except Exception:
            pass
        return False

    def has_save(self):
        return os.path.exists(SAVE_FILE)

    def reset(self):
        self.current_world = 1
        self.current_level = 1
        self.lives = 3
        self.total_rings = 0
        self.best_times = {}
        self.bosses_defeated = []
