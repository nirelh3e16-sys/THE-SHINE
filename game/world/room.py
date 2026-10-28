"""Комната во время игры: стены, двери, препятствия, враги, предметы."""
import math
import random

import pygame

from ..collision import push_out_of_rect
from ..entities.boss import create_boss
from ..entities.enemy import Enemy
from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H, DOOR_HALF
from .dungeon import DIRS

INTERIOR = pygame.Rect(ROOM_X, ROOM_Y, ROOM_W, ROOM_H)
CENTER = pygame.Vector2(INTERIOR.centerx, INTERIOR.centery)
DOORWAY_DEPTH = 16


_GLOW = None


def _fire_glow():
    """Оранжевое зарево по краям экрана (создаётся один раз)."""
    global _GLOW
    if _GLOW is None:
        _GLOW = pygame.Surface((480, 270), pygame.SRCALPHA)
        for i in range(10):
            pygame.draw.rect(_GLOW, (255, 90, 20, 5 + (10 - i) * 4), (i * 5, i * 3, 480 - i * 10, 270 - i * 6), 5)
    return _GLOW


def door_pos(direction):
    """Точка у двери внутри комнаты (куда ставим игрока при входе)."""
    dx, dy = DIRS[direction]
    return pygame.Vector2(CENTER.x + dx * (ROOM_W / 2 - 22), CENTER.y + dy * (ROOM_H / 2 - 22))


PATCH_PALETTES = (
    ((92, 176, 88), (84, 166, 82)),      # лес
    ((104, 106, 120), (96, 98, 112)),    # асфальт
    ((178, 132, 92), (168, 122, 84)),    # дерево
    ((60, 220, 190), (50, 205, 176)),    # кислота
    ((230, 70, 190), (215, 60, 176)),
)
MIXED_TILES = ("rock", "hedge", "crate", "barrier")
GRAVITY_DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))
GRAVITY_WORDS = ("ВПРАВО", "ВНИЗ", "ВЛЕВО", "ВВЕРХ")
GRAVITY_FORCE = 48.0


class Prop:
    """Интерактивный объект: pedestal, heal, npc, altar, apparition, portal."""

    def __init__(self, kind, pos, key, item_id=None, price=0, event_id=None):
        self.kind, self.pos, self.key = kind, pygame.Vector2(pos), key
        self.item_id, self.price, self.event_id = item_id, price, event_id
        self.used = False


class Pickup:
    def __init__(self, kind, pos, value=1):
        self.kind, self.pos, self.value = kind, pygame.Vector2(pos), value
        self.vel = pygame.Vector2(random.uniform(-40, 40), random.uniform(-40, 40))
        self.dead = False


