"""Боссы. Лесник: бросок, пилы, во второй фазе — валит деревья на арену."""
import math
import random

import pygame

from .enemy import Enemy
from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H
from .hazard import Hazard, Laser

LUMBERJACK = {"name": "Лесник", "hp": 250, "speed": 68, "radius": 16, "contact": 1,
              "behavior": "chase", "sprite": "lumberjack", "coin": 0}

# Кандидаты на падение деревьев: углы и края вдали от дверей — проход всегда остаётся
STUMP_SPOTS = [
    pygame.Rect(ROOM_X + 8, ROOM_Y + 8, 40, 40), pygame.Rect(ROOM_X + ROOM_W - 48, ROOM_Y + 8, 40, 40),
    pygame.Rect(ROOM_X + 8, ROOM_Y + ROOM_H - 48, 40, 40), pygame.Rect(ROOM_X + ROOM_W - 48, ROOM_Y + ROOM_H - 48, 40, 40),
    pygame.Rect(ROOM_X + 100, ROOM_Y + 8, 40, 32), pygame.Rect(ROOM_X + ROOM_W - 140, ROOM_Y + ROOM_H - 40, 40, 32),
]
MAX_STUMPS = 4


class Lumberjack(Enemy):
    SPAWN_TIME = 1.2

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("lumberjack", pos, LUMBERJACK, hp_scale)
        self.state = "walk"
        self.timer = 1.5
        self.last_attack = None
        self.phase = 1
        self.aim = pygame.Vector2(1, 0)
        self.warn_rects = []
        self.is_boss = True

    def _next_phase(self, room):
        self.phase = 2
        self.state, self.timer = "roar", 1.2
        room.request_spawn("bush", 2)
        room.effects_hint = "roar"

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        if self.phase == 1 and self.hp <= self.max_hp * 0.5:
            self._next_phase(room)
        self.timer -= dt
        to_player = player.pos - self.pos
        d = to_player.normalize() if to_player.length_squared() > 0 else pygame.Vector2(1, 0)
        self.flip = d.x < 0
        spd = self.speed * (1.3 if self.phase == 2 else 1.0)
        if self.state == "roar":
            if self.timer <= 0:
                self.state, self.timer = "walk", 0.8
        elif self.state == "walk":
            self.pos += d * spd * dt
            if self.timer <= 0:
                self._choose_attack(room, player)
        elif self.state == "wind_charge":
            if self.timer > 0.35:
                self.aim = d.copy()
            if self.timer <= 0:
                self.state, self.timer = "charge", 0.65
                self.contact = 2
        elif self.state == "charge":
            self.pos += self.aim * 275 * dt
            if self.timer <= 0 or room.confine(self.pos, self.radius):
                self.state, self.timer, self.contact = "recover", 0.9, 1
                room.shake_request = (3, 0.2)
                if self.phase == 2:   # после рывка во второй фазе — веер пил
                    off = random.uniform(0, math.tau)
                    for i in range(8):
                        a = off + i * math.tau / 8
                        shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 95, 1, radius=4, color=(200, 210, 230))
        elif self.state == "wind_saws":
            if self.timer <= 0:
                n = 16 if self.phase == 2 else 10
                off = random.uniform(0, math.tau)
                for i in range(n):
                    a = off + i * math.tau / n
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 105, 1, radius=4, color=(200, 210, 230))
                self.state, self.timer = "walk", 0.7
        elif self.state == "wind_fell":
            if self.timer <= 0:
                for rect in self.warn_rects:
                    room.add_stump(rect)
                    room.damage_zones.append((rect.copy(), 2))
                self.warn_rects = []
                room.shake_request = (4, 0.3)
                self.state, self.timer = "walk", 0.7
        elif self.state == "recover" and self.timer <= 0:
            self.state, self.timer = "walk", 0.55 if self.phase == 2 else 0.9
        room.confine(self.pos, self.radius)

    def _choose_attack(self, room, player):
        options = ["charge", "saws"]
        if self.phase == 2 and len(room.stumps) < MAX_STUMPS:
            options.append("fell")
        if self.last_attack in options and len(options) > 1:
            options.remove(self.last_attack)
        choice = random.choice(options)
        self.last_attack = choice
        if choice == "charge":
            self.state, self.timer = "wind_charge", 0.9
            self.aim = (player.pos - self.pos).normalize() if (player.pos - self.pos).length_squared() else self.aim
        elif choice == "saws":
            self.state, self.timer = "wind_saws", 0.7
        else:
            free = [r for r in STUMP_SPOTS if not any(r.colliderect(s) for s in room.stumps)]
            random.shuffle(free)
            count = min(3, MAX_STUMPS - len(room.stumps))
            self.warn_rects = free[:count]
            self.state, self.timer = "wind_fell", 1.4
            if not self.warn_rects:
                self.state, self.timer = "walk", 0.5

    @property
    def warning(self):
        return self.state in ("wind_charge", "wind_saws", "wind_fell")

    def draw(self, surf, off, sprites):
        blink = int(pygame.time.get_ticks() / 90) % 2
        for r in self.warn_rects:  # предупреждение о падении дерева
            col = (255, 60, 60) if blink else (255, 190, 60)
            pygame.draw.rect(surf, col, r.move(off.x, off.y), 2)
        if self.state == "wind_charge" and blink:
            end = self.pos + self.aim * 300
            pygame.draw.line(surf, (255, 60, 60), (self.pos.x + off.x, self.pos.y + off.y), (end.x + off.x, end.y + off.y), 2)
        if self.state == "wind_saws" and blink:
            pygame.draw.circle(surf, (255, 255, 255), (int(self.pos.x + off.x), int(self.pos.y + off.y)), self.radius + 6, 1)
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        img = sprites.white(self.sprite) if self.hurt_t > 0 else sprites.get(self.sprite, self.flip)
        if self.state == "roar" and blink:
            img = sprites.white(self.sprite)
        surf.blit(img, img.get_rect(center=(int(self.pos.x + off.x), int(self.pos.y + off.y))))


NEIGHBOR = {"name": "Сосед", "hp": 210, "speed": 48, "radius": 14, "contact": 1,
            "behavior": "chase", "sprite": "neighbor_boss", "coin": 0}
MOWER_SPEED = 280.0
LANE = 28


