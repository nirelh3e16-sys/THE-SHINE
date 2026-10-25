"""Обычные враги: поведение задаётся данными из enemies.json."""
import json
import math
import random

import pygame

from ..settings import DATA_DIR, ROOM_X, ROOM_Y, ROOM_W, ROOM_H

BEHAVIORS = ("chase", "shoot", "dive", "spin", "burst", "blink")


def load_enemy_defs(path=None):
    path = path or DATA_DIR / "enemies.json"
    with open(path, "r", encoding="utf-8") as f:
        defs = json.load(f)
    for kind, d in defs.items():
        for key in ("name", "hp", "speed", "radius", "contact", "behavior", "sprite"):
            if key not in d:
                raise ValueError(f"враг {kind}: нет поля {key}")
        if d["behavior"] not in BEHAVIORS:
            raise ValueError(f"враг {kind}: неизвестное поведение {d['behavior']}")
    return defs


class Enemy:
    SPAWN_TIME = 0.6

    def __init__(self, kind, pos, data, hp_scale=1.0):
        self.kind = kind
        self.data = data
        self.name = data["name"]
        self.pos = pygame.Vector2(pos)
        self.max_hp = data["hp"] * hp_scale
        self.hp = self.max_hp
        self.radius = data["radius"]
        self.speed = data["speed"]
        self.contact = data["contact"]
        self.sprite = data["sprite"]
        self.coin_chance = data.get("coin", 0.3)
        self.spawn_t = self.SPAWN_TIME
        self.hurt_t = 0.0
        self.knock = pygame.Vector2()
        self.poison_t = 0.0
        self.dead = False
        self.state = "idle"
        self.timer = random.uniform(0.5, 1.5)
        self.dir = pygame.Vector2(1, 0)
        self.flip = False
        self.strafe = random.choice((-1, 1))
        self.angle = random.uniform(0, math.tau)

    @property
    def harmful(self):
        return self.spawn_t <= 0 and not self.dead

    def take_damage(self, dmg, direction=None, knockback=0.0):
        if self.spawn_t > 0 or self.dead:
            return False
        self.hp -= dmg
        self.hurt_t = 0.12
        if direction is not None and direction.length_squared() > 0:
            self.knock += direction.normalize() * knockback
        if self.hp <= 0:
            self.dead = True
        return True

    def _common(self, dt, room):
        self.hurt_t = max(0.0, self.hurt_t - dt)
        if self.poison_t > 0:
            self.poison_t -= dt
            self.hp -= 1.0 * dt
            if self.hp <= 0:
                self.dead = True
        if self.knock.length_squared() > 1:
            self.pos += self.knock * dt
            self.knock *= max(0.0, 1 - 8 * dt)

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        to_player = player.pos - self.pos
        dist = to_player.length()
        direction = to_player / dist if dist > 0 else pygame.Vector2(1, 0)
        self.flip = direction.x < 0
        beh = self.data["behavior"]
        if beh == "chase":
            self.pos += direction * self.speed * dt
        elif beh == "spin":  # вращающаяся струя: читается заранее, не требует предупреждения
            self.timer -= dt
            if self.timer <= 0:
                self.angle += 0.55
                for k in (0.0, math.pi):
                    shoot(self.pos, pygame.Vector2(math.cos(self.angle + k), math.sin(self.angle + k)),
                          self.data.get("proj_speed", 85), 1, radius=3, color=(110, 190, 255))
                self.timer = self.data.get("fire", 0.38)
        elif beh == "shoot":
            if self.speed > 0:  # стрелок ходит боком относительно игрока
                self.pos += pygame.Vector2(-direction.y, direction.x) * self.strafe * self.speed * dt
            self.timer -= dt
            if self.timer <= 0:
                self.strafe = -self.strafe
                n = self.data.get("spread", 3)
                base = math.atan2(direction.y, direction.x)
                for i in range(n):
                    a = base + (i - (n - 1) / 2) * self.data.get("spread_step", 0.35)
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)),
                          self.data.get("proj_speed", 90), 1)
                self.timer = self.data.get("fire", 2.0)
        elif beh == "dive":
            self._dive(dt, room, direction, shoot)
        elif beh == "burst":
            self._burst(dt, dist, direction, shoot)
        elif beh == "blink":
            self._blink(dt, room, player, direction, shoot)
        room.confine(self.pos, self.radius)

    def _blink(self, dt, room, player, direction, shoot):
        """Глитч исчезает и появляется рядом с игроком: точка появления помечена заранее."""
        self.timer -= dt
        if self.state == "idle":
            if self.timer <= 0:
                target = None
                for _ in range(25):
                    a = random.uniform(0, math.tau)
                    p = player.pos + pygame.Vector2(math.cos(a), math.sin(a)) * random.uniform(85, 130)
                    inside = ROOM_X + 16 < p.x < ROOM_X + ROOM_W - 16 and ROOM_Y + 16 < p.y < ROOM_Y + ROOM_H - 16
                    if inside and not any(o.inflate(20, 20).collidepoint(p) for o in room.obstacles):
                        target = p
                        break
                if target is None:
                    self.timer = 0.5
                    return
                self.target = target
                self.state, self.timer = "windup", 0.7
        elif self.state == "windup" and self.timer <= 0:
            self.pos = self.target
            aim = player.pos - self.pos
            base = math.atan2(aim.y, aim.x) if aim.length_squared() else 0.0
            for i in (-1, 0, 1):
                a = base + i * 0.25
                shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), self.data.get("proj_speed", 120), 1,
                      radius=3, color=(80, 255, 220))
            self.state, self.timer = "idle", random.uniform(1.6, 2.4)

    def _burst(self, dt, dist, direction, shoot):
        """Дрон держит дистанцию, затем после предупреждения даёт очередь из 3 выстрелов."""
        self.timer -= dt
        if self.state == "idle":
            perp = pygame.Vector2(-direction.y, direction.x)
            radial = 0.4 if dist > 170 else (-0.4 if dist < 100 else 0.0)
            self.pos += (perp * self.strafe * 0.8 + direction * radial) * self.speed * dt
            if self.timer <= 0:
                self.state, self.timer = "windup", 0.55
        elif self.state == "windup":
            self.dir = direction.copy()
            if self.timer <= 0:
                self.state, self.timer, self.shots_left = "fire", 0.0, 3
        elif self.state == "fire" and self.timer <= 0:
            shoot(self.pos, direction, self.data.get("proj_speed", 130), 1, radius=3, color=(255, 90, 90))
            self.shots_left -= 1
            self.timer = 0.14
            if self.shots_left <= 0:
                self.state, self.timer = "idle", random.uniform(1.4, 2.2)
                self.strafe = -self.strafe

    def _dive(self, dt, room, direction, shoot):
        self.timer -= dt
        if self.state == "idle":  # кружит рядом
            perp = pygame.Vector2(-direction.y, direction.x)
            self.pos += (perp * 0.8 + direction * 0.2) * self.speed * dt
            if self.timer <= 0:
                self.state, self.timer = "windup", 0.65
                self.dir = direction.copy()
        elif self.state == "windup":
            if self.timer > 0.25:
                self.dir = direction.copy()
            if self.timer <= 0:
                self.state, self.timer = "dash", 0.55
        elif self.state == "dash":
            self.pos += self.dir * self.data.get("dive_speed", 200) * dt
            if self.timer <= 0 or room.confine(self.pos, self.radius):
                self.state, self.timer = "rest", 0.8
        elif self.state == "rest" and self.timer <= 0:
            self.state, self.timer = "idle", random.uniform(1.0, 2.0)

    @property
    def warning(self):
        if self.data["behavior"] in ("dive", "burst", "blink"):
            return self.state == "windup"
        if self.data["behavior"] == "shoot":
            return self.timer < 0.4
        return False

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            r = int(2 + 10 * (1 - self.spawn_t / self.SPAWN_TIME))
            pygame.draw.circle(surf, (255, 255, 255), (int(self.pos.x + off.x), int(self.pos.y + off.y)), r, 1)
            return
        if self.data["behavior"] == "blink" and self.state == "windup" and hasattr(self, "target"):
            if int(pygame.time.get_ticks() / 70) % 2:
                pygame.draw.circle(surf, (80, 255, 220), (int(self.target.x + off.x), int(self.target.y + off.y)), 9, 1)
        img = sprites.white(self.sprite) if self.hurt_t > 0 else sprites.get(self.sprite, self.flip)
        bob = int(math.sin(pygame.time.get_ticks() / 120 + self.pos.x) * 1.5) if self.speed > 0 else 0
        rect = img.get_rect(center=(int(self.pos.x + off.x), int(self.pos.y + off.y) + bob))
        surf.blit(img, rect)
        if self.warning and int(pygame.time.get_ticks() / 70) % 2:
            pygame.draw.circle(surf, (255, 60, 60), rect.center, self.radius + 4, 1)
            if self.state == "windup" and self.data["behavior"] in ("dive", "burst"):
                end = self.pos + self.dir * 60
                pygame.draw.line(surf, (255, 80, 80), (self.pos.x + off.x, self.pos.y + off.y),
                                 (end.x + off.x, end.y + off.y), 1)
