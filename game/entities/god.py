"""Бог — финальный босс игры (Небеса).

Существо с радиальной симметрией: у него нет тела, головы и рук — только единственный глаз и
ряды крыльев вокруг него. Бой идёт, когда в игрока уже вселился раненый Шайн: у игрока 1000 здоровья
и 100 урона за выстрел, у Бога 10 000 здоровья и 250 урона за любое попадание. Все атаки заранее
предупреждаются; у боя три фазы (66% и 33% здоровья).
"""
import math
import random

import pygame

from .enemy import Enemy
from .hazard import Hazard
from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H

GOD_DAMAGE = 250
GOD = {"name": "Бог", "hp": 10000, "speed": 0, "radius": 26, "contact": GOD_DAMAGE,
       "behavior": "chase", "sprite": "god", "coin": 0}
GOD_CD = {"rings": (4, 7), "spiral": (6, 9), "gaze": (5, 8), "pillars": (5, 8),
          "gap_ring": (6, 9), "cross": (8, 12), "nova": (11, 15)}
PHASE_ATTACKS = {1: ("rings", "spiral", "gaze", "pillars"),
                 2: ("rings", "spiral", "gaze", "pillars", "gap_ring", "cross"),
                 3: ("rings", "spiral", "gaze", "pillars", "gap_ring", "cross", "nova")}
IRIS = {1: (255, 214, 90), 2: (150, 200, 255), 3: (255, 255, 255)}
GOLD_SHOT = (255, 226, 130)
WHITE_SHOT = (240, 248, 255)
_WING_FRAMES = {}   # кэш повёрнутых слоёв крыльев (узор повторяется каждые 15 градусов)


def _vec(angle):
    return pygame.Vector2(math.cos(angle), math.sin(angle))