def drop_hazards(player_pos, extra=3, size=34, warmup=1.1):
    """Падающие предметы: одна зона под игроком (с предупреждением) и несколько случайных."""
    spots = [(int(player_pos.x - size / 2), int(player_pos.y - size / 2))]
    for _ in range(extra):
        spots.append((random.randint(ROOM_X, ROOM_X + ROOM_W - size), random.randint(ROOM_Y, ROOM_Y + ROOM_H - size)))
    hs = []
    for x, y in spots:
        x = max(ROOM_X, min(ROOM_X + ROOM_W - size, x))
        y = max(ROOM_Y, min(ROOM_Y + ROOM_H - size, y))
        hs.append(Hazard((x, y, size, size), 2, warmup, 0.25, kind="drop"))
    return hs


class Neighbor(Enemy):
    """Сосед с газонокосилкой. Фаза 1: косилка и мусор; 2: бытовая техника; 3: призывает соседей."""

    SPAWN_TIME = 1.2

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("neighbor_boss", pos, NEIGHBOR, 1.0)
        self.state = "walk"
        self.timer = 1.5
        self.phase = 1
        self.last = None
        self.cast_kind = None
        self.is_boss = True
        # перезарядка «спавнящих» атак (косилки, падающие предметы, призыв): 5–10 секунд
        self.cooldowns = {"mow": 0.0, "rain": 0.0, "summon": 0.0}

    @staticmethod
    def _cooldown():
        return random.uniform(5.0, 10.0)

    def _phase_for_hp(self):
        ratio = self.hp / self.max_hp
        return 3 if ratio <= 0.33 else 2 if ratio <= 0.66 else 1

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        new_phase = self._phase_for_hp()
        if new_phase > self.phase:
            self.phase = new_phase
            self.state, self.timer, self.cast_kind = "roar", 1.1, None
            room.shake_request = (3, 0.3)
            if new_phase == 3:
                room.request_spawn("neighbor", 2)
        self.timer -= dt
        for k in self.cooldowns:
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)
        to_player = player.pos - self.pos
        d = to_player.normalize() if to_player.length_squared() > 0 else pygame.Vector2(1, 0)
        self.flip = d.x < 0
        if self.state == "roar":
            if self.timer <= 0:
                self.state, self.timer = "walk", 0.8
        elif self.state == "walk":
            self.pos += d * self.speed * (1 + 0.15 * (self.phase - 1)) * dt
            if self.timer <= 0:
                self._cast(room, player)
        elif self.state == "cast":
            if self.timer <= 0:
                self._resolve_cast(room, player, shoot)
                self.state, self.timer = "walk", (1.4, 1.1, 0.9)[self.phase - 1]
        room.confine(self.pos, self.radius)

    def _alive_neighbors(self, room):
        pending = sum(c for k, c in room.spawn_requests if k == "neighbor")
        return pending + sum(1 for e in room.enemies if e.kind == "neighbor" and not e.dead)

    def _cast(self, room, player):
        options = ["throw"]  # метание мусора — без перезарядки, заполняет паузы
        free_arena = not room.hazards  # новые зоны только когда прошлые исчезли
        if free_arena and self.cooldowns["mow"] <= 0:
            options.append("mow")
        if self.phase >= 2 and free_arena and self.cooldowns["rain"] <= 0:
            options.append("rain")
        if self.phase == 3 and self.cooldowns["summon"] <= 0 and self._alive_neighbors(room) < 3:
            options.append("summon")
        if self.last in options and len(options) > 1:
            options.remove(self.last)
        self.last = choice = random.choice(options)
        self.state = "cast"
        self.cast_kind = choice
        if choice in self.cooldowns:
            self.cooldowns[choice] = self._cooldown()
        if choice == "mow":      # зоны предупреждения появляются сразу, косилки выезжают через 1 с
            room.hazards.extend(self._mow_hazards(player))
            self.timer, self.cast_kind = 0.8, None
        elif choice == "rain":
            room.hazards.extend(self._rain_hazards(player))
            self.timer, self.cast_kind = 0.7, None
        elif choice == "throw":
            self.timer = 0.6
        else:
            self.timer = 1.0

    def _resolve_cast(self, room, player, shoot):
        to_player = player.pos - self.pos
        if self.cast_kind == "throw":
            base = math.atan2(to_player.y, to_player.x) if to_player.length_squared() else 0.0
            if self.phase == 1:
                shots = [(a, 3, (140, 220, 100), 100) for a in (-0.5, -0.25, 0, 0.25, 0.5)]
            else:
                shots = [(-0.3, 3, (240, 240, 240), 130), (0.0, 5, (255, 160, 60), 95), (0.3, 4, (120, 200, 255), 115)]
            for off, radius, color, speed in shots:
                a = base + off
                shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), speed, 1, radius=radius, color=color)
        elif self.cast_kind == "summon":
            if self._alive_neighbors(room) < 4:
                room.request_spawn("neighbor", 2)
        self.cast_kind = None

    @staticmethod
    def _lanes(first, count, low, high, gap=34):
        """Выбирает count непересекающихся позиций полос; первая — под игрока."""
        picks = [max(low, min(high, first))]
        tries = 0
        while len(picks) < count and tries < 40:
            tries += 1
            v = random.randint(low, high)
            if all(abs(v - p) >= gap for p in picks):
                picks.append(v)
        return picks

    def _mow_hazards(self, player):
        hs = []
        n_h = 2
        n_v = {1: 0, 2: 1, 3: 2}[self.phase]
        life = (ROOM_W + 60) / MOWER_SPEED + 0.1
        for y in self._lanes(int(player.pos.y - LANE / 2), n_h, ROOM_Y, ROOM_Y + ROOM_H - LANE):
            left = random.random() < 0.5
            warn = pygame.Rect(ROOM_X, y, ROOM_W, LANE)
            start = pygame.Rect(ROOM_X - 30 if left else ROOM_X + ROOM_W, y, 30, LANE)
            hs.append(Hazard(start, 2, 1.0, life, (MOWER_SPEED if left else -MOWER_SPEED, 0), warn, "mower"))
        if n_v:
            life_v = (ROOM_H + 60) / MOWER_SPEED + 0.1
            for x in self._lanes(int(player.pos.x - LANE / 2), n_v, ROOM_X, ROOM_X + ROOM_W - LANE, 60):
                up = random.random() < 0.5
                warn = pygame.Rect(x, ROOM_Y, LANE, ROOM_H)
                start = pygame.Rect(x, ROOM_Y - 30 if up else ROOM_Y + ROOM_H, LANE, 30)
                hs.append(Hazard(start, 2, 1.0, life_v, (0, MOWER_SPEED if up else -MOWER_SPEED), warn, "mower"))
        return hs

    def _rain_hazards(self, player):
        return drop_hazards(player.pos, 3, 34, 1.1)

    @property
    def warning(self):
        return self.state == "cast"

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        blink = int(pygame.time.get_ticks() / 90) % 2
        img = sprites.white(self.sprite) if self.hurt_t > 0 or (self.state == "roar" and blink) else sprites.get(self.sprite, self.flip)
        surf.blit(img, img.get_rect(center=(int(self.pos.x + off.x), int(self.pos.y + off.y))))
        if self.state == "cast" and blink:
            pygame.draw.circle(surf, (255, 255, 255), (int(self.pos.x + off.x), int(self.pos.y + off.y)), self.radius + 6, 1)