class Room:
    def __init__(self, spec, zone, seed, data, item_ids, ns=""):
        self.spec, self.kind, self.zone = spec, spec.kind, zone
        self.ns = ns  # префикс ключей, чтобы разные зоны и дома не пересекались
        self.hazards = []
        self.arena = None            # Rect платформы (Ад: после обрушения стен комната — озеро лавы с платформой)
        self.arena_pending = None
        self.arena_warn_t = None
        self._cracks, self._veins = [], []
        self.player_shots = []     # заполняется PlayState каждый кадр (боссы смотрят на летящие снаряды)
        self.notices = []          # сообщения боссов для игрока: (текст, цвет)
        self.rule_requests = []    # временные правила боя: ("invert", секунды), ("scramble_ui", 0)
        self.player_effects = []   # (stat, op, value, секунды, текст) — применяются игроку в PlayState
        self.pending = []          # будущая расстановка препятствий (показывается заранее)
        self.reshuffle_t = None
        self.modifier = None
        self.mod_t = 0.0
        self.gravity_dir, self.gravity_next, self.gravity_warn = 0, None, 0.0
        rng = random.Random(f"{seed}:{spec.pos}")
        self.obstacles, self.stumps = [], []
        self.enemies, self.props, self.pickups = [], [], []
        self.damage_zones = []
        self.spawn_requests = []
        self.shake_request = None
        self.effects_hint = None
        self.cleared = spec.kind not in ("combat", "boss")
        self.locked = False
        self.spawned = False
        self.visited = False
        self.data = data
        self._plan = []
        self._bg = None
        self._decor = [(rng.randrange(ROOM_X, ROOM_X + ROOM_W), rng.randrange(ROOM_Y, ROOM_Y + ROOM_H),
                        rng.choice(((255, 240, 120), (255, 150, 200), (130, 240, 90)))) for _ in range(26)]
        self._patch = None
        if zone.get("patchwork"):  # комната из кусочков разных мест
            self._patch = [rng.choice(PATCH_PALETTES) for _ in range(4)]
        if zone.get("burning"):   # трещины в стенах, из которых течёт лава, и жилы на полу
            self._make_cracks(rng)
        self.door_off = {}
        for d in spec.doors:
            if zone.get("shifted_doors"):
                choices = (-128, -96, -64, 0, 64, 96, 128) if d in "NS" else (-64, -32, 0, 32, 64)
                self.door_off[d] = rng.choice(choices)
            else:
                self.door_off[d] = 0
        if zone.get("modifiers") and spec.kind == "combat":
            roll = rng.random()
            self.modifier = "gravity" if roll < 0.28 else "shift" if roll < 0.56 else None
            self.gravity_dir = rng.randrange(4)
            self.mod_t = 4.0 if self.modifier == "gravity" else 5.0
        if spec.kind in ("combat", "start", "event", "treasure", "house"):
            self._build_obstacles(rng)
        self._build_content(rng, item_ids)

    # --- генерация ---
    def _lanes(self):
        """Свободные коридоры от дверей к центру — препятствия сюда не ставятся."""
        lanes = [pygame.Rect(CENTER.x - 28, CENTER.y - 28, 56, 56)]
        for d in self.spec.doors:
            c = self.door_center(d)
            if d in "WE":
                x0, x1 = (ROOM_X, CENTER.x) if d == "W" else (CENTER.x, ROOM_X + ROOM_W)
                lanes.append(pygame.Rect(x0, c.y - 28, x1 - x0, 56))
                lanes.append(pygame.Rect(CENTER.x - 28, min(c.y, CENTER.y) - 28, 56, abs(c.y - CENTER.y) + 56))
            else:
                y0, y1 = (ROOM_Y, CENTER.y) if d == "N" else (CENTER.y, ROOM_Y + ROOM_H)
                lanes.append(pygame.Rect(c.x - 28, y0, 56, y1 - y0))
                lanes.append(pygame.Rect(min(c.x, CENTER.x) - 28, CENTER.y - 28, abs(c.x - CENTER.x) + 56, 56))
        return lanes

    def door_center(self, direction):
        """Центр проёма на границе комнаты (в Городе проёмы смещены от середины стены)."""
        off = self.door_off.get(direction, 0)
        return {"N": pygame.Vector2(CENTER.x + off, INTERIOR.top), "S": pygame.Vector2(CENTER.x + off, INTERIOR.bottom),
                "W": pygame.Vector2(INTERIOR.left, CENTER.y + off), "E": pygame.Vector2(INTERIOR.right, CENTER.y + off)}[direction]

    def door_pos(self, direction):
        """Куда ставим игрока при входе через эту дверь."""
        c = self.door_center(direction)
        dx, dy = DIRS[direction]
        return pygame.Vector2(c.x - dx * 22, c.y - dy * 22)

    def _build_obstacles(self, rng):
        want = rng.randint(2, 5) if self.kind != "start" else 2
        self.obstacles = self._gen_obstacles(rng, want)

    def _gen_obstacles(self, rng, want, avoid=()):
        """Расстановка препятствий вне коридоров от дверей к центру и вне точек avoid."""
        lanes = self._lanes()
        result = []
        tries = 0
        while len(result) < want and tries < 120:
            tries += 1
            w, h = rng.choice(((16, 16), (32, 16), (16, 32), (32, 32)))
            x = ROOM_X + 24 + rng.randrange(0, (ROOM_W - 48 - w) // 16) * 16
            y = ROOM_Y + 24 + rng.randrange(0, (ROOM_H - 48 - h) // 16) * 16
            rect = pygame.Rect(x, y, w, h)
            if any(rect.colliderect(l) for l in lanes):
                continue
            if any(rect.inflate(36, 36).colliderect(o) for o in result):
                continue
            if any(rect.inflate(60, 60).collidepoint(p) for p in avoid):
                continue
            result.append(rect)
        return result

    def _free_spot(self, rng, avoid_dist=90):
        area = self.arena or pygame.Rect(ROOM_X, ROOM_Y, ROOM_W, ROOM_H)
        for _ in range(60):
            p = pygame.Vector2(rng.uniform(area.left + 30, area.right - 30), rng.uniform(area.top + 30, area.bottom - 30))
            if any(o.inflate(24, 24).collidepoint(p) for o in self.obstacles):
                continue
            if all(p.distance_to(self.door_pos(d)) > avoid_dist for d in self.spec.doors):
                return p
        return pygame.Vector2(CENTER)

    def _build_content(self, rng, item_ids):
        pos = self.spec.pos
        if self.kind == "start" and self.zone.get("interior"):
            self.props.append(Prop("exit", (CENTER.x, ROOM_Y + ROOM_H - 20), f"{self.ns}{pos}:exit"))
        if self.kind == "combat":
            pool = [k for k, w in self.zone["enemy_pool"] for _ in range(w)]
            n = min(7, rng.randint(2, 4) + self.spec.depth // 3 + (1 if self.zone["id"] != "forest" else 0))
            self._plan = [(rng.choice(pool), self._free_spot(rng)) for _ in range(n)]
        elif self.kind == "boss":
            self._plan = [(self.zone["boss"], pygame.Vector2(CENTER.x, CENTER.y - 40))]
        elif self.kind == "treasure" and item_ids:
            if rng.random() < 0.4:  # вместо предмета — карточка (выбор одного из трёх)
                self.props.append(Prop("card", CENTER, f"{self.ns}{pos}:0"))
            else:
                self.props.append(Prop("pedestal", CENTER, f"{self.ns}{pos}:0", item_id=item_ids[0]))
        elif self.kind == "shop":
            xs = (CENTER.x - 70, CENTER.x, CENTER.x + 70)
            for i, item_id in enumerate(item_ids):
                self.props.append(Prop("pedestal", (xs[i], CENTER.y - 10), f"{self.ns}{pos}:{i}", item_id=item_id, price=6 + 2 * (i % 2) + rng.randint(0, 2)))
            self.props.append(Prop("heal", (CENTER.x, CENTER.y + 50), f"{self.ns}{pos}:h", price=3))
        elif self.kind == "house":
            self.props.append(Prop("house", (CENTER.x, ROOM_Y + 50), f"{self.ns}{pos}:house"))
        elif self.kind == "event":
            eligible = sorted(k for k, e in self.data.events.items() if self.zone["id"] in e.get("zones", [self.zone["id"]]))
            if not eligible:
                return
            ev = rng.choice(eligible)
            kind = self.data.events[ev]["kind"]
            if kind == "apparition":
                self.props.append(Prop("apparition", (ROOM_X + 40, ROOM_Y + 40), f"{self.ns}{pos}:e", event_id=ev))
            else:
                self.props.append(Prop(kind, CENTER, f"{self.ns}{pos}:e", event_id=ev))

    # --- вход, враги ---
    def enter(self, hp_scale):
        self.visited = True
        self.hazards.clear()
        if self.cleared or self.spawned:
            return
        self.spawned = True
        self.locked = True
        for kind, pos in self._plan:
            self.enemies.append(self._make(kind, pos, hp_scale))

    def _make(self, kind, pos, hp_scale):
        if kind == self.zone.get("boss"):
            return create_boss(kind, pos, 1.0)
        return Enemy(kind, pos, self.data.enemies[kind], hp_scale)

    def request_spawn(self, kind, count):
        self.spawn_requests.append((kind, count))

    def process_spawns(self, hp_scale):
        for kind, count in self.spawn_requests:
            for _ in range(count):
                self.enemies.append(self._make(kind, self._free_spot(random, 70), hp_scale))
        self.spawn_requests = []

    def add_stump(self, rect):
        self.stumps.append(rect.copy())
        self.obstacles.append(rect.copy())

    def _make_cracks(self, rng):
        for _ in range(16):
            side = rng.choice("NSWE")
            if side in "NS":
                x = rng.randrange(8, 472)
                y0, y1 = (ROOM_Y - 2, 3) if side == "N" else (ROOM_Y + ROOM_H + 2, 266)
                mid = (y0 + y1) // 2
                pts = [(x, y0), (x + rng.randint(-6, 6), mid), (x + rng.randint(-8, 8), y1)]
            else:
                y = rng.randrange(ROOM_Y + 4, ROOM_Y + ROOM_H - 4)
                x0, x1 = (ROOM_X - 2, 3) if side == "W" else (ROOM_X + ROOM_W + 2, 477)
                mid = (x0 + x1) // 2
                pts = [(x0, y), (mid, y + rng.randint(-6, 6)), (x1, y + rng.randint(-8, 8))]
            self._cracks.append(pts)
        for _ in range(7):
            x, y = rng.randrange(ROOM_X + 20, ROOM_X + ROOM_W - 20), rng.randrange(ROOM_Y + 16, ROOM_Y + ROOM_H - 16)
            pts = [(x, y)]
            for _ in range(rng.randint(3, 5)):
                x += rng.randint(-18, 18)
                y += rng.randint(-12, 12)
                pts.append((x, y))
            self._veins.append(pts)

    def set_arena(self, rect):
        """Стены обрушились: остаётся платформа rect посреди лавы."""
        self.arena = pygame.Rect(rect)
        self.arena_pending, self.arena_warn_t = None, None
        self._bg = None

    def begin_shrink(self, inset_x=24, inset_y=14, warn=1.6, min_size=(180, 110)):
        """Платформа уменьшается; будущий край заранее мигает красным."""
        if self.arena is None or self.arena_warn_t is not None:
            return False
        new = self.arena.inflate(-2 * inset_x, -2 * inset_y)
        if new.w < min_size[0] or new.h < min_size[1]:
            return False
        self.arena_pending, self.arena_warn_t = new, warn
        return True

    # --- геометрия ---
    def open_doors(self):
        return [] if self.locked else list(self.spec.doors)

    def _in_lane(self, v, center):
        return abs(v - center) <= DOOR_HALF - 4

    def clamp_player(self, pos, r):
        """Ограничение внутри комнаты; через открытые двери можно выйти в проём."""
        if self.arena is not None:
            pos.x = max(self.arena.left + r, min(self.arena.right - r, pos.x))
            pos.y = max(self.arena.top + r, min(self.arena.bottom - r, pos.y))
            return
        doors = self.open_doors()
        lo_x, hi_x = INTERIOR.left + r, INTERIOR.right - r
        lo_y, hi_y = INTERIOR.top + r, INTERIOR.bottom - r
        for d in doors:
            c = self.door_center(d)
            if d == "N" and self._in_lane(pos.x, c.x):
                lo_y = INTERIOR.top - DOORWAY_DEPTH
            elif d == "S" and self._in_lane(pos.x, c.x):
                hi_y = INTERIOR.bottom + DOORWAY_DEPTH
            elif d == "W" and self._in_lane(pos.y, c.y):
                lo_x = INTERIOR.left - DOORWAY_DEPTH
            elif d == "E" and self._in_lane(pos.y, c.y):
                hi_x = INTERIOR.right + DOORWAY_DEPTH
        pos.x = max(lo_x, min(hi_x, pos.x))
        pos.y = max(lo_y, min(hi_y, pos.y))

    def check_exit(self, pos):
        if self.arena is not None:
            return None
        for d in self.open_doors():
            if d == "N" and pos.y < INTERIOR.top - 6:
                return d
            if d == "S" and pos.y > INTERIOR.bottom + 6:
                return d
            if d == "W" and pos.x < INTERIOR.left - 6:
                return d
            if d == "E" and pos.x > INTERIOR.right + 6:
                return d
        return None

    def push_out(self, pos, r):
        moved = False
        for rect in self.obstacles:
            if push_out_of_rect(pos, r, rect):
                moved = True
        return moved

    def confine(self, pos, r):
        """Для врагов: держит внутри комнаты и вне препятствий. True при столкновении."""
        if self.arena is not None:
            x, y = pos.x, pos.y
            pos.x = max(self.arena.left + r, min(self.arena.right - r, pos.x))
            pos.y = max(self.arena.top + r, min(self.arena.bottom - r, pos.y))
            return x != pos.x or y != pos.y
        moved = self.push_out(pos, r)
        x, y = pos.x, pos.y
        pos.x = max(INTERIOR.left + r, min(INTERIOR.right - r, pos.x))
        pos.y = max(INTERIOR.top + r, min(INTERIOR.bottom - r, pos.y))
        return moved or x != pos.x or y != pos.y

    # --- отрисовка ---
    def _build_arena_bg(self):
        """Озеро лавы и базальтовая платформа посреди него."""
        bg = pygame.Surface((480, 270))
        pair = ((255, 96, 22), (236, 74, 16))
        for ty in range(0, 270, 16):
            for tx in range(0, 480, 16):
                bg.fill(pair[((tx // 16) + (ty // 16)) % 2], (tx, ty, 16, 16))
        for i in range(60):   # тёмные корки и яркие пятна
            x, y = (i * 97) % 470, (i * 61) % 262
            bg.fill((200, 50, 12) if i % 2 else (255, 170, 50), (x, y, 6, 3))
        a = self.arena
        for ty in range(a.top, a.bottom, 16):
            for tx in range(a.left, a.right, 16):
                bg.fill(self.zone["floor"][((tx // 16) + (ty // 16)) % 2], (tx, ty, min(16, a.right - tx), min(16, a.bottom - ty)))
        for x in range(a.left + 8, a.right - 8, 40):   # жилы лавы в базальте
            pygame.draw.line(bg, (255, 120, 30), (x, a.top + 6), (x + 10, a.top + 14), 1)
            pygame.draw.line(bg, (255, 120, 30), (x + 18, a.bottom - 6), (x + 8, a.bottom - 14), 1)
        pygame.draw.rect(bg, (20, 12, 20), a, 3)
        pygame.draw.rect(bg, (255, 140, 40), a.inflate(6, 6), 1)
        return bg

    def _build_bg(self):
        if self.arena is not None:
            return self._build_arena_bg()
        zone = self.zone
        bg = pygame.Surface((480, 270))
        bg.fill(zone["wall"])
        for ty in range(INTERIOR.top, INTERIOR.bottom, 16):
            for tx in range(INTERIOR.left, INTERIOR.right, 16):
                pair = zone["floor"]
                if self._patch:
                    pair = self._patch[(1 if tx >= CENTER.x else 0) + (2 if ty >= CENTER.y else 0)]
                bg.fill(pair[((tx // 16) + (ty // 16)) % 2], (tx, ty, 16, 16))
        for x, y, c in self._decor:
            bg.fill(c, (x, y, 2, 2))
        if zone.get("road"):  # дорога поперёк комнаты с разметкой
            pygame.draw.rect(bg, (84, 84, 98), (ROOM_X, int(CENTER.y) - 22, ROOM_W, 44))
            for x in range(ROOM_X + 6, ROOM_X + ROOM_W, 28):
                bg.fill((240, 210, 80), (x, int(CENTER.y) - 1, 14, 3))
        if zone.get("road_v"):  # вертикальная дорога
            pygame.draw.rect(bg, (70, 60, 100), (int(CENTER.x) - 22, ROOM_Y, 44, ROOM_H))
            for y in range(ROOM_Y + 6, ROOM_Y + ROOM_H, 28):
                bg.fill((255, 120, 220), (int(CENTER.x) - 1, y, 3, 14))
        dark = tuple(max(0, v - 28) for v in zone["wall"])
        light = tuple(min(255, v + 22) for v in zone["wall"])
        decor = zone.get("wall_decor", "trees")
        if decor == "acid":
            dark, light = (255, 70, 200), (70, 255, 210)
        if decor == "trees":
            for x in range(0, 480, 12):  # кроны по краям
                pygame.draw.circle(bg, dark, (x, 12), 9)
                pygame.draw.circle(bg, dark, (x, 258), 9)
            for y in range(0, 270, 12):
                pygame.draw.circle(bg, dark, (10, y), 9)
                pygame.draw.circle(bg, dark, (470, y), 9)
        else:  # забор / обои: вертикальные планки
            for x in range(0, 480, 8):
                for y0, y1 in ((0, ROOM_Y), (ROOM_Y + ROOM_H, 270)):
                    pygame.draw.line(bg, light if (x // 8) % 2 else dark, (x, y0), (x, y1 - 1))
            for y in range(0, 270, 8):
                for x0, x1 in ((0, ROOM_X), (ROOM_X + ROOM_W, 480)):
                    pygame.draw.line(bg, light if (y // 8) % 2 else dark, (x0, y), (x1 - 1, y))
        if self._cracks:   # трещины в базальте
            for pts in self._cracks:
                pygame.draw.lines(bg, (150, 55, 20), False, pts, 2)
                pygame.draw.lines(bg, (255, 120, 30), False, pts, 1)
            for pts in self._veins:
                pygame.draw.lines(bg, (255, 100, 25), False, pts, 1)
        pygame.draw.rect(bg, (20, 14, 30), INTERIOR.inflate(2, 2), 1)
        for d in self.spec.doors:
            dx, dy = DIRS[d]
            c = self.door_center(d)
            if dx:
                r = pygame.Rect(INTERIOR.left - 24 if dx < 0 else INTERIOR.right, c.y - DOOR_HALF, 24, DOOR_HALF * 2)
            else:
                r = pygame.Rect(c.x - DOOR_HALF, INTERIOR.top - 32 if dy < 0 else INTERIOR.bottom, DOOR_HALF * 2, 32 if dy < 0 else 30)
            bg.fill((150, 120, 80), r)
            pygame.draw.rect(bg, (20, 14, 30), r, 1)
        return bg

    def draw_floor(self, surf, off):
        if self._bg is None:
            self._bg = self._build_bg()
        surf.blit(self._bg, (off.x, off.y))
        if self.locked and self.arena is None:  # закрытые двери — доски
            for d in self.spec.doors:
                dx, dy = DIRS[d]
                c = self.door_center(d)
                if dx:
                    r = pygame.Rect(INTERIOR.left - 6 if dx < 0 else INTERIOR.right - 2, c.y - DOOR_HALF, 8, DOOR_HALF * 2)
                else:
                    r = pygame.Rect(c.x - DOOR_HALF, INTERIOR.top - 6 if dy < 0 else INTERIOR.bottom - 2, DOOR_HALF * 2, 8)
                pygame.draw.rect(surf, (110, 70, 40), r.move(off.x, off.y))
                pygame.draw.rect(surf, (30, 20, 30), r.move(off.x, off.y), 1)

    # --- динамика комнаты: гравитация и перестройка стен ---
    def begin_reshuffle(self, player_pos, want=None):
        """Новая расстановка стен показывается 1.2 с контурами, затем заменяет старую."""
        if self.reshuffle_t is not None:
            return False
        rng = random.Random(random.random())
        self.pending = self._gen_obstacles(rng, want or rng.randint(3, 5), avoid=[player_pos])
        self.reshuffle_t = 1.2
        return True

    def set_theme(self, theme):
        """Меняет оформление комнаты (например, «рай» рассыпается в финале)."""
        self.zone = {**self.zone, **theme}
        self._bg = None

    def enable_gravity(self):
        """Включает дрейф гравитации (используется боссом); направление и смена показываются стрелками."""
        if self.modifier != "gravity":
            self.modifier = "gravity"
            self.gravity_dir = random.randrange(4)
            self.gravity_next = None
            self.mod_t = 3.0

    def cancel_dynamic(self):
        self.pending, self.reshuffle_t, self.modifier = [], None, None

    def update_dynamic(self, dt, player_pos):
        if self.arena_warn_t is not None:
            self.arena_warn_t -= dt
            if self.arena_warn_t <= 0:
                self.arena, self.arena_pending, self.arena_warn_t = self.arena_pending, None, None
                self._bg = None
        if self.reshuffle_t is not None:
            self.reshuffle_t -= dt
            if self.reshuffle_t <= 0:
                self.obstacles, self.pending, self.reshuffle_t = self.pending, [], None
        if not self.modifier or not self.locked:
            return
        self.mod_t -= dt
        if self.modifier == "shift" and self.mod_t <= 0:
            if self.begin_reshuffle(player_pos):
                self.mod_t = 8.0
        elif self.modifier == "gravity":
            if self.gravity_next is None and self.mod_t <= 0:
                self.gravity_next = (self.gravity_dir + random.choice((1, 2, 3))) % 4
                self.gravity_warn = 1.5
            elif self.gravity_next is not None:
                self.gravity_warn -= dt
                if self.gravity_warn <= 0:
                    self.gravity_dir, self.gravity_next = self.gravity_next, None
                    self.mod_t = 6.5

    def drift(self):
        if self.modifier == "gravity" and self.locked:
            dx, dy = GRAVITY_DIRS[self.gravity_dir]
            return pygame.Vector2(dx, dy) * GRAVITY_FORCE
        return pygame.Vector2()

    def modifier_label(self):
        if not self.locked:
            return None
        if self.modifier == "gravity":
            text = "ГРАВИТАЦИЯ: " + GRAVITY_WORDS[self.gravity_dir]
            if self.gravity_next is not None:
                text += " -> " + GRAVITY_WORDS[self.gravity_next]
            return text
        if self.reshuffle_t is not None:
            return "СТЕНЫ ПЕРЕСТРАИВАЮТСЯ!"
        if self.modifier == "shift":
            return "СТЕНЫ НЕСТАБИЛЬНЫ"
        return None

    def draw_lava(self, surf, off, t):
        """Анимация лавы: потёки из трещин в стенах или волны на озере."""
        if not self.zone.get("burning"):
            return
        if self.arena is not None:
            a = self.arena
            for row in range(0, 270, 10):
                for col in range(0, 480, 60):
                    x = col + math.sin(t * 1.4 + row * 0.3) * 14 + (row % 20)
                    if not a.inflate(8, 8).collidepoint(x, row):
                        pygame.draw.line(surf, (255, 190, 60), (x + off.x, row + off.y), (x + 8 + off.x, row + off.y), 1)
            return
        for i, pts in enumerate(self._cracks):   # капли лавы бегут по трещинам
            p = (t * 0.35 + i * 0.173) % 1.0
            seg = 0 if p < 0.5 else 1
            f = (p * 2) % 1.0
            a, b = pts[seg], pts[seg + 1]
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            pygame.draw.circle(surf, (255, 200, 70), (int(x + off.x), int(y + off.y)), 2)
            pygame.draw.circle(surf, (255, 110, 30), (int(x + off.x), int(y + off.y)), 3, 1)

    def draw_embers(self, surf, off, t):
        """Искры, поднимающиеся вверх, и пульсирующее зарево по краям."""
        if not self.zone.get("burning"):
            return
        for i in range(18):
            x = (i * 53) % 470 + math.sin(t * 2 + i) * 8
            y = 270 - ((t * (22 + (i % 5) * 7) + i * 41) % 290)
            col = (255, 200, 80) if i % 3 == 0 else (255, 120, 40)
            surf.fill(col, (int(x + off.x), int(y + off.y), 2, 2))
        glow = _fire_glow()
        glow.set_alpha(int(120 + 70 * math.sin(t * 3)))
        surf.blit(glow, (0, 0))

    def draw_hazards(self, surf, off):
        blink = int(pygame.time.get_ticks() / 90) % 2
        if self.arena_pending is not None:   # будущий край платформы
            pygame.draw.rect(surf, (255, 70, 70) if blink else (255, 190, 70), self.arena_pending.move(off.x, off.y), 3)
        for rect in self.pending:   # будущие стены — мигающие контуры
            pygame.draw.rect(surf, (255, 70, 70) if blink else (255, 190, 70), rect.move(off.x, off.y), 2)
        if self.modifier == "gravity" and self.locked:
            warn = self.gravity_next is not None
            idx = self.gravity_next if warn else self.gravity_dir
            dx, dy = GRAVITY_DIRS[idx]
            color = ((255, 80, 80) if blink else (255, 200, 80)) if warn else (200, 215, 255)
            for gx in range(ROOM_X + 54, ROOM_X + ROOM_W, 108):
                for gy in range(ROOM_Y + 52, ROOM_Y + ROOM_H, 104):
                    cx, cy = gx + off.x, gy + off.y
                    tip = (cx + dx * 9, cy + dy * 9)
                    pygame.draw.line(surf, color, (cx - dx * 9, cy - dy * 9), tip, 2)
                    px, py = -dy, dx
                    pygame.draw.polygon(surf, color, [tip, (cx + dx * 3 + px * 5, cy + dy * 3 + py * 5),
                                                      (cx + dx * 3 - px * 5, cy + dy * 3 - py * 5)])
        for h in self.hazards:
            h.draw(surf, off)

    def draw_obstacles(self, surf, off, sprites):
        mixed = self.zone["obstacle"] == "mixed"
        rock = None if mixed else sprites.get(self.zone["obstacle"])
        for rect in self.obstacles:
            stump = any(rect == s for s in self.stumps)
            for tx in range(rect.left, rect.right, 16):
                for ty in range(rect.top, rect.bottom, 16):
                    if stump:
                        pygame.draw.rect(surf, (104, 64, 44), (tx + off.x, ty + off.y, 16, 16))
                        pygame.draw.rect(surf, (34, 24, 48), (tx + off.x, ty + off.y, 16, 16), 1)
                    else:
                        tile = sprites.get(MIXED_TILES[(tx // 16 + ty // 16) % 4]) if mixed else rock
                        surf.blit(tile, (tx + off.x, ty + off.y))
