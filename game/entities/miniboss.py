"""Мини-боссы. Каждый стоит в комнате прямо перед комнатой босса и роняет особый предмет.

* Живая ель (Лес) — стреляет иголками, которые застревают в игроке на 3 с и ранят при каждом движении.
* Домовладелец (дом в Пригороде) — кидает собак; во второй фазе включает телевизор: помехи и кластер снарядов.
* Боевой танк (Город) — постоянно едет к игроку и каждые 5 с стреляет гранатами.
"""
import math
import random

import pygame

from .enemy import Enemy
from .hazard import Hazard
from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H

NEEDLE_COLOR = (170, 215, 90)


def _vec(angle):
    return pygame.Vector2(math.cos(angle), math.sin(angle))


def _toward(src, dst, fallback=(1, 0)):
    d = pygame.Vector2(dst) - src
    return d.normalize() if d.length_squared() > 0 else pygame.Vector2(fallback)


class MiniBoss(Enemy):
    """Общая основа: вторая фаза на половине здоровья, слабое отбрасывание, награда-предмет."""
    SPAWN_TIME = 1.0
    drop_item = None
    KNOCK_SCALE = 0.15

    def __init__(self, kind, pos, data, hp_scale=1.0):
        super().__init__(kind, pos, data, hp_scale)
        self.is_miniboss = True
        self.phase = 1
        self.ui_glitch = False
        self.aim = pygame.Vector2(1, 0)

    def take_damage(self, dmg, direction=None, knockback=0.0):
        return super().take_damage(dmg, direction, knockback * self.KNOCK_SCALE)

    @property
    def second_phase(self):
        return self.hp <= self.max_hp * 0.5

    def _begin(self, dt, room):
        """Общее начало кадра. False — босс ещё появляется."""
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return False
        self._common(dt, room)
        return True


# --- Живая ель ---------------------------------------------------------------------------------
LIVING_SPRUCE = {"name": "Живая ель", "hp": 120, "speed": 20, "radius": 15, "contact": 1,
                 "behavior": "chase", "sprite": "living_spruce", "coin": 0}


class LivingSpruce(MiniBoss):
    drop_item = "thorn_cannon"

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("living_spruce", pos, LIVING_SPRUCE, hp_scale)
        self.state, self.timer = "idle", 1.4
        self.last_attack = None
        self.shots_left = 0

    def _needle(self, shoot, origin, direction, speed):
        # урон 0: иголка не ранит сама, а застревает в игроке (см. PlayState._collisions)
        shoot(origin, direction, speed, 0, radius=3, color=NEEDLE_COLOR, kind="needle")

    def update(self, dt, room, player, shoot):
        if not self._begin(dt, room):
            return
        to_player = player.pos - self.pos
        dist = to_player.length()
        d = to_player / dist if dist > 0 else pygame.Vector2(1, 0)
        self.flip = d.x < 0
        self.timer -= dt
        phase2 = self.second_phase
        if phase2 and self.phase == 1:
            self.phase = 2
            self.state, self.timer = "roar", 1.0
            room.notices.append(("Ель скрипит: корни тянутся к тебе!", "red"))
            room.shake_request = (3, 0.3)
        if self.state == "roar":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.5
        elif self.state == "idle":
            if dist > 70:   # медленно подходит ближе
                self.pos += d * self.speed * (1.4 if phase2 else 1.0) * dt
            if self.timer <= 0:
                self._choose(room, player)
        elif self.state == "wind_fan":
            if self.timer > 0.2:
                self.aim = d.copy()
            if self.timer <= 0:
                n, base = (7 if phase2 else 5), math.atan2(self.aim.y, self.aim.x)
                for i in range(n):
                    self._needle(shoot, self.pos, _vec(base + (i - (n - 1) / 2) * 0.2), 105)
                self._rest()
        elif self.state == "wind_ring":
            if self.timer <= 0:
                n, off = (16 if phase2 else 12), random.uniform(0, math.tau)
                for i in range(n):
                    self._needle(shoot, self.pos, _vec(off + i * math.tau / n), 78)
                self._rest()
        elif self.state == "wind_burst":
            if self.timer <= 0:
                self.state, self.timer, self.shots_left = "burst", 0.0, (8 if phase2 else 5)
        elif self.state == "burst":
            if self.timer <= 0:
                a = math.atan2(d.y, d.x) + random.uniform(-0.1, 0.1)
                self._needle(shoot, self.pos, _vec(a), 125)
                self.shots_left -= 1
                self.timer = 0.13
                if self.shots_left <= 0:
                    self._rest()
        elif self.state == "wind_roots":
            if self.timer <= 0:
                self._rest()
        room.confine(self.pos, self.radius)

    def _rest(self):
        self.state = "idle"
        self.timer = random.uniform(1.0, 1.4) if self.second_phase else random.uniform(1.6, 2.1)

    def _choose(self, room, player):
        options = ["fan", "ring", "burst"]
        if self.phase == 2:
            options.append("roots")
        if self.last_attack in options:
            options.remove(self.last_attack)
        choice = random.choice(options)
        self.last_attack = choice
        if choice == "roots":   # корни вылезают под игроком и рядом: наказание за стояние на месте
            self.state, self.timer = "wind_roots", 1.1
            size = 30
            spots = [player.pos.copy()] + [player.pos + pygame.Vector2(random.uniform(-70, 70), random.uniform(-60, 60))
                                          for _ in range(2)]
            for p in spots:
                x = int(max(ROOM_X, min(ROOM_X + ROOM_W - size, p.x - size / 2)))
                y = int(max(ROOM_Y, min(ROOM_Y + ROOM_H - size, p.y - size / 2)))
                room.hazards.append(Hazard((x, y, size, size), 2, 1.0, 0.3, kind="drop"))
        else:
            self.state, self.timer = "wind_" + choice, {"fan": 0.75, "ring": 0.9, "burst": 0.6}[choice]

    @property
    def warning(self):
        return self.state.startswith("wind_")


