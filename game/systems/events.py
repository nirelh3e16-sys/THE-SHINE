"""События с выбором: загрузка данных и применение эффектов."""
import json
from pathlib import Path

from ..settings import DATA_DIR
from .morality import TESTIMONIES
from ..save_system import SINS

EFFECT_TYPES = ("hp", "max_hp", "coins", "run_mod", "sin", "testimony", "notify", "item", "spawn")


def _check_effect(effect, event_id):
    etype = effect.get("type")
    if etype not in EFFECT_TYPES:
        raise ValueError(f"событие {event_id}: неизвестный эффект {etype}")
    if etype == "sin" and effect.get("name") not in SINS:
        raise ValueError(f"событие {event_id}: неизвестный грех {effect.get('name')}")
    if etype == "testimony" and effect.get("id") not in TESTIMONIES:
        raise ValueError(f"событие {event_id}: неизвестное свидетельство {effect.get('id')}")
    if etype == "spawn" and not (isinstance(effect.get("kind"), str) and effect.get("count", 0) > 0):
        raise ValueError(f"событие {event_id}: неверный эффект spawn")
    if etype == "run_mod" and effect.get("op") not in ("add", "mul"):
        raise ValueError(f"событие {event_id}: неверная операция run_mod")


def load_events(path=None):
    path = Path(path) if path else DATA_DIR / "events.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    events = {}
    for ev in raw.get("events", []):
        for key in ("id", "kind", "name", "text"):
            if key not in ev:
                raise ValueError(f"событие без поля '{key}'")
        if ev["kind"] not in ("npc", "altar", "apparition"):
            raise ValueError(f"событие {ev['id']}: неизвестный kind")
        for choice in ev.get("choices", []):
            for effect in choice.get("effects", []):
                _check_effect(effect, ev["id"])
        for effect in ev.get("effects", []):
            _check_effect(effect, ev["id"])
        events[ev["id"]] = ev
    return events


def apply_effects(effects, ctx):
    """ctx должен предоставлять: change_hp, change_max_hp, add_coins, add_run_mod, morality, notify."""
    for e in effects:
        t = e["type"]
        if t == "hp":
            ctx.change_hp(e["value"])
        elif t == "max_hp":
            ctx.change_max_hp(e["value"])
        elif t == "coins":
            ctx.add_coins(e["value"])
        elif t == "run_mod":
            ctx.add_run_mod(e["stat"], e["op"], e["value"])
        elif t == "sin":
            ctx.morality.add_sin(e["name"], e["value"])
        elif t == "testimony":
            if ctx.morality.add_testimony(e["id"]):
                ctx.notify("Новое свидетельство: " + TESTIMONIES[e["id"]][0], "gold")
        elif t == "notify":
            ctx.notify(e["text"], e.get("color", "white"))
        elif t == "item":
            ctx.give_random_item()
        elif t == "spawn":
            ctx.spawn(e["kind"], e["count"])


def can_choose(choice, coins):
    """Проверка условий варианта выбора (сейчас — только цена в монетах)."""
    return coins >= choice.get("requires", {}).get("coins", 0)
