"""Сохранения: JSON, атомарная запись, защита от повреждённых файлов."""
import copy
import json
import os
from pathlib import Path

from .settings import SAVE_DIR

SINS = ("greed", "sloth", "aggression", "egoism", "cunning", "mercy")

DEFAULT_SAVE = {
    "version": 1,
    "runs": 0,
    "wins": 0,
    "best_rooms_cleared": 0,
    "seen_items": [],
    "testimonies": [],
    "legacy_sins": {s: 0 for s in SINS},
    "settings": {"volume": 0.6, "screen_shake": True, "fill": "blur", "show_fps": False},
    "endings": [],
    "current_run": None,
}


class SaveSystem:
    def __init__(self, path=None):
        self.path = Path(path) if path else SAVE_DIR / "save.json"
        self.data = self.load()

    def load(self):
        data = copy.deepcopy(DEFAULT_SAVE)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return data
        except (OSError, json.JSONDecodeError):
            self._backup_corrupt()
            return data
        if not isinstance(raw, dict):
            self._backup_corrupt()
            return data
        for key, default in DEFAULT_SAVE.items():
            value = raw.get(key, default)
            if type(value) is type(default) or default is None:
                data[key] = value
        # вложенные словари
        for key in ("legacy_sins", "settings"):
            merged = copy.deepcopy(DEFAULT_SAVE[key])
            if isinstance(raw.get(key), dict):
                merged.update(raw[key])
            data[key] = merged
        return data

    def _backup_corrupt(self):
        try:
            os.replace(self.path, self.path.with_suffix(".corrupt"))
        except OSError:
            pass

    def write(self):
        """Атомарная запись. Возвращает True при успехе."""
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            return False
        return True