class God(Enemy):
    SPAWN_TIME = 3.0

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("god", pos, GOD, 1.0)
        self.is_boss = True
        self.phase = 1
        self.state, self.timer = "idle", 2.0
        self.cd = {k: 0.0 for k in GOD_CD}
        self.last = None
        self.delayed = []              # отложенные события: [секунды, функция]
        self.aim = pygame.Vector2(1, 0)
        self.spin = self.spin_tick = 0.0
        self.wing_angle = 0.0
        self.pupil = pygame.Vector2()
        self.home = pygame.Vector2(pos)
        self.shots_left = 0
        self.gaze_len = 0

    def take_damage(self, dmg, direction=None, knockback=0.0):
        return super().take_damage(dmg, direction, 0.0)   # Бога не отбросить

    def _phase_for_hp(self):
        ratio = self.hp / self.max_hp
        return 3 if ratio <= 0.33 else 2 if ratio <= 0.66 else 1

    def _enemy_shot(self, shoot, origin, angle, speed, color=GOLD_SHOT, radius=3):
        shoot(origin, _vec(angle), speed, GOD_DAMAGE, radius=radius, color=color)

    # --- цикл ---
    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        self.knock.update(0, 0)
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt)
        for ev in self.delayed:
            ev[0] -= dt
        due = [ev for ev in self.delayed if ev[0] <= 0]
        self.delayed = [ev for ev in self.delayed if ev[0] > 0]
        for ev in due:
            ev[1]()
        self.wing_angle = (self.wing_angle + dt * (10 + 7 * self.phase)) % 360
        new_phase = self._phase_for_hp()
        if new_phase > self.phase:
            self.phase = new_phase
            self.state, self.timer = "roar", 1.6
            room.shake_request = (6, 0.7)
            room.notices.append(("БОГ: «Ты не должен существовать.»" if new_phase == 2
                                 else "БОГ: «Растворись. Стань ничем.»", "gold"))
        # парит у центра верхней части комнаты
        t = pygame.time.get_ticks() / 1000
        self.pos = self.home + pygame.Vector2(math.sin(t * 0.7) * 10, math.cos(t * 0.9) * 6)
        to = player.pos - self.pos
        d = to.normalize() if to.length_squared() > 0 else pygame.Vector2(1, 0)
        self.pupil, self.flip = d, False
        self.timer -= dt
        st = self.state
        if st == "roar":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.7
        elif st == "idle":
            if self.timer <= 0:
                self._choose(room, player)
        elif st == "wind_rings":
            if self.timer <= 0:
                self._rings(shoot)
                self._finish(1.6)
        elif st == "wind_spiral":
            if self.timer <= 0:
                self.state, self.timer, self.spin_tick = "spiral", 3.0, 0.0
        elif st == "spiral":
            self.spin_tick -= dt
            if self.spin_tick <= 0:
                arms = 3 + self.phase       # 4, 5, 6 лучей
                self.spin += 0.31
                for i in range(arms):
                    self._enemy_shot(shoot, self.pos, self.spin + i * math.tau / arms, 92)
                self.spin_tick = 0.13
            if self.timer <= 0:
                self._finish(1.4)
        elif st == "wind_gaze":
            if self.timer > 0.3:
                self.aim = d.copy()   # прицел фиксируется за 0.3 с до выстрела
            if self.timer <= 0:
                self.state, self.timer, self.shots_left = "gaze", 0.0, 6 + 2 * self.phase
        elif st == "gaze":
            if self.timer <= 0:
                spread = random.uniform(-0.05, 0.05) * (self.phase - 1)
                self._enemy_shot(shoot, self.pos + self.aim * 24, math.atan2(self.aim.y, self.aim.x) + spread, 235,
                                 WHITE_SHOT, 2)
                self.shots_left -= 1
                self.timer = 0.09
                if self.shots_left <= 0:
                    self._finish(1.5)
        elif st == "wind_pillars":
            if self.timer <= 0:
                self._finish(1.5)
        elif st == "wind_gap":
            if self.timer <= 0:
                self._gap_ring(shoot)
                self._finish(1.7)
        elif st == "wind_cross":
            if self.timer <= 0:
                self._finish(1.8)
        elif st == "wind_nova":
            if self.timer <= 0:
                for i in range(3):   # три плотных кольца подряд, щели каждый раз смещены
                    self.delayed.append([i * 0.5, lambda i=i: self._nova_ring(shoot, i)])
                self._finish(3.0)

    def _finish(self, rest):
        self.state, self.timer = "idle", rest

    # --- выбор атаки ---
    def _choose(self, room, player):
        options = [a for a in PHASE_ATTACKS[self.phase] if self.cd[a] <= 0 and a != self.last]
        if not options:
            options = [a for a in PHASE_ATTACKS[self.phase] if a != self.last]
        name = random.choice(options)
        self.last = name
        self.cd[name] = random.uniform(*GOD_CD[name])
        getattr(self, "_atk_" + name)(room, player)

    def _atk_rings(self, room, player):
        self.state, self.timer = "wind_rings", 0.9

    def _atk_spiral(self, room, player):
        self.state, self.timer = "wind_spiral", 0.9

    def _atk_gaze(self, room, player):
        self.state, self.timer = "wind_gaze", 1.1
        to = player.pos - self.pos
        self.aim = to.normalize() if to.length_squared() else self.aim

    def _atk_pillars(self, room, player):
        self.state, self.timer = "wind_pillars", 1.25
        extra = 1 + 2 * self.phase       # 3, 5, 7 колонн света; первая — прямо под игроком
        spots = [player.pos.copy()] + [player.pos + pygame.Vector2(random.uniform(-110, 110), random.uniform(-80, 80))
                                       for _ in range(extra)]
        size = 40
        for p in spots:
            x = int(max(ROOM_X, min(ROOM_X + ROOM_W - size, p.x - size / 2)))
            y = int(max(ROOM_Y, min(ROOM_Y + ROOM_H - size, p.y - size / 2)))
            room.hazards.append(Hazard((x, y, size, size), GOD_DAMAGE, 1.1, 0.35, kind="drop"))

    def _atk_gap_ring(self, room, player):
        self.state, self.timer = "wind_gap", 1.0
        to = player.pos - self.pos
        self.aim = to.normalize() if to.length_squared() else self.aim

    def _atk_cross(self, room, player):
        self.state, self.timer = "wind_cross", 1.5
        c = self.pos
        bars = [pygame.Rect(ROOM_X, int(c.y) - 14, ROOM_W, 28), pygame.Rect(int(c.x) - 14, ROOM_Y, 28, ROOM_H)]
        if self.phase == 3:   # в третьей фазе добавляются полосы, нацеленные на игрока
            bars.append(pygame.Rect(ROOM_X, int(player.pos.y) - 12, ROOM_W, 24))
            bars.append(pygame.Rect(int(player.pos.x) - 12, ROOM_Y, 24, ROOM_H))
        for r in bars:
            room.hazards.append(Hazard(r, GOD_DAMAGE, 1.3, 0.4, kind="drop"))

    def _atk_nova(self, room, player):
        self.state, self.timer = "wind_nova", 1.7

    # --- сами выстрелы ---
    def _rings(self, shoot):
        n = 18 + 2 * self.phase
        for r in range(3):
            self.delayed.append([r * 0.45, lambda r=r: [self._enemy_shot(shoot, self.pos, (r % 2) * math.pi / n + i * math.tau / n, 82)
                                                         for i in range(n)]])

    def _gap_ring(self, shoot):
        n = 36
        gap_center = math.atan2(self.aim.y, self.aim.x)
        for i in range(n):
            a = i * math.tau / n
            diff = abs((a - gap_center + math.pi) % math.tau - math.pi)
            if diff > 0.34:   # щель шириной около 40 градусов — в сторону игрока
                self._enemy_shot(shoot, self.pos, a, 78, WHITE_SHOT)

    def _nova_ring(self, shoot, index):
        n = 32
        gap = random.uniform(0, math.tau)
        for i in range(n):
            a = i * math.tau / n
            if abs((a - gap + math.pi) % math.tau - math.pi) > 0.3:
                self._enemy_shot(shoot, self.pos, a, 70 + index * 14, GOLD_SHOT, 3)

    @property
    def warning(self):
        return self.state.startswith("wind_") and self.spawn_t <= 0

    # --- отрисовка ---
    def _wings(self, sprites, hurt):
        key = (int(self.wing_angle) % 15, hurt)
        if key not in _WING_FRAMES:
            base = sprites.white("god") if hurt else sprites.get("god")
            _WING_FRAMES[key] = pygame.transform.rotate(base, key[0])
        return _WING_FRAMES[key]

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        t = pygame.time.get_ticks()
        blink = int(t / 90) % 2
        cx, cy = int(self.pos.x + off.x), int(self.pos.y + off.y)
        img = self._wings(sprites, self.hurt_t > 0 or (self.state == "roar" and blink))
        surf.blit(img, img.get_rect(center=(cx, cy)))
        # единственный глаз: радужка и зрачок следят за игроком; в «нове» глаз закрывается
        closed = self.state == "wind_nova"
        if closed:
            pygame.draw.line(surf, (232, 190, 90), (cx - 16, cy), (cx + 16, cy), 3)
        else:
            from ..sprites import draw_iris
            draw_iris(surf, cx, cy, int(self.pupil.x * 4), int(self.pupil.y * 4), IRIS[self.phase])
        if self.state == "wind_gaze" and blink:    # линия взгляда: куда прилетит очередь
            end = self.pos + self.aim * 320
            pygame.draw.line(surf, (255, 60, 60), (cx, cy), (end.x + off.x, end.y + off.y), 2)
        if self.state == "wind_gap" and blink:     # куда будет щель в кольце
            end = self.pos + self.aim * 90
            pygame.draw.line(surf, (120, 255, 160), (cx, cy), (end.x + off.x, end.y + off.y), 2)
        if self.warning and blink:
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 36, 1)