MAYOR = {"name": "Мэр", "hp": 430, "speed": 0, "radius": 16, "contact": 1,
         "behavior": "chase", "sprite": "mayor", "coin": 0}
# закон: (название на экране, перезарядка мин, макс)
LAWS = {
    "hire": ("Закон о трудоустройстве", 5.0, 10.0),
    "demolish": ("Приказ о сносе", 5.0, 10.0),
    "reform": ("Градостроительная реформа", 8.0, 12.0),
    "tax": ("Налог на скорострельность", 10.0, 15.0),
}


class Mayor(Enemy):
    """Мэр. Фаза 1: подписывает законы (каждый заранее показывается). Фаза 2: стол-монстр.
    Фаза 3: сюрреалистическая форма со спиральным обстрелом."""

    SPAWN_TIME = 1.4

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("mayor", pos, MAYOR, 1.0)
        self.state = "idle"
        self.timer = 1.8
        self.phase = 1
        self.last = None
        self.law = None
        self.aim = pygame.Vector2(1, 0)
        self.spin = 0.0
        self.is_boss = True
        self.cooldowns = {k: 0.0 for k in list(LAWS) + ["spiral"]}

    def _phase_for_hp(self):
        ratio = self.hp / self.max_hp
        return 3 if ratio <= 0.33 else 2 if ratio <= 0.66 else 1

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        new_phase = self._phase_for_hp()
        if new_phase > self.phase:
            self.phase = new_phase
            self.sprite = "mayor_desk" if new_phase == 2 else "mayor_surreal"
            self.radius = 17 if new_phase == 2 else 15
            self.state, self.timer, self.law = "roar", 1.4, None
            room.shake_request = (4, 0.4)
        self.timer -= dt
        for k in self.cooldowns:
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)
        to_player = player.pos - self.pos
        d = to_player.normalize() if to_player.length_squared() > 0 else pygame.Vector2(1, 0)
        self.flip = d.x < 0
        st = self.state
        if st == "roar":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.8
        elif st == "idle":
            self.pos += d * (24, 44, 38)[self.phase - 1] * dt   # в первой фазе медленно подходит
            if self.timer <= 0:
                self._choose(room, player)
        elif st == "sign":
            if self.timer <= 0:
                self._apply_law(room, player)
                self.state, self.timer, self.law = "idle", (1.5, 1.2, 1.0)[self.phase - 1], None
        elif st == "wind_stamp":
            if self.timer <= 0:
                base = math.atan2(to_player.y, to_player.x) if to_player.length_squared() else 0.0
                for off in (-0.5, -0.25, 0.0, 0.25, 0.5):
                    a = base + off
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 115, 1, radius=4, color=(250, 245, 225))
                self.state, self.timer = "idle", (1.5, 1.2, 1.0)[self.phase - 1]
        elif st == "wind_charge":
            if self.timer > 0.35:
                self.aim = d.copy()
            if self.timer <= 0:
                self.state, self.timer, self.contact = "charge", 0.6, 2
        elif st == "charge":
            self.pos += self.aim * 265 * dt
            if self.timer <= 0 or room.confine(self.pos, self.radius):
                self.state, self.timer, self.contact = "recover", 0.9, 1
                room.shake_request = (3, 0.2)
        elif st == "recover":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.8
        elif st == "wind_papers":
            if self.timer <= 0:
                n = 14
                off = random.uniform(0, math.tau)
                for i in range(n):
                    a = off + i * math.tau / n
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 100, 1, radius=4, color=(250, 245, 225))
                self.state, self.timer = "idle", 1.4
        elif st == "wind_spiral":
            if self.timer <= 0:
                self.state, self.timer, self.spin_tick = "spiral", 3.6, 0.0
        elif st == "spiral":
            self.spin_tick -= dt
            if self.spin_tick <= 0:
                self.spin_tick = 0.2
                self.spin += 0.45
                for arm in range(4):
                    a = self.spin + arm * math.tau / 4
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 80, 1, radius=3, color=(200, 120, 255))
            if self.timer <= 0:
                self.state, self.timer = "recover", 1.0
        room.confine(self.pos, self.radius)

    def _enemy_count(self, room):
        pending = sum(c for _, c in room.spawn_requests)
        return pending + sum(1 for e in room.enemies if not getattr(e, "is_boss", False) and not e.dead)

    def _choose(self, room, player):
        options = []
        calm = not room.hazards and room.reshuffle_t is None
        if self.cooldowns["hire"] <= 0 and self._enemy_count(room) < 5:
            options.append("hire")
        if self.cooldowns["demolish"] <= 0 and calm:
            options.append("demolish")
        if self.cooldowns["reform"] <= 0 and calm:
            options.append("reform")
        if self.cooldowns["tax"] <= 0:
            options.append("tax")
        if self.phase == 1:
            options = options * 2  # в первой фазе законы — основная атака
        options.append("stamp")
        if self.phase >= 2:
            options += ["charge", "papers"]
        if self.phase == 3 and self.cooldowns["spiral"] <= 0:
            options.append("spiral")
        pool = [o for o in options if o != self.last] or options
        choice = random.choice(pool)
        self.last = choice
        if choice in LAWS:
            self.law = choice
            self.cooldowns[choice] = random.uniform(LAWS[choice][1], LAWS[choice][2])
            self.state, self.timer = "sign", 1.1
        elif choice == "stamp":
            self.state, self.timer = "wind_stamp", 0.6
        elif choice == "charge":
            self.aim = (player.pos - self.pos).normalize() if (player.pos - self.pos).length_squared() else self.aim
            self.state, self.timer = "wind_charge", 0.9
        elif choice == "papers":
            self.state, self.timer = "wind_papers", 0.7
        else:
            self.cooldowns["spiral"] = random.uniform(6.0, 10.0)
            self.state, self.timer = "wind_spiral", 0.9

    def _apply_law(self, room, player):
        law = self.law
        if law == "hire":
            room.request_spawn(random.choice(("rad_rat", "mutant_cop")), 3)
        elif law == "demolish":
            room.hazards.extend(drop_hazards(player.pos, 5, 34, 1.2))
        elif law == "reform":
            room.begin_reshuffle(player.pos, 4)
        elif law == "tax":
            room.player_effects.append(("fire_delay", "mul", 1.5, 10.0, "Налог на скорострельность: стрельба медленнее (10 с)"))

    @property
    def warning(self):
        return self.state in ("sign", "wind_stamp", "wind_charge", "wind_papers", "wind_spiral")

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        blink = int(pygame.time.get_ticks() / 90) % 2
        img = sprites.white(self.sprite) if self.hurt_t > 0 or (self.state == "roar" and blink) else sprites.get(self.sprite, self.flip)
        cx, cy = int(self.pos.x + off.x), int(self.pos.y + off.y)
        surf.blit(img, img.get_rect(center=(cx, cy)))
        if self.state == "wind_charge" and blink:
            end = self.pos + self.aim * 300
            pygame.draw.line(surf, (255, 60, 60), (cx, cy), (end.x + off.x, end.y + off.y), 2)
        if self.state in ("wind_papers", "wind_spiral", "wind_stamp") and blink:
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), self.radius + 6, 1)
        if self.state == "sign" and self.law:  # название закона показывается заранее
            from ..ui.text import draw_text
            draw_text(surf, LAWS[self.law][0], (cx, cy - self.radius - 14), "gold" if blink else "white", 11, "midbottom")