# --- Домовладелец ------------------------------------------------------------------------------
LANDLORD = {"name": "Домовладелец", "hp": 130, "speed": 38, "radius": 10, "contact": 1,
            "behavior": "chase", "sprite": "landlord", "coin": 0}
TV_POS = pygame.Vector2(ROOM_X + 36, ROOM_Y + 34)
TV_PERIOD = 5.0       # раз в 5 секунд телевизор даёт помехи и стреляет
TV_WARN = 1.0         # помехи начинаются за секунду до выстрела
MAX_DOGS = 4


class Landlord(MiniBoss):
    drop_item = "old_remote"

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("landlord", pos, LANDLORD, hp_scale)
        self.state, self.timer = "walk", 1.6
        self.tv_on, self.tv_t, self.glitch_t = False, TV_PERIOD, 0.0
        self.tv_pos = TV_POS.copy()

    def _dogs(self, room):
        return sum(1 for e in room.enemies if e.kind == "mutant_dog" and not e.dead)

    def _throw_dogs(self, room, player, n):
        data = room.data.enemies.get("mutant_dog")
        if data is None:
            return
        base = _toward(self.pos, player.pos)
        for i in range(n):
            if self._dogs(room) >= MAX_DOGS:
                break
            direction = base.rotate(math.degrees((i - (n - 1) / 2) * 0.35))
            dog = Enemy("mutant_dog", self.pos + direction * 14, data, 0.8)
            dog.spawn_t = 0.15
            dog.knock = direction * 650      # собаку именно бросают: она отлетает к игроку
            room.enemies.append(dog)

    def update(self, dt, room, player, shoot):
        if not self._begin(dt, room):
            return
        d = _toward(self.pos, player.pos)
        dist = self.pos.distance_to(player.pos)
        self.flip = d.x < 0
        self.timer -= dt
        if self.second_phase and self.phase == 1:
            self.phase = 2
            self.state, self.timer = "tv_start", 1.4
            room.notices.append(("Домовладелец включил телевизор!", "red"))
            room.shake_request = (3, 0.3)
        if self.tv_on:
            self._update_tv(dt, room, player, shoot)
        if self.state == "walk":
            perp = pygame.Vector2(-d.y, d.x)
            radial = 0.5 if dist > 150 else (-0.5 if dist < 85 else 0.0)
            self.pos += (perp * 0.7 + d * radial) * self.speed * dt
            if self.timer <= 0:
                self.state, self.timer = "wind_throw", 0.6
        elif self.state == "wind_throw":
            self.aim = d.copy()
            if self.timer <= 0:
                self._throw_dogs(room, player, 1 if self.phase == 2 else 2)
                self.state, self.timer = "walk", random.uniform(2.6, 3.2) if self.phase == 1 else random.uniform(3.4, 4.2)
        elif self.state == "tv_start" and self.timer <= 0:
            self.tv_on, self.tv_t = True, TV_PERIOD
            self.state, self.timer = "walk", 1.0
        room.confine(self.pos, self.radius)

    def _update_tv(self, dt, room, player, shoot):
        """Телевизор: каждые 5 с — помехи (интерфейс «рвёт»), затем кластер снарядов."""
        self.tv_t -= dt
        self.glitch_t = max(0.0, self.glitch_t - dt)
        if self.tv_t <= TV_WARN:
            self.glitch_t = max(self.glitch_t, 0.2)
        if self.tv_t <= 0:
            self.tv_t = TV_PERIOD
            self.glitch_t = 0.5
            aim = _toward(self.tv_pos, player.pos)
            base = math.atan2(aim.y, aim.x)
            for _ in range(10):
                a = base + random.uniform(-0.55, 0.55)
                shoot(self.tv_pos, _vec(a), random.uniform(70, 125), 1, radius=random.choice((2, 3, 3, 4)),
                      color=random.choice(((190, 220, 255), (255, 255, 255), (120, 150, 255))))
            room.shake_request = (2, 0.2)
        self.ui_glitch = self.glitch_t > 0

    @property
    def tv_warning(self):
        return self.tv_on and self.tv_t <= TV_WARN

    @property
    def warning(self):
        return self.state in ("wind_throw", "tv_start")

    def draw(self, surf, off, sprites):
        if self.tv_on or self.state == "tv_start" or self.phase == 2:
            self._draw_tv(surf, off)
        super().draw(surf, off, sprites)

    def _draw_tv(self, surf, off):
        x, y = int(self.tv_pos.x + off.x), int(self.tv_pos.y + off.y)
        t = pygame.time.get_ticks()
        pygame.draw.rect(surf, (34, 24, 48), (x - 13, y - 11, 26, 22))
        pygame.draw.rect(surf, (120, 90, 60), (x - 12, y - 10, 24, 20))
        pygame.draw.line(surf, (200, 200, 200), (x - 4, y - 11), (x - 9, y - 18), 1)
        pygame.draw.line(surf, (200, 200, 200), (x + 4, y - 11), (x + 9, y - 18), 1)
        screen = pygame.Rect(x - 10, y - 8, 17, 15)
        if not self.tv_on:
            pygame.draw.rect(surf, (30, 36, 46), screen)
            return
        pygame.draw.rect(surf, (150, 190, 255) if self.tv_warning and (t // 70) % 2 else (70, 110, 190), screen)
        for i in range(5):   # «снег» на экране
            nx, ny = x - 10 + (t // 50 * (7 + i * 3)) % 15, y - 8 + (t // 50 * (5 + i * 4)) % 13
            pygame.draw.rect(surf, (255, 255, 255), (nx, ny, 2, 2))
        if self.tv_warning and (t // 90) % 2:
            pygame.draw.rect(surf, (255, 70, 70), (x - 15, y - 13, 30, 26), 1)


# --- Боевой танк -------------------------------------------------------------------------------
TANK = {"name": "Боевой танк", "hp": 160, "speed": 40, "radius": 15, "contact": 2,
        "behavior": "chase", "sprite": "tank", "coin": 0}
TANK_FIRE_EVERY = 5.0   # граната раз в 5 секунд
SHELL_FLIGHT = 1.1
BLAST_RADIUS = 26


class Tank(MiniBoss):
    drop_item = "kevlar_vest"
    KNOCK_SCALE = 0.05

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("tank", pos, TANK, hp_scale)
        self.fire_t = 2.5          # первый выстрел чуть позже, дальше строго раз в 5 с
        self.shells = []
        self.phase_notice = False

    def update(self, dt, room, player, shoot):
        if not self._begin(dt, room):
            return
        d = _toward(self.pos, player.pos)
        self.aim = d
        self.flip = d.x < 0
        if self.second_phase and self.phase == 1:
            self.phase = 2
            room.notices.append(("Танк заряжает сразу три гранаты!", "red"))
        # постоянно едет в сторону игрока
        self.pos += d * self.speed * (1.3 if self.phase == 2 else 1.0) * dt
        self.fire_t -= dt
        if self.fire_t <= 0:
            self.fire_t = TANK_FIRE_EVERY
            self._fire(player)
        self._update_shells(dt, room)
        room.confine(self.pos, self.radius)

    def _fire(self, player):
        targets = [player.pos.copy()]
        if self.phase == 2:
            targets += [player.pos + pygame.Vector2(random.uniform(-60, 60), random.uniform(-60, 60)) for _ in range(2)]
        for t in targets:
            t.x = max(ROOM_X + BLAST_RADIUS, min(ROOM_X + ROOM_W - BLAST_RADIUS, t.x))
            t.y = max(ROOM_Y + BLAST_RADIUS, min(ROOM_Y + ROOM_H - BLAST_RADIUS, t.y))
            self.shells.append({"start": self.pos.copy(), "target": t, "t": 0.0})

    def _update_shells(self, dt, room):
        left = []
        for sh in self.shells:
            sh["t"] += dt
            if sh["t"] < SHELL_FLIGHT:
                left.append(sh)
                continue
            c = sh["target"]
            rect = pygame.Rect(int(c.x - BLAST_RADIUS), int(c.y - BLAST_RADIUS), BLAST_RADIUS * 2, BLAST_RADIUS * 2)
            room.hazards.append(Hazard(rect, 2, 0.0, 0.3, kind="blast"))
            room.shake_request = (3, 0.25)
        self.shells = left

    @property
    def warning(self):
        return self.fire_t < 0.6 and self.spawn_t <= 0

    def draw(self, surf, off, sprites):
        # метки будущих взрывов рисуются под танком
        blink = (pygame.time.get_ticks() // 90) % 2
        for sh in self.shells:
            c = sh["target"]
            if blink:
                pygame.draw.circle(surf, (255, 70, 70), (int(c.x + off.x), int(c.y + off.y)), BLAST_RADIUS, 1)
        super().draw(surf, off, sprites)
        if self.spawn_t > 0:
            return
        base = (int(self.pos.x + off.x), int(self.pos.y + off.y) - 3)
        tip = (base[0] + self.aim.x * 17, base[1] + self.aim.y * 17)
        pygame.draw.line(surf, (34, 24, 48), base, tip, 5)
        pygame.draw.line(surf, (104, 120, 96), base, tip, 3)
        for sh in self.shells:   # летящая граната по дуге
            f = min(1.0, sh["t"] / SHELL_FLIGHT)
            ground = sh["start"].lerp(sh["target"], f)
            h = math.sin(math.pi * f) * 34
            pos = (int(ground.x + off.x), int(ground.y + off.y - h))
            pygame.draw.circle(surf, (34, 24, 48), pos, 4)
            pygame.draw.circle(surf, (230, 200, 90), pos, 3)


# --- Хранитель врат ---------------------------------------------------------------------------
GATE_KEEPER = {"name": "Хранитель врат", "hp": 520, "speed": 30, "radius": 15, "contact": 2,
               "behavior": "chase", "sprite": "gate_keeper", "coin": 0}
LEASH = 130.0         # дальше этого расстояния от босса он начинает восстанавливать здоровье
HEAL_RATE = 0.035     # доля максимального здоровья в секунду
MAX_SUMMONED = 5


class GateKeeper(MiniBoss):
    """Каменная статуя ангела с весами (Небеса). Бьёт весами, призывает врагов локации и лечится,
    если игрок отходит от него дальше LEASH. Награды у него нет: после победы открывается дверь к Богу."""
    drop_item = None
    KNOCK_SCALE = 0.1

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("gate_keeper", pos, GATE_KEEPER, hp_scale)
        self.state, self.timer = "walk", 1.6
        self.last_attack = None
        self.away_t = 0.0
        self.healing = False
        self.hint_shown = False

    def _summoned(self, room):
        pending = sum(c for _, c in room.spawn_requests)
        return pending + sum(1 for e in room.enemies if not getattr(e, "is_miniboss", False) and not e.dead)

    def update(self, dt, room, player, shoot):
        if not self._begin(dt, room):
            return
        d = _toward(self.pos, player.pos)
        dist = self.pos.distance_to(player.pos)
        self.flip = d.x < 0
        self.timer -= dt
        # Нужно держаться рядом: пока игрок далеко, Хранитель восстанавливает здоровье
        if dist > LEASH and self.hp < self.max_hp:
            self.away_t += dt
        else:
            self.away_t = max(0.0, self.away_t - dt * 2)
        self.healing = self.away_t > 0.4
        if self.healing:
            self.hp = min(self.max_hp, self.hp + self.max_hp * HEAL_RATE * dt)
            if not self.hint_shown:
                self.hint_shown = True
                room.notices.append(("Хранитель восстанавливает силы! Держись рядом с ним.", "red"))
        if self.second_phase and self.phase == 1:
            self.phase = 2
            self.state, self.timer = "roar", 1.0
            room.notices.append(("Хранитель врат раскалывает пол: призыв сильнее!", "red"))
            room.shake_request = (4, 0.4)
        if self.state == "roar":
            if self.timer <= 0:
                self.state, self.timer = "walk", 0.6
        elif self.state == "walk":
            if dist > 64:
                self.pos += d * self.speed * (1.25 if self.phase == 2 else 1.0) * dt
            if self.timer <= 0:
                self._choose(room, player, d)
        elif self.state in ("wind_slam", "wind_sweep", "wind_summon"):
            if self.timer <= 0:
                if self.state == "wind_summon":
                    self._summon(room)
                self.state, self.timer = "walk", random.uniform(1.0, 1.5) if self.phase == 2 else random.uniform(1.5, 2.2)
        room.confine(self.pos, self.radius)

    def _choose(self, room, player, d):
        options = ["slam", "sweep", "summon"]
        if self._summoned(room) >= MAX_SUMMONED:
            options.remove("summon")
        if self.last_attack in options and len(options) > 1:
            options.remove(self.last_attack)
        choice = random.choice(options)
        self.last_attack = choice
        if choice == "slam":      # удар весами сверху: круг под игроком (и рядом во второй фазе)
            self.state, self.timer = "wind_slam", 1.05
            spots = [player.pos.copy()]
            if self.phase == 2:
                spots += [player.pos + pygame.Vector2(random.uniform(-60, 60), random.uniform(-50, 50)) for _ in range(2)]
            for p in spots:
                self._blast(room, p, 72, 1.0)
        elif choice == "sweep":   # взмах чашей весов: дуга ударов перед боссом, один за другим
            self.state, self.timer = "wind_sweep", 1.0
            base = math.atan2(d.y, d.x)
            for i in range(5):
                a = base + (i - 2) * 0.45
                self._blast(room, self.pos + _vec(a) * (58 + (i % 2) * 22), 46, 0.7 + i * 0.07)
        else:
            self.state, self.timer = "wind_summon", 1.0

    def _blast(self, room, center, size, warmup):
        x = max(ROOM_X, min(ROOM_X + ROOM_W - size, center.x - size / 2))
        y = max(ROOM_Y, min(ROOM_Y + ROOM_H - size, center.y - size / 2))
        room.hazards.append(Hazard(pygame.Rect(int(x), int(y), int(size), int(size)), 2, warmup, 0.3, kind="blast"))

    def _summon(self, room):
        pool = [k for k, w in room.zone["enemy_pool"] for _ in range(w)]
        n = min(3 if self.phase == 2 else 2, MAX_SUMMONED - self._summoned(room))
        for _ in range(max(0, n)):
            room.request_spawn(random.choice(pool), 1)
        room.notices.append(("Хранитель призывает небесную стражу!", "grey"))

    @property
    def warning(self):
        return self.state in ("wind_slam", "wind_sweep", "wind_summon") and self.spawn_t <= 0

    def draw(self, surf, off, sprites):
        super().draw(surf, off, sprites)
        if self.spawn_t > 0:
            return
        # кольцо «держись рядом»: внутри него Хранитель не лечится
        cx, cy = self.pos.x + off.x, self.pos.y + off.y
        blink = (pygame.time.get_ticks() // 120) % 2
        col = (255, 90, 90) if self.healing and blink else ((140, 255, 150) if self.healing else (255, 225, 120))
        for i in range(28):
            a = i * math.tau / 28
            pygame.draw.circle(surf, col, (int(cx + math.cos(a) * LEASH), int(cy + math.sin(a) * LEASH)), 1)


MINIBOSSES = {"living_spruce": LivingSpruce, "landlord": Landlord, "tank": Tank, "gate_keeper": GateKeeper}


def create_miniboss(kind, pos, hp_scale=1.0):
    if kind not in MINIBOSSES:
        raise ValueError(f"неизвестный мини-босс: {kind}")
    return MINIBOSSES[kind](pos, hp_scale)
