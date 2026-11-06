"""Гейзер душ: луч из игрока, который следит за курсором (Балансатор и Крик персонажа «Душа»).

Чистая математика на кортежах, без pygame — логику легко тестировать.
"""
import math

BLOCK = 16.0
RANGE = 25 * BLOCK          # дальность гейзера: 25 блоков
CHARGE_TIME = 3.0           # Балансатор заряжается 3 секунды
TICK = 0.1                  # как часто гейзер наносит урон тому, кто в нём стоит

BALANCER = {"width": 14.0, "duration": 1.4, "damage_mult": 2.0, "turn_speed": 4.5, "recoil": 0.0}
# Крик: ширина в 4 раза больше, держится дольше, бьёт сильнее, медленнее поворачивается и отбрасывает игрока назад
SCREAM = {"width": BALANCER["width"] * 4, "duration": 3.0, "damage_mult": 5.0, "turn_speed": 2.2, "recoil": 120.0}


class Charge:
    """Зарядка: пока кнопка зажата — копится; отпустил до полной зарядки — всё потеряно."""

    def __init__(self, need=CHARGE_TIME):
        self.need, self.value = need, 0.0

    @property
    def ready(self):
        return self.value >= self.need

    @property
    def fraction(self):
        return min(1.0, self.value / self.need)

    def hold(self, dt):
        self.value = min(self.need, self.value + dt)

    def release(self):
        """Кнопку отпустили. True, если заряд был полным (можно стрелять)."""
        fired = self.ready
        self.value = 0.0
        return fired

    def cancel(self):
        self.value = 0.0


class Geyser:
    def __init__(self, width, duration, damage_mult, turn_speed, recoil=0.0, reach=RANGE):
        self.width, self.duration, self.damage_mult = width, duration, damage_mult
        self.turn_speed, self.recoil, self.reach = turn_speed, recoil, reach
        self.left = 0.0
        self.origin = (0.0, 0.0)
        self.angle = 0.0
        self._tick = 0.0

    @classmethod
    def balancer(cls):
        return cls(**BALANCER)

    @classmethod
    def scream(cls):
        return cls(**SCREAM)

    @property
    def active(self):
        return self.left > 0

    @property
    def direction(self):
        return math.cos(self.angle), math.sin(self.angle)

    def start(self, origin, direction):
        self.origin = tuple(origin)
        self.angle = math.atan2(direction[1], direction[0])
        self.left, self._tick = self.duration, 0.0

    def stop(self):
        self.left = 0.0

    def update(self, dt, origin, aim):
        """Двигает гейзер: крепится к игроку, плавно поворачивается к курсору. Возвращает число тиков урона за кадр."""
        if not self.active:
            return 0
        self.origin = tuple(origin)
        if aim[0] or aim[1]:
            diff = (math.atan2(aim[1], aim[0]) - self.angle + math.pi) % math.tau - math.pi
            limit = self.turn_speed * dt
            self.angle += max(-limit, min(limit, diff))
        self.left = max(0.0, self.left - dt)
        self._tick -= dt
        ticks = 0
        while self._tick <= 0:
            self._tick += TICK
            ticks += 1
        return ticks

    def end(self):
        d = self.direction
        return self.origin[0] + d[0] * self.reach, self.origin[1] + d[1] * self.reach

    def distance_to(self, point):
        """Расстояние от точки до оси гейзера (отрезок от игрока до конца)."""
        (x0, y0), (x1, y1) = self.origin, self.end()
        dx, dy = x1 - x0, y1 - y0
        length_sq = dx * dx + dy * dy
        t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((point[0] - x0) * dx + (point[1] - y0) * dy) / length_sq))
        return math.hypot(point[0] - (x0 + dx * t), point[1] - (y0 + dy * t))

    def hits(self, point, radius=0.0):
        return self.active and self.distance_to(point) <= self.width / 2 + radius

    def recoil_vector(self):
        """Куда толкает игрока отдача (против направления гейзера); пока гейзер активен."""
        if not self.active or not self.recoil:
            return (0.0, 0.0)
        d = self.direction
        return -d[0] * self.recoil, -d[1] * self.recoil