CHAOS = {"name": "Хаос", "hp": 310, "speed": 0, "radius": 18, "contact": 1,
         "behavior": "chase", "sprite": "chaos", "coin": 0}
# «правки реальности»: (подпись, [(характеристика, операция, значение), ...]) на 8 секунд
REALITY_EDITS = (
    ("Свойства предметов изменены: быстро, но слабо (8 с)", [("damage", "mul", 0.6), ("fire_delay", "mul", 0.55)]),
    ("Свойства предметов изменены: медленно, но сильно (8 с)", [("damage", "mul", 1.7), ("fire_delay", "mul", 1.8)]),
    ("Свойства предметов изменены: снаряды ближе и тяжелее (8 с)", [("range", "mul", 0.65), ("damage", "mul", 1.4)]),
    ("Свойства предметов изменены: ты быстрее, но слабее (8 с)", [("speed", "mul", 1.35), ("damage", "mul", 0.8)]),
)
CHAOS_LAWS = {  # название над боссом, перезарядка мин/макс
    "summon": ("Фрагменты глаз", 5.0, 10.0),
    "slam": ("Падение обломков", 5.0, 10.0),
    "edit": ("Правка свойств предметов", 12.0, 16.0),
    "geometry": ("Геометрия комнаты изменится", 10.0, 14.0),
    "spiral": ("Спираль", 6.0, 10.0),
}


