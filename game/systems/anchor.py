"""Якорь: пока удерживается атака — вертится вокруг игрока, при отпускании летит к курсору и возвращается.

Чистая математика на кортежах (без pygame), чтобы логику можно было тестировать.
"""
import math

BLOCK = 16.0
MIN_REACH = 40.0
MAX_REACH = 10 * BLOCK        # максимум 10 блоков
FULL_CHARGE = 1.5             # секунд удержания до максимальной дальности
ORBIT_RADIUS = 28.0
ORBIT_SPEED = 6.0             # рад/с
FLY_SPEED = 430.0
RETURN_SPEED = 360.0
RECOVER = 0.35                # пауза после возвращения


def reach_for_hold(hold):
    """Дальность полёта: чем дольше зажата атака, тем дальше (до MAX_REACH)."""
    return MIN_REACH + (MAX_REACH - MIN_REACH) * min(1.0, max(0.0, hold) / FULL_CHARGE)


class Anchor:
    def __init__(self):
        self.state = "idle"            # idle | orbit | fly | return
        self.pos = (0.0, 0.0)
        self.angle = 0.0
        self.hold = 0.0
        self.dir = (1.0, 0.0)
        self.target_dist = 0.0
        self.traveled = 0.0
        self.cooldown = 0.0
        self.pass_id = 0               # меняется на каждом проходе (вылет/возврат) — чтобы бить цель один раз за проход

    @property
    def flying(self):
        return self.state in ("fly", "return")

    def holding(self, dt, player):
        """Атака зажата: вращение вокруг игрока."""
        if self.flying or self.cooldown > 0:
            return
        if self.state != "orbit":
            self.state, self.hold = "orbit", 0.0
        self.hold += dt
        self.angle += ORBIT_SPEED * dt
        self.pos = (player[0] + math.cos(self.angle) * ORBIT_RADIUS, player[1] + math.sin(self.angle) * ORBIT_RADIUS)

    def release(self, aim_dir):
        """Атака отпущена: якорь летит в сторону aim_dir на дальность, зависящую от удержания."""
        if self.state != "orbit":
            return False
        length = math.hypot(*aim_dir) or 1.0
        self.dir = (aim_dir[0] / length, aim_dir[1] / length)
        self.target_dist = reach_for_hold(self.hold)
        self.traveled = 0.0
        self.state = "fly"
        self.pass_id += 1
        return True

    def step(self, dt, player):
        """Продвигает якорь. Вызывать каждый кадр."""
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.state == "fly":
            move = FLY_SPEED * dt
            self.pos = (self.pos[0] + self.dir[0] * move, self.pos[1] + self.dir[1] * move)
            self.traveled += move
            if self.traveled >= self.target_dist:
                self.state = "return"
                self.pass_id += 1
        elif self.state == "return":
            dx, dy = player[0] - self.pos[0], player[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            move = RETURN_SPEED * dt
            if dist <= move + 6:
                self.state, self.cooldown, self.hold = "idle", RECOVER, 0.0
                self.pos = player
            else:
                self.pos = (self.pos[0] + dx / dist * move, self.pos[1] + dy / dist * move)
        elif self.state == "idle":
            self.pos = player

    def cancel_orbit(self):
        """Атака отпущена слишком рано/недоступна: якорь просто возвращается к игроку."""
        if self.state == "orbit":
            self.state, self.hold = "idle", 0.0
