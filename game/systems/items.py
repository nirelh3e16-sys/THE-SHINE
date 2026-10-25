"""Данные предметов, расчёт характеристик и комбинации."""
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import DATA_DIR

BASE_STATS = {
    "damage": 3.0,
    "fire_delay": 0.38,
    "shot_speed": 220.0,
    "range": 0.9,      # время жизни снаряда, сек
    "luck": 0.0,
    "max_hp": 6.0,     # 2 единицы = 1 сердце
    "speed": 105.0,
}
STAT_MIN = {"damage": 0.5, "fire_delay": 0.1, "shot_speed": 60.0, "range": 0.1, "max_hp": 2.0, "speed": 50.0, "luck": -5.0}
VALID_OPS = ("add", "mul")


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    desc: str
    icon: str
    color: tuple
    mods: dict = field(default_factory=dict)
    flags: tuple = ()
    active: dict = None


class ItemDatabase:
    def __init__(self, items, combos):
        self.items = items      # id -> ItemDef
        self.combos = combos    # список словарей

    @classmethod
    def from_file(cls, path=None):
        path = Path(path) if path else DATA_DIR / "items.json"
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = {}
        for entry in raw.get("items", []):
            for key in ("id", "name", "desc", "icon", "color"):
                if key not in entry:
                    raise ValueError(f"предмет без поля '{key}': {entry}")
            mods = entry.get("mods", {})
            for stat, (op, value) in mods.items():
                if stat not in BASE_STATS or op not in VALID_OPS:
                    raise ValueError(f"некорректный модификатор {stat} у {entry['id']}")
            if entry["id"] in items:
                raise ValueError(f"повторяющийся id предмета {entry['id']}")
            items[entry["id"]] = ItemDef(
                id=entry["id"], name=entry["name"], desc=entry["desc"], icon=entry["icon"],
                color=tuple(entry["color"]), mods={k: tuple(v) for k, v in mods.items()},
                flags=tuple(entry.get("flags", [])), active=entry.get("active"))
        combos = raw.get("combos", [])
        for combo in combos:
            for need in combo["needs"]:
                if need not in items:
                    raise ValueError(f"комбинация {combo['id']} ссылается на неизвестный предмет {need}")
        return cls(items, combos)

    def stats(self, owned, extra_mods=()):
        """Итоговые характеристики: сначала все 'add', затем все 'mul'.

        extra_mods — список (stat, op, value) от событий и временных бонусов.
        """
        mods = []
        for item_id in owned:
            for stat, (op, value) in self.items[item_id].mods.items():
                mods.append((stat, op, value))
        mods.extend(extra_mods)
        stats = dict(BASE_STATS)
        for stat, op, value in mods:
            if op == "add":
                stats[stat] += value
        for stat, op, value in mods:
            if op == "mul":
                stats[stat] *= value
        for stat, low in STAT_MIN.items():
            stats[stat] = max(low, stats[stat])
        return stats

    def card_options(self, owned, rng, n=3):
        """До n случайных предметов, которых у игрока ещё нет (для карточек)."""
        pool = sorted(i for i in self.items if i not in set(owned))
        return rng.sample(pool, min(n, len(pool)))

    def active_combos(self, owned):
        have = set(owned)
        return [c for c in self.combos if all(n in have for n in c["needs"])]

    def flags(self, owned):
        result = set()
        for item_id in owned:
            result.update(self.items[item_id].flags)
        for combo in self.active_combos(owned):
            result.add(combo["flag"])
        return result