class Chaos(Enemy):
    """Хаос. Фаза 1: осколки, глаза, обломки. Фаза 2: правки свойств предметов и геометрии комнаты.
    Фаза 3: сбои интерфейса, звука и картинки + спиральный обстрел. Всё предупреждается заранее."""

    SPAWN_TIME = 1.6

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("chaos", pos, CHAOS, 1.0)
        self.state, self.timer, self.phase = "idle", 1.8, 1
        self.last = None
        self.law = None
        self.aim = pygame.Vector2(1, 0)
        self.spin = 0.0
        self.spin_tick = 0.0
        self.is_boss = True
        self.ui_glitch = False
        self.cooldowns = {k: 0.0 for k in CHAOS_LAWS}
        self.pupil = pygame.Vector2()

    def _phase_for_hp(self):
        ratio = self.hp / self.max_hp
        return 3 if ratio <= 0.33 else 2 if ratio <= 0.66 else 1

    def _enemy_count(self, room):
        pending = sum(c for _, c in room.spawn_requests)
        return pending + sum(1 for e in room.enemies if not getattr(e, "is_boss", False) and not e.dead)

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        new_phase = self._phase_for_hp()
        if new_phase > self.phase:
            self.phase = new_phase
            self.state, self.timer, self.law = "roar", 1.5, None
            room.shake_request = (4, 0.5)
            if new_phase == 2:
                room.notices.append(("Реальность начинает меняться...", "gold"))
            else:
                self.ui_glitch = True
                room.notices.append(("Интерфейс и звук дают сбой!", "red"))
        self.timer -= dt
        for k in self.cooldowns:
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)
        to_player = player.pos - self.pos
        d = to_player.normalize() if to_player.length_squared() > 0 else pygame.Vector2(1, 0)
        self.pupil = d
        self.flip = d.x < 0
        st = self.state
        if st == "roar":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.8
        elif st == "idle":
            self.pos += d * (30, 36, 42)[self.phase - 1] * dt
            if self.timer <= 0:
                self._choose(room, player)
        elif st == "sign":
            if self.timer <= 0:
                self._apply(room, player)
                self.state, self.timer, self.law = "idle", (2.0, 1.6, 1.3)[self.phase - 1], None
        elif st == "wind_shards":
            if self.timer <= 0:
                n = 16 if self.phase == 3 else 12
                off = random.uniform(0, math.tau)
                for i in range(n):
                    a = off + i * math.tau / n
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 95, 1, radius=3,
                          color=random.choice(((255, 90, 220), (80, 255, 210), (255, 235, 90))))
                self.state, self.timer = "idle", (1.8, 1.5, 1.2)[self.phase - 1]
        elif st == "wait":
            if self.timer <= 0:
                self.state, self.timer = "idle", 1.2
        elif st == "wind_charge":
            if self.timer > 0.35:
                self.aim = d.copy()
            if self.timer <= 0:
                self.state, self.timer, self.contact = "charge", 0.6, 2
        elif st == "charge":
            self.pos += self.aim * 235 * dt
            if self.timer <= 0 or room.confine(self.pos, self.radius):
                self.state, self.timer, self.contact = "recover", 0.9, 1
                room.shake_request = (3, 0.2)
        elif st == "recover":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.8
        elif st == "wind_spiral":
            if self.timer <= 0:
                self.state, self.timer, self.spin_tick = "spiral", 3.2, 0.0
        elif st == "spiral":
            self.spin_tick -= dt
            if self.spin_tick <= 0:
                self.spin_tick = 0.2
                self.spin += 0.45
                for arm in range(3):
                    a = self.spin + arm * math.tau / 3
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 80, 1, radius=3, color=(255, 90, 220))
            if self.timer <= 0:
                self.state, self.timer = "recover", 1.0
        room.confine(self.pos, self.radius)

    def _choose(self, room, player):
        calm = not room.hazards and room.reshuffle_t is None
        options = ["shards", "shards"]
        if self.cooldowns["summon"] <= 0 and self._enemy_count(room) < 4:
            options.append("summon")
        if self.cooldowns["slam"] <= 0 and calm:
            options.append("slam")
        if self.phase >= 2:
            options.append("charge")
            if self.cooldowns["edit"] <= 0:
                options.append("edit")
            if self.cooldowns["geometry"] <= 0 and calm:
                options.append("geometry")
        if self.phase == 3 and self.cooldowns["spiral"] <= 0:
            options.append("spiral")
        pool = [o for o in options if o != self.last] or options
        choice = self.last = random.choice(pool)
        if choice in CHAOS_LAWS:
            lo, hi = CHAOS_LAWS[choice][1:]
            self.cooldowns[choice] = random.uniform(lo, hi)
        if choice in ("edit", "geometry"):
            self.law, self.state, self.timer = choice, "sign", 1.3
        elif choice == "summon":
            self.law, self.state, self.timer = choice, "sign", 0.9
        elif choice == "slam":
            room.hazards.extend(drop_hazards(player.pos, 4, 36, 1.2))
            self.state, self.timer = "wait", 0.8
        elif choice == "shards":
            self.state, self.timer = "wind_shards", 0.7
        elif choice == "charge":
            self.aim = (player.pos - self.pos).normalize() if (player.pos - self.pos).length_squared() else self.aim
            self.state, self.timer = "wind_charge", 0.9
        else:
            self.state, self.timer = "wind_spiral", 0.9

    def _apply(self, room, player):
        if self.law == "summon":
            room.request_spawn("eye_swarm", 2)
        elif self.law == "edit":
            text, mods = random.choice(REALITY_EDITS)
            for i, (stat, op, value) in enumerate(mods):
                room.player_effects.append((stat, op, value, 8.0, text if i == 0 else ""))
        elif self.law == "geometry":
            room.begin_reshuffle(player.pos, 4)
            room.enable_gravity()
            room.notices.append(("Гравитация сместилась. Смотри на стрелки.", "gold"))

    @property
    def warning(self):
        return self.state in ("sign", "wind_shards", "wind_charge", "wind_spiral")

    # положения глаз на коллаже (относительно центра) по фазам
    EYES = ((-8, -6), (8, -6), (0, 4), (-12, 10), (12, 10), (-16, 0), (16, 0))

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        blink = int(pygame.time.get_ticks() / 90) % 2
        cx, cy = int(self.pos.x + off.x), int(self.pos.y + off.y)
        if self.phase == 3 and random.random() < 0.3:  # визуальный сбой
            cx += random.randint(-3, 3)
            cy += random.randint(-2, 2)
        img = sprites.white("chaos") if self.hurt_t > 0 or (self.state == "roar" and blink) else sprites.get("chaos", self.flip)
        surf.blit(img, img.get_rect(center=(cx, cy)))
        for ex, ey in self.EYES[:3 + 2 * (self.phase - 1)]:  # с каждой фазой глаз больше, и все смотрят на игрока
            pygame.draw.circle(surf, (255, 255, 255), (cx + ex, cy + ey), 4)
            pygame.draw.circle(surf, (210, 20, 60), (cx + ex + int(self.pupil.x * 2), cy + ey + int(self.pupil.y * 2)), 2)
        if self.state == "wind_charge" and blink:
            end = self.pos + self.aim * 300
            pygame.draw.line(surf, (255, 60, 60), (cx, cy), (end.x + off.x, end.y + off.y), 2)
        if self.state in ("wind_shards", "wind_spiral") and blink:
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), self.radius + 6, 1)
        if self.state == "sign" and self.law:  # что именно изменится — подписано заранее
            from ..ui.text import draw_text
            draw_text(surf, CHAOS_LAWS[self.law][0], (cx, cy - self.radius - 14), "gold" if blink else "white", 11, "midbottom")


def mow_hazards(player_pos, n_h=2, n_v=0):
    """Косилки по горизонтальным и вертикальным полосам (общий приём Соседа и The Shine)."""
    hs = []
    life = (ROOM_W + 60) / MOWER_SPEED + 0.1
    for y in Neighbor._lanes(int(player_pos.y - LANE / 2), n_h, ROOM_Y, ROOM_Y + ROOM_H - LANE):
        left = random.random() < 0.5
        warn = pygame.Rect(ROOM_X, y, ROOM_W, LANE)
        start = pygame.Rect(ROOM_X - 30 if left else ROOM_X + ROOM_W, y, 30, LANE)
        hs.append(Hazard(start, 2, 1.0, life, (MOWER_SPEED if left else -MOWER_SPEED, 0), warn, "mower"))
    if n_v:
        life_v = (ROOM_H + 60) / MOWER_SPEED + 0.1
        for x in Neighbor._lanes(int(player_pos.x - LANE / 2), n_v, ROOM_X, ROOM_X + ROOM_W - LANE, 60):
            up = random.random() < 0.5
            warn = pygame.Rect(x, ROOM_Y, LANE, ROOM_H)
            start = pygame.Rect(x, ROOM_Y - 30 if up else ROOM_Y + ROOM_H, LANE, 30)
            hs.append(Hazard(start, 2, 1.0, life_v, (0, MOWER_SPEED if up else -MOWER_SPEED), warn, "mower"))
    return hs


SHINE = {"name": "THE SHINE", "hp": 900, "speed": 0, "radius": 22, "contact": 1,
         "behavior": "chase", "sprite": "shine", "coin": 0}
WING_BAND = 120
WING_SPEED = 160.0
# перезарядки (мин, макс) для атак, создающих опасные зоны, — 5–10 секунд, как у остальных боссов
SHINE_CD = {"mow": (5, 10), "rain": (5, 10), "geometry": (9, 13), "spiral": (6, 10),
            "wings": (4, 7), "halos": (4, 8), "rule": (11, 15), "papers": (4, 7), "dive": (7, 11)}
