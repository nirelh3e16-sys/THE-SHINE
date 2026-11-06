"""Смена дня и ночи (чисто визуальная). Без pygame — легко тестируется.

Забег начинается на рассвете (солнце только поднимается), затем утро, пик солнца, закат, сумерки и ночь.
В закрытых локациях (дома, Ад, Врата) солнца нет — там темно, как ночью.
"""
import math
from dataclasses import dataclass

# (время суток 0..1, цвет освещения, затемнение 0..1, высота солнца -1..1)
KEYFRAMES = (
    (0.00, (255, 170, 120), 0.30, 0.06),   # рассвет
    (0.08, (255, 205, 160), 0.12, 0.30),   # раннее утро
    (0.25, (255, 255, 245), 0.00, 1.00),   # пик солнца
    (0.42, (255, 238, 205), 0.04, 0.55),   # после полудня
    (0.52, (255, 140, 90), 0.28, 0.08),    # закат
    (0.60, (150, 110, 170), 0.55, -0.10),  # сумерки
    (0.68, (55, 65, 125), 0.74, -0.80),    # ночь
    (0.90, (55, 65, 125), 0.74, -1.00),
    (0.96, (120, 100, 160), 0.50, -0.20),  # перед рассветом
    (1.00, (255, 170, 120), 0.30, 0.06),
)
NIGHT_RGB = (8, 12, 36)          # цвет затемнения ночью на улице
DEFAULT_AMBIENT = (40, 34, 58, 0.72)   # закрытая локация без своего ambient
PRESETS = {"dawn": 0.01, "day": 0.25, "sunset": 0.50, "night": 0.78}
MAX_DARKNESS = 0.9


@dataclass(frozen=True)
class DayState:
    t: float
    tint: tuple          # множитель цвета сцены (255,255,255 — без изменений)
    darkness: float      # 0..1, непрозрачность затемнения
    dark_rgb: tuple      # цвет затемнения
    elevation: float     # высота солнца, <=0 — солнца нет
    sun_dx: float        # -1 слева ... +1 справа
    outdoor: bool

    @property
    def has_sun(self):
        return self.outdoor and self.elevation > 0.0


def _lerp(a, b, k):
    return a + (b - a) * k


def _keyframe_values(t):
    t %= 1.0
    for (t0, c0, d0, e0), (t1, c1, d1, e1) in zip(KEYFRAMES, KEYFRAMES[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            tint = tuple(int(round(_lerp(a, b, k))) for a, b in zip(c0, c1))
            return tint, _lerp(d0, d1, k), _lerp(e0, e1, k)
    return KEYFRAMES[0][1], KEYFRAMES[0][2], KEYFRAMES[0][3]


def sun_dx_for(t):
    """Солнце восходит слева, заходит справа."""
    t %= 1.0
    if t <= 0.52:
        return -math.cos(math.pi * t / 0.52)
    return 1.0 if t < 0.9 else -1.0


def day_state(t):
    tint, darkness, elevation = _keyframe_values(t)
    return DayState(t % 1.0, tint, darkness, NIGHT_RGB, elevation, sun_dx_for(t), True)


def clock_to_t(clock_seconds, day_length):
    return (clock_seconds / max(1.0, day_length)) % 1.0


def effective_state(zone, clock_seconds, day_length=480.0, time_mode="auto", night_mult=1.0, lights_on=True):
    """Освещение для зоны: улица следует за временем суток, закрытые локации всегда тёмные."""
    if zone.get("outdoor"):
        t = PRESETS.get(time_mode, clock_to_t(clock_seconds, day_length))
        if zone.get("always_day"):   # Небеса: всегда день, как бы ни шли часы
            t = PRESETS["day"]
        st = day_state(t)
        darkness, rgb = st.darkness * night_mult, st.dark_rgb
        tint, elevation, sun_dx = st.tint, st.elevation, st.sun_dx
        outdoor = True
    else:
        r, g, b, dark = zone.get("ambient", DEFAULT_AMBIENT)
        t, tint, elevation, sun_dx, outdoor = 0.78, (255, 255, 255), -1.0, 0.0, False
        darkness, rgb = dark * night_mult, (r, g, b)
    if not lights_on:      # без источников света слишком тёмное играть нельзя
        darkness = min(darkness, 0.35)
    darkness = max(0.0, min(MAX_DARKNESS, darkness))
    return DayState(t, tint, darkness, rgb, elevation, sun_dx, outdoor)


def shadow_params(state):
    """(dx, dy, длина, сила 0..1) тени от солнца. Нет солнца — силы нет."""
    if not state.has_sun:
        return 0.0, 0.0, 0.0, 0.0
    length = max(0.35, min(1.7, 1.7 - 1.35 * state.elevation))   # низкое солнце — длинные тени
    strength = max(0.0, min(1.0, 0.35 + 0.65 * min(1.0, state.elevation * 3)))
    return -state.sun_dx, 0.42, length, strength
