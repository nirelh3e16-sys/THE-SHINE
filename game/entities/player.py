"""Игрок: движение, уклонение, здоровье, характеристики."""
import math
import random

import pygame

from ..collision import push_out_of_rect
from ..systems.inventory import Inventory
from ..systems.needles import Needles


class Player:
    RADIUS = 5
    IFRAMES = 1.0
    ACCEL = 9.0       # разгон до полной скорости ≈ 0.11 с (небольшая инерция)
    DECEL = 6.5       # остановка ≈ 0.15 с
    DODGE_TIME = 0.22
    DODGE_COOLDOWN = 0.9
    ARMOR_BLOCK_CHANCE = 0.5   # Бронежилет: с шансом 50% удар поглощается полностью
    SHINE_HP = 1000.0       # финал Бога: в игрока вселяется раненый Шайн
    SHINE_DAMAGE = 100.0
    FLIGHT_MULT = 2.4         # Крылья (серафима, Икара): уклонение превращается в полёт — во столько раз дольше

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
        self.art = None           # ArtifactState (артефакты 1.1.0), создаётся в PlayState
        self.floor_mods = []      # модификаторы «до конца этажа» (Тридцать сребреников); в сохранение не попадают
        self.flying = False       # идёт полёт (уклонение с Крыльями)
        self.landed = False       # полёт только что закончился: PlayState применяет цену Крыльев
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
        self.needles = Needles()    # иголки Живой ели, застрявшие в игроке
        self.rng = random.Random()  # источник случайности брони (в тестах подменяется)
        self.absorbed_hit = False   # True, если последний удар поглотил Бронежилет (play_state показывает эффект и сбрасывает)
        self.dodge_t = 0.0
        self.dodge_cd = 0.0
        self.dodge_dir = pygame.Vector2(1, 0)
        self.shoot_cd = 0.0
        self.knock = pygame.Vector2()
        self.aim = pygame.Vector2(1, 0)
        self.moving = False
        self.flags = set()
        self.form = None            # None или "shine" (финальный бой: игрок играет за Шайна)
        self.god = False            # тест-меню: неуязвимость
        self.debug_damage = None    # тест-меню: принудительные значения
        self.debug_max_hp = None
        self.recompute()               # применить модификаторы персонажа
        self.hp = self.max_hp

    def effective_items(self):
        """Предметы, которые сейчас действуют («Цена бессмертия» отключает три предмета до конца этажа)."""
        if self.art is not None and self.art.disabled:
            return [i for i in self.inv.items if i not in self.art.disabled]
        return self.inv.items

    def recompute(self):
        items = self.effective_items()
        self.flags = self.db.flags(items)
        extra = list(self.char_mods) + list(self.run_mods) + list(self.floor_mods) + [(s, o, v) for s, o, v, _ in self.temp_buffs]
        if self.art is not None:
            extra += self.art.dynamic_mods(self)
        old_max = self.max_hp
        self.stats = self.db.stats(items, extra)
        if self.debug_damage is not None:
            self.stats["damage"] = float(self.debug_damage)
        if self.debug_max_hp is not None:
            self.stats["max_hp"] = float(self.debug_max_hp)
        if self.form == "shine":   # у Шайна свои, фиксированные здоровье и урон
            self.stats["max_hp"], self.stats["damage"] = self.SHINE_HP, self.SHINE_DAMAGE
        self.ghost = "ghost" in self.char.get("traits", []) or "ghost" in self.flags
        self.gravity_immune = "gravity_immune" in self.char.get("traits", []) or "gravity_immune" in self.flags
        self.max_hp = int(round(self.stats["max_hp"]))
        if self.max_hp > old_max:
            self.hp += self.max_hp - old_max
        self.hp = max(1, min(self.hp, self.max_hp)) if self.hp > 0 else 0

    def set_form(self, form):
        """Превращение (None — обычный игрок). Шайн получает полное здоровье и чуть больший хитбокс."""
        self.form = form
        self.RADIUS = 7 if form else 5 * self.char.get("scale", 1.0)
        self.recompute()
        if form:
            self.hp = self.max_hp

    @property
    def invulnerable(self):
        return self.iframes > 0 or self.dodge_t > 0

    def heal(self, amount):
        if "halo_curse" in self.flags:
            amount = max(1, amount // 2)
        if "grail" in self.flags:   # цена Святого Грааля: обычное лечение вполовину слабее
            amount = max(1, amount // 2)
        self.hp = min(self.max_hp, self.hp + amount)

    def hurt(self, amount, source_pos=None):
        if self.god or self.invulnerable or self.hp <= 0:
            return False
        art = self.art
        if art is not None and art.invis_t > 0:   # Шлем Аида: невидимого не ранить
            return False
        if "armor" in self.flags and self.rng.random() < self.ARMOR_BLOCK_CHANCE:
            # Бронежилет поглотил удар целиком: урона нет, но короткая неуязвимость есть (чтобы контактный урон не перебрасывал кубик каждый кадр)
            self.iframes = self.IFRAMES
            self.absorbed_hit = True
            return False
        if art is not None and art.try_absorb():   # Скрижали Завета
            self.iframes = self.IFRAMES
            self.absorbed_hit = True
            return False
        if art is not None and self.hp - amount <= 0 and art.try_survive(amount):   # Игла Кощея / Цена бессмертия
            self.iframes = self.IFRAMES
            return True
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
        if self.flying and self.dodge_t <= 0:
            self.flying, self.landed = False, True
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
        self.flying = "flight" in self.flags
        self.dodge_t = self.DODGE_TIME * (self.FLIGHT_MULT if self.flying else 1.0)
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
            if not self.ghost and not self.flying:   # Ангел и летящий игрок проходят над блоками
                room.push_out(self.pos, self.RADIUS)
            room.clamp_player(self.pos, self.RADIUS)

    def draw(self, surf, off, sprites):
        if self.iframes > 0 and self.dodge_t <= 0 and int(self.iframes * 20) % 2:
            return
        state = "walk" if (self.moving or self.dodge_t > 0) else "idle"
        img = sprites.get("player_shine_form" if self.form == "shine" else "player_" + self.char_id, self.aim.x < 0, state)
        bob = 0   # покачивание теперь входит в кадры ходьбы
        rect = img.get_rect(midbottom=(int(self.pos.x + off.x), int(self.pos.y + off.y) + int(self.RADIUS) + 4 + bob))
        if self.flying:
            rect.move_ip(0, -6)
        if self.dodge_t > 0:
            img = img.copy()
            img.set_alpha(130)
        elif self.art is not None and self.art.invis_t > 0:
            img = img.copy()
            img.set_alpha(70)
        surf.blit(img, rect)
