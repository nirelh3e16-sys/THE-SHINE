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
STAT_MIN = {"damage": 0.5, "fire_delay": 0.1, "shot_speed": 60.0, "range": 0.1, "max_hp": 1.0, "speed": 50.0, "luck": -5.0}
VALID_OPS = ("add", "mul")
RARITIES = ("common", "uncommon", "rare", "divine")   # обычный, необычный, редкий, божественный
THEMES = ("bible", "slavic", "greek")                  # библейские, древнерусские, греческие артефакты
RARITY_NAMES = {"common": "Обычный", "uncommon": "Необычный", "rare": "Редкий", "divine": "Божественный"}
THEME_NAMES = {"bible": "Библейский", "slavic": "Древнерусский", "greek": "Греческий"}


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
    drop_only: bool = False   # выпадает только с мини-боссов: не попадает в магазины, сокровищницы и карточки
    num: int = 0              # числовой номер предмета: уникален, как и id (команда консоли give принимает и то и другое)
    rarity: str = None        # common / uncommon / rare / divine (у артефактов 1.1.0)
    theme: str = None         # bible / slavic / greek (у артефактов 1.1.0)


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
        numbers = {}
        for entry in raw.get("items", []):
            for key in ("id", "name", "desc", "icon", "color"):
                if key not in entry:
                    raise ValueError(f"предмет без поля '{key}': {entry}")
            mods = entry.get("mods", {})
            for stat, (op, value) in mods.items():
                if stat not in BASE_STATS or op not in VALID_OPS:
                    raise ValueError(f"некорректный модификатор {stat} у {entry['id']}")
            active = entry.get("active")
            if active is not None:
                by_time = float(active.get("cooldown", 0)) > 0
                by_kills = active.get("recharge") == "kills" and int(active.get("kills", 0)) > 0
                if "type" not in active or not (by_time or by_kills):
                    raise ValueError(f"предмет {entry['id']}: у активного предмета нужны type и перезарядка")
            if entry["id"] in items:
                raise ValueError(f"повторяющийся id предмета {entry['id']}")
            num = int(entry.get("num", 0))
            if num:
                if num in numbers:
                    raise ValueError(f"повторяющийся номер {num}: {numbers[num]} и {entry['id']}")
                numbers[num] = entry["id"]
            if entry.get("rarity") is not None and entry["rarity"] not in RARITIES:
                raise ValueError(f"предмет {entry['id']}: неизвестная редкость {entry['rarity']}")
            if entry.get("theme") is not None and entry["theme"] not in THEMES:
                raise ValueError(f"предмет {entry['id']}: неизвестная тема {entry['theme']}")
            items[entry["id"]] = ItemDef(
                id=entry["id"], name=entry["name"], desc=entry["desc"], icon=entry["icon"],
                color=tuple(entry["color"]), mods={k: tuple(v) for k, v in mods.items()},
                flags=tuple(entry.get("flags", [])), active=entry.get("active"),
                drop_only=bool(entry.get("drop_only", False)), num=num,
                rarity=entry.get("rarity"), theme=entry.get("theme"))
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

    def resolve(self, token):
        """Найти предмет по id, числовому номеру или однозначному началу id (для консоли). Нет такого — None."""
        token = str(token).strip().lower()
        if token in self.items:
            return token
        if token.isdigit():
            return next((i for i, d in self.items.items() if d.num == int(token)), None)
        starts = [i for i in self.items if i.startswith(token)] if token else []
        return starts[0] if len(starts) == 1 else None

    def regular_ids(self):
        """Предметы, которые могут лежать в магазинах и сокровищницах (без наград мини-боссов)."""
        return sorted(i for i, d in self.items.items() if not d.drop_only)

    def card_options(self, owned, rng, n=3):
        """До n случайных предметов, которых у игрока ещё нет (для карточек)."""
        pool = sorted(i for i, d in self.items.items() if i not in set(owned) and not d.drop_only)
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
