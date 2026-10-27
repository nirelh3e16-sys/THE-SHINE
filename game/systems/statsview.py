"""Строки для меню статистики персонажа (F4 + 2). Без pygame — легко тестируется."""
from .items import BASE_STATS

SPEED_LABELS = {"damage": "урон", "fire_delay": "задержка выстрела", "shot_speed": "скорость снарядов",
                "range": "дальность", "luck": "удача", "max_hp": "макс. здоровье", "speed": "скорость"}


def build_stat_rows(player, rooms_cleared=0):
    """Список (подпись, значение). player — объект с stats, hp, max_hp, RADIUS, char, temp_buffs, inv, coins."""
    st = player.stats
    per_sec = 1.0 / st["fire_delay"]
    rows = [
        ("Персонаж", player.char.get("name", player.char["id"])),
        ("Здоровье", f"{player.hp / 2:g} / {player.max_hp / 2:g} сердец  ({player.hp}/{player.max_hp})"),
        ("Урон за выстрел", f"{st['damage']:.1f}"),
        ("Скорострельность", f"{per_sec:.2f} выстр./с"),
        ("Урон в секунду (оценка)", f"{st['damage'] * per_sec:.1f}"),
        ("Скорость снарядов", f"{st['shot_speed']:.0f}"),
        ("Дальность", f"{st['shot_speed'] * st['range']:.0f} px"),
        ("Скорость движения", f"{st['speed']:.0f}  ({st['speed'] / BASE_STATS['speed'] * 100:.0f}%)"),
        ("Удача", f"{st['luck']:g}"),
        ("Размер (хитбокс)", f"{player.RADIUS:g}"),
    ]
    traits = []
    if "ghost" in player.char.get("traits", []):
        traits.append("проходит сквозь блоки")
    if "gravity_immune" in player.char.get("traits", []):
        traits.append("гравитация не действует")
    if traits:
        rows.append(("Особенности", ", ".join(traits)))
    rows += [("Предметов", str(len(player.inv.items))), ("Монет", str(player.coins)), ("Комнат пройдено", str(rooms_cleared))]
    for stat, op, value, left in player.temp_buffs:
        shown = f"x{value:g}" if op == "mul" else f"{value:+g}"
        rows.append((f"Временно: {SPEED_LABELS.get(stat, stat)}", f"{shown}  ({left:.0f} с)"))
    return rows
