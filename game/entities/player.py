"""Игрок: движение, уклонение, здоровье, характеристики."""
import math

import pygame

from ..collision import push_out_of_rect
from ..systems.inventory import Inventory


class Player:
    RADIUS = 5
    IFRAMES = 1.0
    ACCEL = 9.0       # разгон до полной скорости ≈ 0.11 с (небольшая инерция)
    DECEL = 6.5       # остановка ≈ 0.15 с
    DODGE_TIME = 0.22
    DODGE_COOLDOWN = 0.9

    def __init__(self, db, char=None):
        self.db = db
        # персонаж: модификаторы характеристик, размер и особенности (проход сквозь блоки, иммунитет к гравитации)
        self.char = char or {"id": "rob", "mods": [], "scale": 1.0, "traits": []}
        self.char_id = self.char["id"]
        self.char_mods = [tuple(m) for m in self.char["mods"]]
        self.RADIUS = 5 * self.char.get("scale", 1.0)   # у крупного Тома хитбокс больше
        self.ghost = "ghost" in self.char.get("traits", [])
        self.gravity_immune = "gravity_immune" in self.char.get("traits", [])
        self.inv = Inventory()
        self.pos = pygame.Vector2(240, 136)
        self.vel = pygame.Vector2()
        self.cur_vel = pygame.Vector2()   # фактическая скорость с инерцией
        self.coins = 0
        self.run_mods = []        # (stat, op, value) — постоянные модификаторы забега
        self.temp_buffs = []      # [stat, op, value, time_left]
        self.stats = db.stats([])
        self.max_hp = int(self.stats["max_hp"])
        self.hp = self.max_hp
        self.iframes = 0.0
        self.dodge_t = 0.0
        self.dodge_cd = 0.0
        self.dodge_dir = pygame.Vector2(1, 0)
        self.shoot_cd = 0.0
        self.knock = pygame.Vector2()
        self.aim = pygame.Vector2(1, 0)
        self.moving = False
        self.flags = set()
        self.god = False            # тест-меню: неуязвимость
        self.debug_damage = None    # тест-меню: принудительные значения
        self.debug_max_hp = None
        self.recompute()               # применить модификаторы персонажа
        self.hp = self.max_hp

    def recompute(self):
        extra = list(self.char_mods) + list(self.run_mods) + [(s, o, v) for s, o, v, _ in self.temp_buffs]
        old_max = self.max_hp
        self.stats = self.db.stats(self.inv.items, extra)
        if self.debug_damage is not None:
            self.stats["damage"] = float(self.debug_damage)
        if self.debug_max_hp is not None:
            self.stats["max_hp"] = float(self.debug_max_hp)
        self.flags = self.db.flags(self.inv.items)
        self.max_hp = int(round(self.stats["max_hp"]))
        if self.max_hp > old_max:
            self.hp += self.max_hp - old_max
        self.hp = max(1, min(self.hp, self.max_hp)) if self.hp > 0 else 0

    @property
    def invulnerable(self):
        return self.iframes > 0 or self.dodge_t > 0

    def heal(self, amount):
        if "halo_curse" in self.flags:
            amount = max(1, amount // 2)
        self.hp = min(self.max_hp, self.hp + amount)

    def hurt(self, amount, source_pos=None):
        if self.god or self.invulnerable or self.hp <= 0:
            return False
        self.hp -= amount
        self.iframes = self.IFRAMES
        if source_pos is not None:
            d = self.pos - source_pos
            if d.length_squared() > 0:
                self.knock = d.normalize() * 160
        return True

    def tick_timers(self, dt):
        self.iframes = max(0.0, self.iframes - dt)
        self.dodge_t = max(0.0, self.dodge_t - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.inv.tick(dt)
        if self.temp_buffs:
            for b in self.temp_buffs:
                b[3] -= dt
            if any(b[3] <= 0 for b in self.temp_buffs):
                self.temp_buffs = [b for b in self.temp_buffs if b[3] > 0]
                self.recompute()

    def start_dodge(self):
        if self.dodge_cd > 0 or self.dodge_t > 0:
            return False
        self.dodge_dir = self.vel.normalize() if self.moving else self.aim.copy()
        self.dodge_t = self.DODGE_TIME
        self.dodge_cd = self.DODGE_COOLDOWN
        return True

    def update(self, dt, move_dir, room, drift=None):
        self.tick_timers(dt)
        self.moving = move_dir.length_squared() > 0
        if self.moving:
            self.vel = move_dir.normalize()  # диагональ нормализована
        speed = self.stats["speed"]
        if self.dodge_t > 0:
            delta = self.dodge_dir * 260 * dt
            self.cur_vel = self.dodge_dir * speed   # после уклонения плавно продолжаем движение
        else:
            target = self.vel * speed if self.moving else pygame.Vector2()
            self.cur_vel = self.cur_vel.move_towards(target, speed * (self.ACCEL if self.moving else self.DECEL) * dt)
            delta = self.cur_vel * dt
        if drift is not None:
            delta += drift * dt
        if self.knock.length_squared() > 1:
            delta += self.knock * dt
            self.knock *= max(0.0, 1 - 9 * dt)
        # по осям отдельно, чтобы скользить вдоль стен
        for axis in (0, 1):
            if axis == 0:
                self.pos.x += delta.x
            else:
                self.pos.y += delta.y
            if not self.ghost:   # Ангел проходит сквозь блоки
                room.push_out(self.pos, self.RADIUS)
            room.clamp_player(self.pos, self.RADIUS)

    def draw(self, surf, off, sprites):
        if self.iframes > 0 and self.dodge_t <= 0 and int(self.iframes * 20) % 2:
            return
        img = sprites.get("player_" + self.char_id, self.aim.x < 0)
        bob = int(math.sin(pygame.time.get_ticks() / 80)) if self.moving else 0
        rect = img.get_rect(midbottom=(int(self.pos.x + off.x), int(self.pos.y + off.y) + int(self.RADIUS) + 4 + bob))
        if self.dodge_t > 0:
            img = img.copy()
            img.set_alpha(130)
        surf.blit(img, rect)
