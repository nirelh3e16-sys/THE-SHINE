"""Адаптивное качество эффектов («шейдеров»): если игра долго идёт медленнее ~45 кадров/с, дорогие эффекты
по одному отключаются, а когда кадр снова быстрый — возвращаются. Без pygame.

Уровни: 2 — всё; 1 — без лучей солнца и бликов линзы; 0 — ещё и тени без «проекции», меньше источников света.
"""

HIGH, MEDIUM, LOW = 2, 1, 0
SLOW_FRAME = 1 / 45        # средний кадр дольше этого — игра «тормозит»
FAST_FRAME = 1 / 57        # средний кадр короче этого — запас по скорости есть
SLOW_AFTER = 1.5           # сколько секунд подряд тормозить, чтобы понизить качество
FAST_AFTER = 8.0           # сколько секунд подряд работать быстро, чтобы вернуть качество
SMOOTHING = 0.1            # сглаживание: одиночный скачок (загрузка комнаты) качество не трогает


class AdaptiveQuality:
    def __init__(self, target_fps=60):
        self.level = HIGH
        self.avg = 1.0 / max(1, target_fps)
        self._slow = 0.0
        self._fast = 0.0

    def update(self, frame_time):
        """frame_time — настоящая длительность кадра в секундах (без ограничения MAX_DT)."""
        if frame_time <= 0:
            return self.level
        self.avg += (frame_time - self.avg) * SMOOTHING
        if self.avg > SLOW_FRAME:
            self._slow += frame_time
            self._fast = 0.0
            if self._slow >= SLOW_AFTER and self.level > LOW:
                self.level -= 1
                self._slow = 0.0
        elif self.avg < FAST_FRAME:
            self._fast += frame_time
            self._slow = 0.0
            if self._fast >= FAST_AFTER and self.level < HIGH:
                self.level += 1
                self._fast = 0.0
        else:
            self._slow = self._fast = 0.0
        return self.level

    def effective(self, mode):
        """Какой уровень использовать при настройке mode: auto — адаптивный, high/low — зафиксирован."""
        if mode == "high":
            return HIGH
        if mode == "low":
            return LOW
        return self.level