RULES = (
    ("invert", "ПРАВИЛО: управление инвертировано (6 с)"),
    ("heavy", "ПРАВИЛО: ты медленнее, но стреляешь чаще (6 с)"),
    ("gravity", "ПРАВИЛО: гравитация смещается"),
)
SHINE_COMMENTS = {
    "hurt": "Ожидаемо.",
    "active": "Ты правда опять нажал эту кнопку?",
    "repeat": "Ты ведь уже видел эту атаку.",
    "phase3": "Я всё видел.",
}
ITEM_COMMENTS = {
    "shine_feather": "Моё перо. Ты правда его взял?",
    "black_halo": "Мой нимб... Тебе он не идёт.",
    "cracked_mask": "Опять прячешься за маской?",
    "old_tv": "Ты правда опять взял этот предмет?",
    "empty_photo": "Эта фотография... Положи её.",
}


class Shine(Enemy):
    """Финальный босс. Фаза 1 — Ангел, 2 — Судья (атаки прошлых боссов), 3 — Издевательство
    (временные правила, перестановка интерфейса, комментарии по событиям). Все атаки предупреждаются."""

    SPAWN_TIME = 2.0

    def __init__(self, pos, hp_scale=1.0):
        super().__init__("shine", pos, SHINE, 1.0)
        self.state, self.timer, self.phase = "idle", 2.0, 1
        self.is_boss = True
        self.last = None
        self.aim = pygame.Vector2(1, 0)
        self.spin = self.spin_tick = 0.0
        self.cd = {k: 0.0 for k in SHINE_CD}
        self.delayed = []              # отложенные события: [секунды, функция]
        self.cast_fn = None
        self.label = None
        self.counts = {}
        self.commented = set()
        self.comment_t = 0.0
        self.simple_t = 0.0            # пока > 0 — только лёгкие атаки (во время «правил»)
        self.pupil = pygame.Vector2()
        self.ctx = None
        # поведение «убегающего» босса
        self.airborne = False          # пока летит над ареной — неуязвим и безопасен
        self.rise = 0.0
        self.target = pygame.Vector2()
        self.dodge_t = self.dodge_cd = self.flip_cd = self.corner_t = 0.0
        self.dodge_vec = pygame.Vector2()
        self.circle_dir = random.choice((-1, 1))
        self.cornered = False

    @property
    def harmful(self):
        return self.spawn_t <= 0 and not self.dead and not self.airborne

    def take_damage(self, dmg, direction=None, knockback=0.0):
        if self.airborne:
            return False
        return super().take_damage(dmg, direction, knockback)

    # --- комментарии: только по событиям, с общим ограничением частоты ---
    def comment(self, key, room=None):
        room = room or (self.ctx[0] if self.ctx else None)
        if room is None or key in self.commented or self.comment_t > 0:
            return
        self.commented.add(key)
        self.comment_t = 6.0
        room.notices.append(("THE SHINE: «" + SHINE_COMMENTS[key] + "»", "gold"))

    def opening_comment(self, room, item_ids):
        for item_id, text in ITEM_COMMENTS.items():
            if item_id in item_ids:
                room.notices.append(("THE SHINE: «" + text + "»", "gold"))
                self.comment_t = 6.0
                return

    def _phase_for_hp(self):
        ratio = self.hp / self.max_hp
        return 3 if ratio <= 0.33 else 2 if ratio <= 0.66 else 1

    def update(self, dt, room, player, shoot):
        if self.spawn_t > 0:
            self.spawn_t -= dt
            return
        self._common(dt, room)
        self.ctx = (room, player, shoot)
        self.comment_t = max(0.0, self.comment_t - dt)
        self.simple_t = max(0.0, self.simple_t - dt)
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        self.flip_cd = max(0.0, self.flip_cd - dt)
        if self.dodge_t > 0:   # короткий рывок в сторону от летящего снаряда
            self.dodge_t -= dt
            self.pos += self.dodge_vec * 330 * dt
        for ev in self.delayed:
            ev[0] -= dt
        due = [ev for ev in self.delayed if ev[0] <= 0]
        self.delayed = [ev for ev in self.delayed if ev[0] > 0]
        for ev in due:
            ev[1]()
        new_phase = self._phase_for_hp()
        if new_phase > self.phase:
            self._enter_phase(new_phase, room)
        self.timer -= dt
        to_player = player.pos - self.pos
        dist = to_player.length()
        d = to_player / dist if dist > 0 else pygame.Vector2(1, 0)
        self.pupil, self.flip = d, d.x < 0
        st = self.state
        if st == "roar":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.6
        elif st == "idle":
            # держит дистанцию: отступает от игрока, кружит и подтягивается, если далеко
            speed = 70 + 12 * self.phase
            perp = pygame.Vector2(-d.y, d.x) * self.circle_dir
            if dist < 210:
                desired = -d * 0.85 + perp * 0.45
            elif dist > 300:
                desired = d * 0.6
            else:
                desired = perp * 0.5
            self.pos += desired * speed * dt
            self._try_dodge(room)
            if self.cornered:   # загнали в угол: меняем направление кружения, а затем взлетаем и падаем на игрока
                self.corner_t += dt
                if self.corner_t > 0.35 and self.flip_cd <= 0:
                    self.circle_dir, self.flip_cd = -self.circle_dir, 0.8
                if self.corner_t > 1.0:
                    self.corner_t = 0.0
                    self._atk_dive(room, player, shoot)
            else:
                self.corner_t = max(0.0, self.corner_t - dt)
            if self.timer <= 0 and self.state == "idle":
                self._choose(room, player, shoot)
        elif st == "dive_up":
            self.rise = min(46.0, self.rise + 130 * dt)
            self.target = player.pos.copy()
            if self.timer <= 0:
                self.state, self.timer = "dive_air", 1.0
        elif st == "dive_air":
            if self.timer > 0.45:   # метка следует за игроком, но в последние 0.45 с фиксируется
                self.target = player.pos.copy()
            if self.timer <= 0:
                self._land(room, shoot)
        elif st == "cast":
            if self.timer <= 0:
                fn, self.cast_fn, self.label = self.cast_fn, None, None
                if fn:
                    fn()
                self.state, self.timer = "idle", self.after
        elif st == "wind_charge":
            if self.timer > 0.35:
                self.aim = d.copy()
            if self.timer <= 0:
                self.state, self.timer, self.contact = "charge", 0.6, 2
        elif st == "charge":
            self.pos += self.aim * 235 * dt
            if self.timer <= 0 or room.confine(self.pos, self.radius):
                self.state, self.timer, self.contact = "recover", 0.9, 1
                room.shake_request = (3, 0.2)
        elif st == "recover":
            if self.timer <= 0:
                self.state, self.timer = "idle", 0.8
        elif st == "wind_spiral":
            if self.timer <= 0:
                self.state, self.timer, self.spin_tick = "spiral", 3.0, 0.0
        elif st == "spiral":
            self.spin_tick -= dt
            if self.spin_tick <= 0:
                self.spin_tick = 0.2
                self.spin += 0.45
                for arm in range(3):
                    a = self.spin + arm * math.tau / 3
                    shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 80, 1, radius=3, color=(255, 235, 150))
            if self.timer <= 0:
                self.state, self.timer = "recover", 1.0
        if not self.airborne:
            self.cornered = room.confine(self.pos, self.radius)

    def _try_dodge(self, room):
        """Иногда уворачивается от снаряда игрока, летящего прямо в него."""
        if self.dodge_cd > 0 or self.dodge_t > 0:
            return
        for pr in getattr(room, "player_shots", ()):
            if pr.dead or pr.kind == "swing" or getattr(pr, "_shine_seen", False):
                continue
            speed = pr.vel.length()
            rel = self.pos - pr.pos
            if speed <= 0 or rel.length() > 150:
                continue
            fwd = pr.vel / speed
            if rel.dot(fwd) <= 0:
                continue
            perp = pygame.Vector2(-fwd.y, fwd.x)
            lateral = rel.dot(perp)
            if abs(lateral) > self.radius + pr.radius + 6:
                continue
            pr._shine_seen = True               # решение принимается один раз для каждого снаряда
            if random.random() < 0.45:
                self.dodge_vec = perp * (1 if lateral >= 0 else -1)
                self.dodge_t = 0.22
                self.dodge_cd = random.uniform(1.6, 2.8)
                return

    def _land(self, room, shoot):
        """Приземление точно на метку: зона урона и (во 2–3 фазах) кольцо пуль."""
        self.pos = pygame.Vector2(self.target)
        self.airborne, self.rise = False, 0.0
        room.hazards.append(Hazard((self.pos.x - 42, self.pos.y - 42, 84, 84), 2, 0.0, 0.25, kind="drop"))
        room.shake_request = (5, 0.3)
        if self.phase >= 2:
            self._ring(self.pos, shoot)
        self.state, self.timer = "recover", 0.9

    def _atk_dive(self, room, player, shoot):
        self.airborne = True
        self.target = player.pos.copy()
        self.state, self.timer = "dive_up", 0.55

    def _enter_phase(self, phase, room):
        self.phase = phase
        self.sprite = "shine2" if phase == 2 else "shine3"
        self.state, self.timer, self.cast_fn, self.label = "roar", 1.6, None, None
        room.shake_request = (5, 0.6)
        if phase == 2:
            room.notices.append(("THE SHINE: «Хватит играть в ангела. Теперь я судья.»", "gold"))
        else:
            room.notices.append(("THE SHINE: «Теперь будет смешно.»", "gold"))
            room.rule_requests.append(("scramble_ui", 0))
            self.comment("phase3", room)

    # --- выбор атаки ---
    def _cast(self, label, wind, fn, after):
        self.state, self.timer, self.label, self.cast_fn, self.after = "cast", wind, label, fn, after

    def _choose(self, room, player, shoot):
        calm = not room.hazards and room.reshuffle_t is None
        options = ["light", "light", "laser"]
        if self.cd["wings"] <= 0 and calm:
            options.append("wings")
        if self.cd["halos"] <= 0:
            options.append("halos")
        if self.cd["dive"] <= 0 and self.simple_t <= 0:
            options.append("dive")
        if self.phase >= 2:
            if self.cd["papers"] <= 0:
                options.append("papers")
            options.append("charge")
            if self.simple_t <= 0:
                if self.cd["mow"] <= 0 and calm:
                    options.append("mow")
                if self.cd["rain"] <= 0 and calm:
                    options.append("rain")
                if self.cd["geometry"] <= 0 and calm:
                    options.append("geometry")
                if self.cd["spiral"] <= 0:
                    options.append("spiral")
        if self.phase == 3 and self.cd["rule"] <= 0 and self.simple_t <= 0 and calm:
            options.append("rule")
        if self.simple_t > 0:
            options = [o for o in options if o in ("light", "laser", "halos", "papers")] or ["light"]
        pool = [o for o in options if o != self.last] or options
        choice = self.last = random.choice(pool)
        self.counts[choice] = self.counts.get(choice, 0) + 1
        if self.counts[choice] == 3:
            self.comment("repeat", room)
        if choice in self.cd:
            lo, hi = SHINE_CD[choice]
            self.cd[choice] = random.uniform(lo, hi)
        getattr(self, "_atk_" + choice)(room, player, shoot)

    def _fan(self, shoot, n, step, speed, color):
        room, player, _ = self.ctx
        aim = player.pos - self.pos
        base = math.atan2(aim.y, aim.x) if aim.length_squared() else 0.0
        for i in range(n):
            a = base + (i - (n - 1) / 2) * step
            shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), speed, 1, radius=4, color=color)

    def _atk_light(self, room, player, shoot):
        n = 5 if self.phase == 1 else 7
        self._cast(None, 0.6, lambda: self._fan(shoot, n, 0.22, 115 if self.phase == 1 else 125, (255, 240, 150)), 1.0)

    def _atk_papers(self, room, player, shoot):
        def fire():
            off = random.uniform(0, math.tau)
            for i in range(10):
                a = off + i * math.tau / 10
                shoot(self.pos, pygame.Vector2(math.cos(a), math.sin(a)), 100, 1, radius=4, color=(250, 245, 225))
        self._cast(None, 0.7, fire, 1.3)

    def _atk_wings(self, room, player, shoot):
        left = random.random() < 0.5
        y = ROOM_Y if random.random() < 0.5 else ROOM_Y + ROOM_H - WING_BAND
        start = pygame.Rect(ROOM_X - 70 if left else ROOM_X + ROOM_W, y, 70, WING_BAND)
        warn = pygame.Rect(ROOM_X, y, ROOM_W, WING_BAND)
        life = (ROOM_W + 140) / WING_SPEED + 0.1
        room.hazards.append(Hazard(start, 2, 1.3, life, (WING_SPEED if left else -WING_SPEED, 0), warn, "wing"))
        self._cast("Взмах крыла", 0.9, None, 0.9)

    def _atk_laser(self, room, player, shoot):
        count = (1, 2, 3)[self.phase - 1]

        def fire():
            aim = player.pos - self.pos
            base = math.atan2(aim.y, aim.x) if aim.length_squared() else 0.0
            offs = {1: (0,), 2: (-0.7, 0.7), 3: (-0.9, 0.0, 0.9)}[count]
            for off in offs:
                room.hazards.append(Laser(self.pos, base + off, 1.0, 0.4, 12, 2))
        self._cast("Луч", 0.4, fire, 1.4)

    def _atk_halos(self, room, player, shoot):
        def fire():
            for _ in range(2 if self.phase == 1 else 3):
                a = random.uniform(0, math.tau)
                p = player.pos + pygame.Vector2(math.cos(a), math.sin(a)) * random.uniform(60, 120)
                p.x = max(ROOM_X + 20, min(ROOM_X + ROOM_W - 20, p.x))
                p.y = max(ROOM_Y + 20, min(ROOM_Y + ROOM_H - 20, p.y))
                room.hazards.append(Hazard((p.x - 22, p.y - 22, 44, 44), 1, 1.1, 0.05, kind="drop"))
                self.delayed.append([1.1, lambda p=p: self._ring(p, shoot)])
        self._cast(None, 0.4, fire, 1.2)

    def _ring(self, p, shoot):
        off = random.uniform(0, math.tau)
        for i in range(12):
            a = off + i * math.tau / 12
            shoot(p, pygame.Vector2(math.cos(a), math.sin(a)), 85, 1, radius=3, color=(255, 215, 90))

    def _atk_mow(self, room, player, shoot):
        room.hazards.extend(mow_hazards(player.pos, 2, 1 if self.phase == 2 else 2))
        self._cast(None, 1.0, None, 1.2)

    def _atk_rain(self, room, player, shoot):
        room.hazards.extend(drop_hazards(player.pos, 4, 34, 1.2))
        self._cast(None, 0.8, None, 1.2)

    def _atk_geometry(self, room, player, shoot):
        def fire():
            room.begin_reshuffle(player.pos, 4)
        self._cast("Арена меняет форму", 1.2, fire, 1.6)

    def _atk_spiral(self, room, player, shoot):
        self.state, self.timer = "wind_spiral", 0.9

    def _atk_charge(self, room, player, shoot):
        to = player.pos - self.pos
        self.aim = to.normalize() if to.length_squared() else self.aim
        self.state, self.timer = "wind_charge", 0.9

    def _atk_rule(self, room, player, shoot):
        name, text = random.choice(RULES)

        def fire():
            self.simple_t = 8.0
            if name == "invert":
                room.rule_requests.append(("invert", 6.0))
            elif name == "heavy":
                room.player_effects.append(("speed", "mul", 0.6, 6.0, text))
                room.player_effects.append(("fire_delay", "mul", 0.6, 6.0, ""))
            else:
                room.enable_gravity()
                room.notices.append((text, "red"))
            room.rule_requests.append(("scramble_ui", 0))
        self._cast(text.split(":")[1].strip().capitalize(), 1.6, fire, 1.5)

    @property
    def warning(self):
        return self.state in ("cast", "wind_charge", "wind_spiral")

    def draw(self, surf, off, sprites):
        if self.spawn_t > 0:
            super().draw(surf, off, sprites)
            return
        t = pygame.time.get_ticks()
        blink = int(t / 90) % 2
        cx, cy = int(self.pos.x + off.x), int(self.pos.y + off.y) + int(math.sin(t / 300) * 3)
        if self.airborne:   # тень на земле и метка приземления (последние 0.45 с — зафиксирована)
            shadow = pygame.Rect(0, 0, 38, 12)
            shadow.center = (cx, int(self.pos.y + off.y) + 14)
            pygame.draw.ellipse(surf, (20, 10, 30), shadow)
            locked = self.state == "dive_air" and self.timer <= 0.45
            mx, my = int(self.target.x + off.x), int(self.target.y + off.y)
            if locked or blink:
                pygame.draw.circle(surf, (255, 60, 60) if locked else (255, 200, 80), (mx, my), 42, 3 if locked else 1)
        cy -= int(self.rise)
        img = sprites.white(self.sprite) if self.hurt_t > 0 or (self.state == "roar" and blink) else sprites.get(self.sprite, self.flip)
        if self.dodge_t > 0:   # лёгкий шлейф при уворачивании
            ghost = img.copy()
            ghost.set_alpha(110)
            surf.blit(ghost, ghost.get_rect(center=(cx - int(self.dodge_vec.x * 14), cy - int(self.dodge_vec.y * 14))))
        surf.blit(img, img.get_rect(center=(cx, cy)))
        # радужка и зрачок большого глаза следят за игроком; цвет зависит от фазы
        from ..sprites import SHINE_IRIS
        ex, ey = cx + 1, cy + 4
        iris = SHINE_IRIS[self.phase]
        pygame.draw.circle(surf, iris, (ex + int(self.pupil.x * 4), ey + int(self.pupil.y * 4)), 10)
        pygame.draw.circle(surf, (20, 10, 30), (ex + int(self.pupil.x * 6), ey + int(self.pupil.y * 6)), 5)
        pygame.draw.circle(surf, (255, 255, 255), (ex + int(self.pupil.x * 6) - 2, ey + int(self.pupil.y * 6) - 2), 1)
        if self.state == "wind_charge" and blink:
            end = self.pos + self.aim * 300
            pygame.draw.line(surf, (255, 60, 60), (cx, cy), (end.x + off.x, end.y + off.y), 2)
        if self.warning and blink:
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), self.radius + 8, 1)
        if self.state == "cast" and self.label:
            from ..ui.text import draw_text
            draw_text(surf, self.label, (cx, cy - self.radius - 22), "gold" if blink else "white", 11, "midbottom")


def create_boss(boss_id, pos, hp_scale=1.0):
    if boss_id == "lumberjack":
        return Lumberjack(pos, hp_scale)
    if boss_id == "neighbor":
        return Neighbor(pos, hp_scale)
    if boss_id == "mayor":
        return Mayor(pos, hp_scale)
    if boss_id == "chaos":
        return Chaos(pos, hp_scale)
    if boss_id == "shine":
        return Shine(pos, hp_scale)
    raise ValueError(f"неизвестный босс: {boss_id}")
