"""Настройки «шейдеров» (теней, света, смены дня и ночи). Без pygame."""

DEFAULTS = {
    "shaders": True,          # главный выключатель всех эффектов
    "shadows": True,          # тени от мобов, игрока, NPC и боссов
    "shadow_strength": 1,     # 0 слабая, 1 средняя, 2 сильная
    "sun_glare": True,        # блики и лучи солнца
    "lights": True,           # свет от игрока, боссов и источников
    "time_mode": "auto",      # auto | dawn | day | sunset | night
    "night_brightness": 1,    # 0 тёмная, 1 средняя, 2 светлая
}
TIME_MODES = ("auto", "dawn", "day", "sunset", "night")
TIME_LABELS = {"auto": "смена по времени", "dawn": "всегда рассвет", "day": "всегда день",
               "sunset": "всегда закат", "night": "всегда ночь"}
STRENGTH_LABELS = ("слабая", "средняя", "сильная")
BRIGHTNESS_LABELS = ("тёмная", "средняя", "светлая")
SHADOW_ALPHA = (0.55, 0.8, 1.05)     # множитель непрозрачности теней
NIGHT_MULT = (1.0, 0.8, 0.6)         # множитель затемнения по настройке яркости ночи


def sanitize(raw):
    """Приводит сохранённые значения к допустимым; неизвестное заменяется значениями по умолчанию."""
    cfg = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key in ("shaders", "shadows", "sun_glare", "lights"):
        if isinstance(raw.get(key), bool):
            cfg[key] = raw[key]
    for key in ("shadow_strength", "night_brightness"):
        if isinstance(raw.get(key), int) and not isinstance(raw.get(key), bool) and 0 <= raw[key] <= 2:
            cfg[key] = raw[key]
    if raw.get("time_mode") in TIME_MODES:
        cfg["time_mode"] = raw["time_mode"]
    return cfg


def cycle(cfg, key):
    """Переключает параметр на следующее значение."""
    if key == "time_mode":
        cfg[key] = TIME_MODES[(TIME_MODES.index(cfg[key]) + 1) % len(TIME_MODES)]
    elif key in ("shadow_strength", "night_brightness"):
        cfg[key] = (cfg[key] + 1) % 3
    else:
        cfg[key] = not cfg[key]
    return cfg[key]
