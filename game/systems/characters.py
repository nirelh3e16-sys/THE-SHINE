"""Играбельные персонажи: данные, проверка и открытие за победы над боссами."""
import json
from pathlib import Path

from ..settings import DATA_DIR
from .items import BASE_STATS, VALID_OPS

TRAITS = ("ghost", "gravity_immune")
DEFAULT_ID = "rob"


def load_characters(item_db, path=None):
    """Возвращает упорядоченный dict id -> данные персонажа. Ошибки в данных — ValueError."""
    path = Path(path) if path else DATA_DIR / "characters.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    result = {}
    for c in raw.get("characters", []):
        for key in ("id", "name", "desc", "mods", "start_items"):
            if key not in c:
                raise ValueError(f"персонаж без поля '{key}': {c.get('id')}")
        if c["id"] in result:
            raise ValueError(f"повторяющийся id персонажа {c['id']}")
        for stat, op, _value in c["mods"]:
            if stat not in BASE_STATS or op not in VALID_OPS:
                raise ValueError(f"персонаж {c['id']}: некорректный модификатор {stat}/{op}")
        for item_id in c["start_items"]:
            if item_id not in item_db.items:
                raise ValueError(f"персонаж {c['id']}: неизвестный предмет {item_id}")
        for trait in c.get("traits", []):
            if trait not in TRAITS:
                raise ValueError(f"персонаж {c['id']}: неизвестная особенность {trait}")
        unlock = c.get("unlock")
        if unlock is not None and not (isinstance(unlock.get("boss"), str) and int(unlock.get("kills", 0)) > 0):
            raise ValueError(f"персонаж {c['id']}: неверное условие открытия")
        result[c["id"]] = {"scale": 1.0, "traits": [], "unlock": None, **c,
                           "mods": [tuple(m) for m in c["mods"]]}
    if DEFAULT_ID not in result or result[DEFAULT_ID]["unlock"] is not None:
        raise ValueError("стартовый персонаж rob обязателен и должен быть открыт с начала")
    return result


def kills(save_data, boss_id):
    return int(save_data.get("boss_kills", {}).get(boss_id, 0))


def is_unlocked(char, save_data, unlock_all=False):
    if unlock_all or char["unlock"] is None:
        return True
    return kills(save_data, char["unlock"]["boss"]) >= char["unlock"]["kills"]


def unlocked_ids(chars, save_data, unlock_all=False):
    return [cid for cid, c in chars.items() if is_unlocked(c, save_data, unlock_all)]


def progress(char, save_data):
    """(сколько побед, сколько нужно) — для экрана выбора. Для открытого с начала персонажа (0, 0)."""
    if char["unlock"] is None:
        return 0, 0
    return kills(save_data, char["unlock"]["boss"]), char["unlock"]["kills"]


def record_boss_kill(save_data, chars, boss_id):
    """Записывает победу над боссом. Возвращает id персонажей, открытых именно этой победой."""
    counts = save_data.setdefault("boss_kills", {})
    counts[boss_id] = int(counts.get(boss_id, 0)) + 1
    return [cid for cid, c in chars.items()
            if c["unlock"] and c["unlock"]["boss"] == boss_id and counts[boss_id] == c["unlock"]["kills"]]
