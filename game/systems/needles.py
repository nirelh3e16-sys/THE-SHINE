"""Иголки и колючки, застрявшие в цели (игроке или мобе).

Каждая иголка держится STICK_TIME секунд. Пока в цели есть хотя бы одна иголка, каждое
движение (каждые STEP пикселей пути) наносит урон. Модуль без pygame — легко тестируется.
"""
import math

STICK_TIME = 3.0   # сколько секунд иголка торчит в цели
STEP = 24.0        # сколько пикселей нужно пройти, чтобы иголки «кольнули» один раз
MAX_STUCK = 8      # больше иголок в одной цели не помещается (новая заменяет самую старую)


class Needles:
    def __init__(self, stick_time=STICK_TIME, step=STEP, limit=MAX_STUCK):
        self.stick_time, self.step, self.limit = stick_time, step, limit
        self.timers = []       # оставшееся время каждой иголки
        self._last = None      # где цель была в прошлый раз
        self._walked = 0.0     # накопленный путь с прошлого укола

    @property
    def count(self):
        return len(self.timers)

    def __bool__(self):
        return bool(self.timers)

    def add(self, n=1):
        for _ in range(n):
            if len(self.timers) >= self.limit:
                self.timers.pop(0)   # самая старая выпала
            self.timers.append(self.stick_time)

    def clear(self):
        self.timers.clear()
        self._last, self._walked = None, 0.0

    def update(self, dt, x, y):
        """Двигает таймеры. Возвращает число уколов за этот кадр (0, если цель стоит на месте)."""
        self.timers = [t - dt for t in self.timers if t - dt > 0]
        if not self.timers:
            self._last, self._walked = None, 0.0
            return 0
        if self._last is None:
            self._last = (x, y)
            return 0
        self._walked += math.hypot(x - self._last[0], y - self._last[1])
        self._last = (x, y)
        steps = int(self._walked // self.step)
        if steps:
            self._walked -= steps * self.step
        return steps

    def stab_damage(self):
        """Урон одного укола по игроку: 1 (полсердца), а если иголок три и больше — 2."""
        return 1 + (1 if self.count >= 3 else 0)
