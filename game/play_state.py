"""Основное игровое состояние: забег по зоне."""
import math
import random

import pygame

from .collision import circles_overlap, circle_rect_overlap
from .entities.player import Player
from .entities.miniboss import MINIBOSSES
from .entities.projectile import Projectile
from .systems import combat
from .systems import characters as char_logic
from .daycycle import effective_state
from .graphics_settings import NIGHT_MULT
from .systems.anchor import Anchor, FULL_CHARGE
from .systems.geyser import Geyser, Charge
from .systems.needles import Needles
from .systems.statsview import build_stat_rows
from .systems.events import apply_effects, can_choose
from .systems.morality import Morality, TESTIMONIES
from .ui.dialogue import DialogueBox
from .ui.hud import Notifications, draw_hud
from .ui.menus import Menu, draw_journal
from .ui.text import draw_text
from .world.dungeon import Dungeon, OPP
from .world.room import Room, Prop, Pickup, CENTER
from .world.zones import ZONES, ZONE_ORDER, SIDE_ZONES, zone_room_count
from .ui.text import draw_text as _draw_text
from .settings import GAME_W, GAME_H, ROOM_X, ROOM_Y, ROOM_W, ROOM_H

BURGER_BUFFS = (
    ("damage", "add", 1.5, "урон +1.5"), ("fire_delay", "mul", 0.6, "быстрая стрельба"),
    ("speed", "mul", 1.35, "скорость"), ("luck", "add", 3.0, "удача"),
)
FEATHER_LINES = ("Ангел: «Красивое перо. Не потеряй».", "Ангел: «Я наблюдаю».", "Ангел: «Ты ведь уже видел эту атаку».")


class PlayState:
    def __init__(self, game, snapshot=None):
        self.game = game
        self.cfg = game.cfg
        self.db = game.data.items
        if snapshot is not None and "zone" not in snapshot:
            raise ValueError("сохранение старого формата")
        self.seed = snapshot["seed"] if snapshot else (
            self.cfg["seed"] if self.cfg["seed"] is not None else random.randrange(1 << 30))
        char_id = snapshot.get("char", char_logic.DEFAULT_ID) if snapshot else game.selected_char
        self.char = game.characters.get(char_id) or game.characters[char_logic.DEFAULT_ID]
        self.player = Player(self.db, self.char)
        self.morality = Morality(self.seed, game.save.data["testimonies"])
        self.notes = Notifications()
        self.pshots, self.eshots = [], []
        self.pickups_total = 0
        self.dialogue = None
        self.after_dialogue = None
        self.paused = False
        self.pause_menu = None
        self.overlay = False
        self.tab = 0
        self.trans = None
        self.dying = 0.0
        self.room_hit = False
        self.photo_count = 0
        self.rooms_cleared = 0
        self.slow_t = self.freeze_t = 0.0
        self.soldier_t, self.clock_t = 1.4, 14.0
        self.thorn_t = 1.0         # Колючка-пушка: время до следующего выстрела
        self.needle_hint = False   # подсказка про иголки Живой ели показана
        self.balancer = Geyser.balancer()      # Душа: Балансатор (гейзер душ после зарядки)
        self.balancer_charge = Charge()
        self.scream = Geyser.scream()          # Душа: Крик (активный предмет, гигантский гейзер)
        self.sky_hint = False      # подсказка про «спящих» небесных стражей показана
        self.burger_t, self.feather_t = random.uniform(15, 25), random.uniform(30, 50)
        if not snapshot:  # стартовые предметы персонажа (при продолжении они уже есть в сохранении)
            for item_id in self.char["start_items"]:
                self.give_item(item_id, silent=True)
            self.player.hp = self.player.max_hp
        self.cutscene = False
        self.chain = []
        self.on_dialogue_end = None
        self.inverted_t = 0.0      # правило финального босса: инвертированное управление
        self.hud_layout = 0        # правило финального босса: перестановка элементов интерфейса
        self.secret_ready = False
        self.cheated = False       # тест-меню использовалось: результаты забега не сохраняются
        self.debug = None
        self.day_clock = float(snapshot.get("day", 0.0)) if snapshot else 0.0   # визуальное время суток: забег начинается на рассвете
        self.pending_cutscene = False   # Ад: сцена с Бесом начнётся, когда игрок дойдёт до центра комнаты
        self.chain_end = None
        self.grenades, self.blasts = [], []
        self.anchor = Anchor()
        self.imp = None            # компактный бес (спутник)
        self.stats_open = False    # меню статистики персонажа (F4 + 2)
        self.cards = None          # меню выбора карточки: {"options": [...], "sel": 0, "then": fn}
        self.stack = []  # внешние уровни, пока игрок внутри дома
        self._setup_zone(snapshot["zone"] if snapshot else 0, snapshot.get("zone_pool") if snapshot else None)
        if snapshot:
            self._restore(snapshot)
        self.room = self.get_room(self.dungeon.pos)
        self.player.pos = pygame.Vector2(CENTER)
        self.player.recompute()
        if self.zone.get("arena"):
            self._start_fight()
        else:
            self._enter_room()
        if not snapshot:
            self.notes.push("ЛЕС. Двигайся: WASD, стреляй: мышь, уклонение: Space", "gold", 5)

    def _setup_zone(self, index, pool=None):
        """Создаёт раскладку зоны. Пул предметов фиксируется при входе в зону (нужно для сохранений)."""
        self.zone_index = index
        self.zone = ZONES[ZONE_ORDER[index]]
        self.main_zone = self.zone
        self.zone_seed = f"{self.seed}:{self.zone['id']}"
        self.zone_pool = list(pool) if pool is not None else sorted(
            i for i, d in self.db.items.items() if i not in self.player.inv.items and not d.drop_only)
        n = zone_room_count(self.zone["id"], self.cfg)
        self.dungeon = Dungeon(self.zone_seed, n, self.zone_pool, extra_kinds=self.zone.get("extra_kinds", ()),
                               arena=bool(self.zone.get("arena")),
                               mini_kind="miniboss" if self.zone.get("miniboss") else None)
        self.rooms = {}
        self.taken = set()
        self.boss_dead = False
        self.stack = []
        self.ctx_seed = self.zone_seed
        self.ns = f"{self.zone['id']}:"

    # --- вспомогательное ---
    def hp_scale(self):
        return (1.0 + 0.08 * self.dungeon.spec().depth) * self.zone.get("hp_mult", 1.0)

    def get_room(self, pos):
        if pos not in self.rooms:
            spec = self.dungeon.specs[pos]
            room = Room(spec, self.zone, self.ctx_seed, self.game.data, self.dungeon.item_for_room.get(pos, []), self.ns)
            room.props = [p for p in room.props if p.key not in self.taken]
            self.rooms[pos] = room
        return self.rooms[pos]

    def ui_glitch(self):
        """Фаза 3 Хаоса: часть интерфейса пропадает, звук и картинка дают сбой."""
        boss = self.boss() or self.miniboss()
        return bool(boss is not None and getattr(boss, "ui_glitch", False))

    def boss(self):
        for e in self.room.enemies:
            if getattr(e, "is_boss", False) and not e.dead:
                return e
        return None

    def miniboss(self):
        for e in self.room.enemies:
            if getattr(e, "is_miniboss", False) and not e.dead:
                return e
        return None

    @property
    def active_cooldown(self):
        aid = self.player.inv.active_id
        return self.db.items[aid].active.get("cooldown", 1.0) if aid else 1.0

    # --- ctx для событий ---
    @property
    def sfx(self):
        return self.game.audio.play

    def notify(self, text, color="white"):
        self.notes.push(text, color)

    def change_hp(self, v):
        if v > 0:
            self.player.heal(v)
        else:
            self.player.hp = max(1, self.player.hp + v)
            self.game.effects.flash((255, 60, 60), 0.2)

    def change_max_hp(self, v):
        self.add_run_mod("max_hp", "add", v)

    def add_coins(self, v):
        self.player.coins = max(0, self.player.coins + v)

    def give_random_item(self):
        pool = [i for i in self.zone_pool if i not in self.player.inv.items] or \
               [i for i in self.db.regular_ids() if i not in self.player.inv.items]
        if not pool:
            self.add_coins(5)
            self.notes.push("Предметов больше нет. Только монеты.", "gold")
            return
        self.give_item(random.choice(pool))

    def spawn(self, kind, count):
        """Последствие выбора: комната снова запирается, появляются враги."""
        self.room.cleared, self.room.locked = False, True
        self.room.request_spawn(kind, count)

    def add_run_mod(self, stat, op, value):
        self.player.run_mods.append((stat, op, value))
        self.player.recompute()

    # --- предметы ---
    def give_item(self, item_id, silent=False):
        item = self.db.items[item_id]
        before = {c["id"] for c in self.db.active_combos(self.player.inv.items)}
        if not self.player.inv.add(item):
            return
        self.player.recompute()
        seen = self.game.save.data["seen_items"]
        if item_id not in seen:
            seen.append(item_id)
        if silent:
            return
        self.sfx("pickup")
        self.game.effects.flash(item.color, 0.25)
        self.notes.push(f"{item.name}: {item.desc}", "gold", 4.5)
        for c in self.db.active_combos(self.player.inv.items):
            if c["id"] not in before:
                self.notes.push(f"КОМБО «{c['name']}»: {c['desc']}", "green", 5)
                self.sfx("story")

    def use_active(self):
        inv = self.player.inv
        if not inv.can_use_active():
            return
        item = self.db.items[inv.active_id]
        kind, p, fx = item.active["type"], self.player, self.game.effects
        if kind == "nuke":
            for e in self.room.enemies:
                if not e.dead:
                    e.take_damage(item.active["damage"], pygame.Vector2(e.pos - p.pos), 200)
            self.eshots.clear()
            fx.flash((255, 200, 120), 0.5)
            fx.shake(5, 0.5)
            self.sfx("nuke")
            if "frozen_blast" in p.flags:
                self.freeze_t = 5.0
            inv.start_cooldown(item.active["cooldown"])
        elif kind == "grenade":
            self._throw_grenade(item.active)
            inv.start_cooldown(item.active["cooldown"])
        elif kind == "medkit":
            if p.hp >= p.max_hp:
                self.notes.push("Здоровье и так полное", "grey")
                return
            p.hp = p.max_hp
            fx.flash((120, 255, 150), 0.3)
            fx.burst(p.pos, (120, 255, 150), 18, 90, 0.6, 3)
            self.sfx("pickup")
            inv.start_kill_recharge(item.active["kills"])
            self.notes.push(f"Аптечка: здоровье восстановлено. Перезарядка — {item.active['kills']} убийств.", "green", 3)
        elif kind == "scream":   # Душа: гигантский гейзер душ с отдачей
            self.scream.start((p.pos.x, p.pos.y), (p.aim.x, p.aim.y))
            fx.flash((255, 255, 255), 0.3)
            fx.shake(6, 0.4)
            self.sfx("nuke")
            inv.start_cooldown(item.active["cooldown"])
        elif kind == "phone":
            if not self._teleport_random():
                self.notes.push("Телефон не ловит сеть: некуда телепортироваться.", "grey")
                return
            inv.start_cooldown(item.active["cooldown"])
        self._boss_comment("active")

    # --- граната ---
    def _throw_grenade(self, active):
        p = self.player
        target = self.game.display.to_game(pygame.mouse.get_pos())
        area = self.room.arena or pygame.Rect(ROOM_X, ROOM_Y, ROOM_W, ROOM_H)
        target.x = max(area.left, min(area.right, target.x))
        target.y = max(area.top, min(area.bottom, target.y))
        offset = target - p.pos
        if offset.length() > 260:   # ограничение дальности броска
            target = p.pos + offset.normalize() * 260
        dist = p.pos.distance_to(target)
        self.grenades.append({"start": p.pos.copy(), "target": pygame.Vector2(target), "t": 0.0,
                              "dur": max(0.35, dist / 260), "damage": active["damage"], "radius": active["radius"]})
        self.sfx("shoot")

    def _update_grenades(self, dt):
        for g in self.grenades:
            g["t"] += dt
            if g["t"] >= g["dur"]:
                self._explode_grenade(g)
                g["done"] = True
        self.grenades = [g for g in self.grenades if not g.get("done")]
        for b in self.blasts:
            b["t"] += dt
        self.blasts = [b for b in self.blasts if b["t"] < 0.4]

    def _explode_grenade(self, g):
        """Взрыв диаметром 5 блоков: все враги внутри получают 50 урона."""
        center, radius, fx = g["target"], g["radius"], self.game.effects
        for e in self.room.enemies:
            if not e.dead and e.pos.distance_to(center) <= radius + e.radius:
                e.take_damage(g["damage"], e.pos - center, 260)
        self.eshots = [s for s in self.eshots if s.pos.distance_to(center) > radius]
        fx.burst(center, (255, 200, 80), 28, 170, 0.6, 3)
        fx.burst(center, (255, 90, 30), 18, 120, 0.5, 3)
        fx.shake(4, 0.3)
        fx.flash((255, 220, 150), 0.15)
        self.sfx("nuke")
        self.blasts.append({"pos": pygame.Vector2(center), "t": 0.0, "r": radius})

    # --- сломанный телефон ---
    def _teleport_random(self):
        """Телепорт в случайную комнату локации (кроме текущей и комнаты босса)."""
        options = [pos for pos, spec in self.dungeon.specs.items() if pos != self.dungeon.pos and spec.kind != "boss"]
        if not options:
            return False
        pos = random.choice(options)
        self.dungeon.visited.add(pos)
        self.dungeon.pos = pos
        self._swap_room(pos)
        self.game.effects.flash((180, 220, 255), 0.25)
        self.sfx("door")
        self.notes.push("Телефон телепортировал тебя в другую комнату.", "blue", 2.5)
        return True

    # --- якорь ---
    def _update_anchor(self, dt, mouse_down):
        p, a, room, fx = self.player, self.anchor, self.room, self.game.effects
        ppos = (p.pos.x, p.pos.y)
        if mouse_down and not a.flying and a.cooldown <= 0 and p.dodge_t <= 0:
            a.holding(dt, ppos)
        elif a.state == "orbit":
            a.release((p.aim.x, p.aim.y))   # отпустил — якорь летит к курсору
        a.step(dt, ppos)
        apos = pygame.Vector2(a.pos)
        for e in room.enemies:
            if e.dead or e.spawn_t > 0:
                continue
            e._anchor_cd = max(0.0, getattr(e, "_anchor_cd", 0.0) - dt)
            if apos.distance_to(e.pos) > 9 + e.radius:
                continue
            if a.state == "orbit":
                if e._anchor_cd <= 0 and e.take_damage(p.stats["damage"] * 0.4, e.pos - apos, 170):
                    e._anchor_cd = 0.45
                    fx.burst(e.pos, (255, 255, 200), 4, 70, 0.25)
                    self.sfx("hit")
            elif a.flying and getattr(e, "_anchor_pass", -1) != a.pass_id:
                e._anchor_pass = a.pass_id
                if e.take_damage(p.stats["damage"] * 4.0, pygame.Vector2(a.dir), 400):   # колоссальный урон
                    fx.burst(e.pos, (255, 255, 255), 10, 130, 0.4, 3)
                    fx.shake(2, 0.15)
                    self.sfx("hit")

    # --- Душа: Балансатор и Крик ---
    def _update_balancer(self, dt, mouse_down):
        """Зажми атаку на 3 секунды и отпусти: гейзер душ, который следит за курсором. Недозаряд пропадает."""
        p, charge, geyser = self.player, self.balancer_charge, self.balancer
        if geyser.active:
            charge.cancel()
            return
        if mouse_down and p.dodge_t <= 0:
            charge.hold(dt)
        elif charge.value > 0 and charge.release():
            geyser.start((p.pos.x, p.pos.y), (p.aim.x, p.aim.y))
            self.game.effects.shake(2, 0.2)
            self.sfx("nuke")

    def _update_geysers(self, dt):
        """Двигает гейзеры, наносит урон каждые 0.1 с всем, кто в луче, и отталкивает игрока (отдача Крика)."""
        p, room, fx = self.player, self.room, self.game.effects
        origin, aim = (p.pos.x, p.pos.y), (p.aim.x, p.aim.y)
        for g in (self.balancer, self.scream):
            was_active = g.active
            ticks = g.update(dt, origin, aim)
            if not was_active:
                continue
            if ticks:
                # у Шайна (финал Бога) урон 100, поэтому гейзер душ в его теле слабее, чтобы бой не кончался за секунды
                dmg = p.stats["damage"] * g.damage_mult * (0.06 if p.form else 1.0) * ticks
                for e in room.enemies:
                    if e.harmful and g.hits((e.pos.x, e.pos.y), e.radius) and e.take_damage(dmg, pygame.Vector2(g.direction), 30):
                        fx.burst(e.pos, (215, 232, 255), 2, 60, 0.25)
                if g is self.scream:   # Крик сметает вражеские снаряды
                    for pr in self.eshots:
                        if g.hits((pr.pos.x, pr.pos.y), pr.radius):
                            pr.dead = True
            if g.recoil:
                p.knock = pygame.Vector2(g.recoil_vector())
                fx.shake(2, 0.05)

    def _draw_geyser(self, surf, off, g):
        if not g.active:
            return
        ox, oy = g.origin
        ex, ey = g.end()
        a, b = (ox + off.x, oy + off.y), (ex + off.x, ey + off.y)
        fade = min(1.0, g.left / 0.25)
        w = max(2, int(g.width * fade))
        pygame.draw.line(surf, (150, 185, 255), a, b, w + 6)
        pygame.draw.line(surf, (222, 236, 255), a, b, w)
        pygame.draw.line(surf, (255, 255, 255), a, b, max(2, int(w * 0.45)))
        t = pygame.time.get_ticks() / 1000
        d = pygame.Vector2(g.direction)
        n = pygame.Vector2(-d.y, d.x)
        for i in range(18):   # души, текущие вдоль луча
            dist = ((t * 190 + i * g.reach / 18) % g.reach)
            sway = math.sin(t * 7 + i * 1.9) * g.width * 0.35
            c = pygame.Vector2(a) + d * dist + n * sway
            pygame.draw.circle(surf, (255, 255, 255), (int(c.x), int(c.y)), 3 if g.width > 20 else 2)
            pygame.draw.circle(surf, (20, 20, 40), (int(c.x) - 1, int(c.y)), 1)

    def _draw_balancer_charge(self, surf, off):
        """Кольцо зарядки вокруг Души; когда заряд полный — виден прицельный луч до конца дальности."""
        p, charge = self.player, self.balancer_charge
        if charge.value <= 0 or self.balancer.active:
            return
        c = (int(p.pos.x + off.x), int(p.pos.y + off.y))
        rect = pygame.Rect(c[0] - 13, c[1] - 13, 26, 26)
        pygame.draw.circle(surf, (60, 70, 110), c, 13, 1)
        if charge.ready:
            blink = (pygame.time.get_ticks() // 100) % 2
            pygame.draw.circle(surf, (255, 255, 255) if blink else (190, 215, 255), c, 15, 2)
            end = p.pos + p.aim * self.balancer.reach
            pygame.draw.line(surf, (190, 215, 255), c, (end.x + off.x, end.y + off.y), 1)
        else:
            pygame.draw.arc(surf, (200, 225, 255), rect, math.pi / 2, math.pi / 2 + math.tau * charge.fraction, 3)

    # --- компактный бес ---
    def _update_imp(self, dt):
        p, room, fx = self.player, self.room, self.game.effects
        if "imp" not in p.flags:
            self.imp = None
            return
        if self.imp is None:
            self.imp = {"pos": p.pos + pygame.Vector2(-16, -20), "aggro": 0.0, "hit_cd": 0.0, "flip": False}
        imp = self.imp
        imp["hit_cd"] = max(0.0, imp["hit_cd"] - dt)
        imp["aggro"] = max(0.0, imp["aggro"] - dt)
        targets = [e for e in room.enemies if e.harmful]
        if imp["aggro"] > 0 and targets:
            tgt = min(targets, key=lambda e: e.pos.distance_to(imp["pos"]))
            d = tgt.pos - imp["pos"]
            dist = d.length()
            if dist > 1:
                imp["pos"] += d / dist * 170 * dt
                imp["flip"] = d.x < 0
            if dist <= tgt.radius + 9 and imp["hit_cd"] <= 0 and tgt.take_damage(max(3.0, p.stats["damage"]), d, 200):
                imp["hit_cd"] = 0.55
                fx.burst(tgt.pos, (255, 150, 60), 6, 90, 0.3)
                self.sfx("hit")
        else:
            t = pygame.time.get_ticks() / 1000
            target = p.pos + pygame.Vector2(-16 + math.sin(t * 3) * 3, -20 + math.cos(t * 4) * 3)
            imp["pos"] += (target - imp["pos"]) * min(1.0, 6 * dt)
            imp["flip"] = p.aim.x < 0

    def _imp_on_hurt(self):
        p = self.player
        if "imp" not in p.flags or p.hp <= 0:
            return
        if p.hp < p.max_hp / 2:   # здоровья меньше половины: бес бьёт игрока и улетает навсегда
            p.hp = max(1, p.hp - 1)
            if "compact_imp" in p.inv.items:
                p.inv.items.remove("compact_imp")
            p.recompute()
            self.imp = None
            self.notes.push("Компактный бес ударил тебя и улетел!", "red", 4)
            self.game.effects.flash((255, 80, 60), 0.25)
        else:
            if self.imp is None:
                self.imp = {"pos": p.pos + pygame.Vector2(-16, -20), "aggro": 0.0, "hit_cd": 0.0, "flip": False}
            self.imp["aggro"] = 8.0
            self.notes.push("Компактный бес разозлился!", "gold", 2)

    # --- сохранение ---
    def _outer(self):
        """Основной уровень зоны (если игрок в доме — тот, из которого он вошёл)."""
        if self.stack:
            return self.stack[0]["dungeon"], self.stack[0]["rooms"]
        return self.dungeon, self.rooms

    def snapshot(self):
        p = self.player
        dungeon, rooms = self._outer()
        return {
            "seed": self.seed, "char": self.char["id"], "zone": self.zone_index, "day": round(self.day_clock, 1), "zone_pool": list(self.zone_pool),
            "pos": list(dungeon.pos), "visited": [list(v) for v in dungeon.visited],
            "cleared": [list(pos) for pos, r in rooms.items() if r.cleared and r.kind in ("combat", "boss", "miniboss")],
            "taken": sorted(self.taken), "hp": p.hp, "coins": p.coins, "items": list(p.inv.items),
            "run_mods": [list(m) for m in p.run_mods], "sins": self.morality.run_sins,
            "testimonies": self.morality.run_testimonies, "boss_dead": self.boss_dead,
            "photo": self.photo_count, "rooms_cleared": self.rooms_cleared,
        }

    def save_snapshot(self):
        if self.cheated or self.player.form:   # во время финала с Шайном забег не сохраняется
            return
        self.game.save.data["current_run"] = self.snapshot()
        self.game.save.write()

    def _restore(self, s):
        self.dungeon.pos = tuple(s["pos"])
        self.dungeon.visited = {tuple(v) for v in s["visited"]}
        self.taken = set(s.get("taken", []))
        for it in s["items"]:
            if it in self.db.items:
                self.give_item(it, silent=True)
        self.player.run_mods = [tuple(m) for m in s.get("run_mods", [])]
        self.player.recompute()
        self.player.hp = max(1, min(int(s["hp"]), self.player.max_hp))
        self.player.coins = int(s.get("coins", 0))
        for k, v in s.get("sins", {}).items():
            if k in self.morality.run_sins:
                self.morality.run_sins[k] = v
        self.morality.run_testimonies = [t for t in s.get("testimonies", []) if t in TESTIMONIES]
        self.photo_count = s.get("photo", 0)
        self.rooms_cleared = s.get("rooms_cleared", 0)
        self.boss_dead = s.get("boss_dead", False)
        for pos in s.get("cleared", []):
            room = self.get_room(tuple(pos))
            room.cleared, room.locked, room.spawned = True, False, True
            if room.kind == "boss" and self.boss_dead:
                self._boss_rewards(room, silent=True)
            elif room.kind == "miniboss":
                self._miniboss_reward(room)

    def finish_run(self, won):
        data = self.game.save.data
        if self.cheated:  # тест-режим: ничего не засчитываем
            data["current_run"] = None
            self.game.save.write()
            return
        data["runs"] += 1
        data["wins"] += 1 if won else 0
        data["best_rooms_cleared"] = max(data["best_rooms_cleared"], self.rooms_cleared)
        data["testimonies"] = self.morality.all_testimonies()
        for k, v in self.morality.run_sins.items():
            data["legacy_sins"][k] = data["legacy_sins"].get(k, 0) + v
        data["current_run"] = None
        self.game.save.write()

    # --- события ввода ---
    def toggle_stats(self):
        self.stats_open = not self.stats_open

    def _draw_stats(self, surf):
        veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        veil.fill((8, 4, 20, 225))
        surf.blit(veil, (0, 0))
        _draw_text(surf, "СТАТИСТИКА ПЕРСОНАЖА", (GAME_W // 2, 8), "gold", 14, "midtop")
        y = 32
        for label, value in build_stat_rows(self.player, self.rooms_cleared):
            _draw_text(surf, label, (60, y), "grey", 11)
            _draw_text(surf, value, (GAME_W - 60, y), "white", 11, "topright")
            y += 15
        _draw_text(surf, "Esc или F4 + 2 — закрыть", (GAME_W // 2, GAME_H - 6), "grey", 9, "midbottom")

    def handle_event(self, event):
        if self.stats_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stats_open = False
            return
        if self.debug is not None:
            self._debug_event(event)
            return
        if self.cards is not None:
            self._cards_event(event)
            return
        if self.dialogue:
            self.dialogue.handle_event(event)
            return
        if self.paused:
            self.pause_menu.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.paused = False
            return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if self.overlay:
            if k in (pygame.K_TAB, pygame.K_ESCAPE):
                self.overlay = False
            elif k in (pygame.K_q, pygame.K_e, pygame.K_LEFT, pygame.K_RIGHT):
                self.tab = 1 - self.tab
            return
        if k == pygame.K_ESCAPE:
            self.open_pause()
        elif k == pygame.K_TAB:
            self.overlay = True
        elif k in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
            if self.trans is None and self.player.start_dodge():
                self.sfx("dodge")
        elif k == pygame.K_q:
            self.use_active()
        elif k == pygame.K_e:
            self.interact()

    def open_pause(self):
        self.paused = True
        self.pause_menu = Menu("ПАУЗА", [
            ("Продолжить", lambda: setattr(self, "paused", False)),
            ("Графика", lambda: self.game.go_graphics(back_state=self)),
            ("Сохранить и в меню", self._save_quit),
            ("В меню без сохранения", self.game.go_menu),
        ])

    def on_focus_lost(self):
        if not self.paused and not self.dialogue and self.dying <= 0:
            self.open_pause()

    def _save_quit(self):
        self.save_snapshot()
        self.game.go_menu()

    def nearest_prop(self, dist=24):
        best, bd = None, dist
        for p in self.room.props:
            d = p.pos.distance_to(self.player.pos)
            if d < bd and p.kind != "apparition":
                best, bd = p, d
        return best

    def interact(self):
        prop = self.nearest_prop()
        if prop is None:
            return
        if prop.kind == "pedestal":
            if prop.price > self.player.coins:
                self.notes.push("Не хватает монет", "red")
                return
            self.player.coins -= prop.price
            self.room.props.remove(prop)
            self.taken.add(prop.key)
            if prop.price:
                self.sfx("buy")
            self.give_item(prop.item_id)
        elif prop.kind == "card":
            self.room.props.remove(prop)
            self.taken.add(prop.key)
            self.open_cards()
        elif prop.kind == "heal":
            if prop.price > self.player.coins:
                self.notes.push("Не хватает монет", "red")
            elif self.player.hp >= self.player.max_hp:
                self.notes.push("Здоровье и так полное", "grey")
            else:
                self.player.coins -= prop.price
                self.player.heal(2)
                self.sfx("buy")
                self.room.props.remove(prop)
                self.taken.add(prop.key)
        elif prop.kind == "house":
            self.enter_house(prop)
        elif prop.kind == "exit":
            self.leave_house()
        elif prop.kind in ("npc", "altar"):
            if prop.used:
                self.notes.push("Ему больше нечего сказать.", "grey")
                return
            ev = self.game.data.events[prop.event_id]
            labels = [c["label"] for c in ev["choices"]]
            enabled = [can_choose(c, self.player.coins) for c in ev["choices"]]
            self.dialogue = DialogueBox(ev["name"], ev["text"], labels, enabled)
            self.after_dialogue = lambda choice, ev=ev, prop=prop: self._resolve_event(ev, prop, choice)
        elif prop.kind == "gates":
            self._finish_ending()
        elif prop.kind == "rift":
            self.advance_zone()   # прыжок в разлом — новая локация Ад
        elif prop.kind == "sky_portal":
            self.advance_zone("heaven")   # забег не заканчивается: портал ведёт на Небеса
        elif prop.kind == "portal":
            if self.zone.get("ends_run"):   # портал после Беса: злая концовка (она открывает Небеса)
                self.finish_run(True)
                self.game.go_ending(self, self.zone["ends_run"])
            elif self.zone_index + 1 < len(ZONE_ORDER) and ZONE_ORDER[self.zone_index + 1] not in SIDE_ZONES:
                self.advance_zone()
            else:
                self.finish_run(True)
                self.game.go_victory(self)

    # --- зоны и дома ---
    def advance_zone(self, zone_id=None):
        """Переход в следующую зону (или в указанную: Ад — из разлома, Небеса — из небесного портала)."""
        self.eshots.clear()
        self.pshots.clear()
        self._setup_zone(ZONE_ORDER.index(zone_id) if zone_id else self.zone_index + 1)
        self.player.heal(2)
        self.room = self.get_room(self.dungeon.pos)
        self.player.pos = pygame.Vector2(CENTER)
        self.game.effects.flash((255, 255, 255), 0.6)
        self.sfx("story")
        self.notes.push(f"{self.zone['name']}", "gold", 4)
        self.open_cards(then=self._zone_intro)

    def _zone_intro(self):
        if self.zone.get("arena"):
            self._start_betrayal()
            return
        self._enter_room()
        self.save_snapshot()

    # --- карточки: выбор одного из трёх случайных предметов (видны только название и значок) ---
    def open_cards(self, then=None):
        options = self.db.card_options(self.player.inv.items, random)
        if not options:
            self.add_coins(5)
            self.notes.push("Все предметы уже у тебя. Вместо карточки — монеты.", "gold", 3)
            if then:
                then()
            return
        self.cards = {"options": options, "sel": 0, "then": then}
        self.sfx("story")

    def _card_rects(self):
        n = len(self.cards["options"])
        w, h, gap = 108, 150, 14
        x0 = (GAME_W - (n * w + (n - 1) * gap)) // 2
        return [pygame.Rect(x0 + i * (w + gap), 62, w, h) for i in range(n)]

    def _cards_event(self, event):
        c = self.cards
        n = len(c["options"])
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_LEFT, pygame.K_a):
                c["sel"] = (c["sel"] - 1) % n
            elif k in (pygame.K_RIGHT, pygame.K_d):
                c["sel"] = (c["sel"] + 1) % n
            elif pygame.K_1 <= k < pygame.K_1 + n:
                c["sel"] = k - pygame.K_1
                self._pick_card()
            elif k in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
                self._pick_card()
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and hasattr(event, "pos_game"):
            for i, rect in enumerate(self._card_rects()):
                if rect.collidepoint(event.pos_game):
                    c["sel"] = i
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._pick_card()
                    break

    def _pick_card(self):
        c, self.cards = self.cards, None
        self.give_item(c["options"][c["sel"]])
        if c["then"]:
            c["then"]()

    def _draw_cards(self, surf):
        veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        veil.fill((8, 4, 20, 215))
        surf.blit(veil, (0, 0))
        _draw_text(surf, "ВЫБЕРИ КАРТОЧКУ", (GAME_W // 2, 24), "gold", 16, "midtop")
        _draw_text(surf, "Видно только название. Что внутри — узнаешь потом.", (GAME_W // 2, 46), "grey", 10, "midtop")
        from .ui.text import wrap
        for i, rect in enumerate(self._card_rects()):
            sel = i == self.cards["sel"]
            r = rect.move(0, -8 if sel else 0)
            pygame.draw.rect(surf, (36, 24, 60) if sel else (26, 18, 44), r, border_radius=6)
            pygame.draw.rect(surf, (255, 215, 90) if sel else (110, 90, 150), r, 2, border_radius=6)
            icon = self.game.sprites.icon(self.cards["options"][i])
            big = pygame.transform.scale(icon, (icon.get_width() * 4, icon.get_height() * 4))
            surf.blit(big, big.get_rect(center=(r.centerx, r.y + 52)))
            item = self.db.items[self.cards["options"][i]]
            for j, line in enumerate(wrap(item.name, r.width - 12, 10)[:3]):
                _draw_text(surf, line, (r.centerx, r.y + 94 + j * 13), "white" if sel else "grey", 10, "midtop")
            _draw_text(surf, str(i + 1), (r.x + 6, r.y + 4), "gold", 10)
        _draw_text(surf, "←/→ или мышь — выбор, Enter / клик — взять", (GAME_W // 2, GAME_H - 8), "grey", 9, "midbottom")

    # --- финал: предательство, бой, концовки ---
    BETRAYAL = (
        ("THE SHINE", "Ты справился. Хаос побеждён. Я наблюдал за каждым твоим шагом.", None),
        ("THE SHINE", "Врата рая перед тобой. Иди. Ты заслужил... в каком-то смысле.", None),
        ("THE SHINE", "...", None),
        ("THE SHINE", "Ха. Ха-ха-ха-ха!", "laugh"),
        ("THE SHINE", "Ты правда думал, что я тебя пущу? Взрыв, Хаос, весь город — это был я.", "shatter"),
        ("THE SHINE", "Испытание — тоже я. Его нельзя пройти. Его можно только проходить.", None),
        ("THE SHINE", "Ну что ж. Покажи, насколько ты упрям.", None),
    )

    def _start_betrayal(self):
        self.cutscene = True
        self.chain = list(self.BETRAYAL)
        self.game.audio.music.stop()
        self._next_chain()

    IMP_SCENE = (
        ("—", "Пол под ногами дрожит. Стены осыпаются в пустоту.", "collapse"),
        ("—", "Ты стоишь на куске базальта посреди озера лавы.", None),
        ("—", "Лава расступается. Из неё поднимается нечто с рогами.", "emerge"),
        ("БЕС", "Наконец-то. Я так долго тебя ждал.", None),
        ("БЕС", "Я следил за тобой с самого утра. С той минуты, как ты открыл занавески.", None),
        ("БЕС", "Тот, кого ты убил наверху... THE SHINE... он был моим сыном.", None),
        ("БЕС", "Он никогда не был богом. Он был всего лишь падшим бесом, которому судьба дала второй шанс.", None),
        ("БЕС", "Он им так и не воспользовался. А ты — убил его.", None),
        ("БЕС", "Ну что ж. Покажи мне, на что способен убийца моего сына.", None),
    )

    GOD_SCENE = (
        ("—", "Небо замирает. Вокруг единственного глаза раскрываются бесчисленные крылья.", "appear"),
        ("БОГ", "Сын мой, зачем ты вторгаешься в святые земли, разжигая в них пламя хаоса и нечестия?", None),
        ("БОГ", "Я уже молчу о частичном уничтожении баланса: ты разрушил преисподнюю.", None),
        ("БОГ", "Кажется, ты сотворил не только семь смертных грехов, но и породил восьмой — совокупность всего зла мира. «Чистое зло».", None),
        ("БОГ", "Такому, как ты, нет места ни на земле, ни в аду, ни в раю.", None),
        ("БОГ", "Я изгоняю тебя из этой вселенной. Прощай, сын мой.", "smite"),
        ("—", "Что-то внутри тебя шевельнулось. Раненый Шайн, зарядившись силой твоей души, приходит в себя...", "possess"),
        ("—", "Он разрывает твоё тело и поднимается на его месте. Теперь ты — Шайн. 1000 здоровья, 100 урона.", "transform"),
    )

    def _start_boss_cutscene(self):
        if self.zone.get("boss_cutscene") == "god":
            self._start_god_cutscene()
        else:
            self._start_imp_cutscene()

    def _start_god_cutscene(self):
        self.pending_cutscene = False
        self.cutscene = True
        self.chain = list(self.GOD_SCENE)
        self.chain_end = self._start_god_fight
        self.player.pos = pygame.Vector2(CENTER.x, CENTER.y + 56)
        self.game.audio.music.stop()
        self._next_chain()

    def _start_god_fight(self):
        boss = self.boss()
        if boss is not None:
            boss.spawn_t = 1.0   # короткая пауза перед началом боя
        self.hud_layout = 0

    def _enter_room(self):
        """Вход в комнату. Босс Ада появляется не сразу: сначала игрок должен дойти до центра."""
        room = self.room
        if room.kind == "boss" and not room.cleared and self.zone.get("boss_cutscene") and room.arena is None:
            room.visited = True
            self.pending_cutscene = True
            return
        self.pending_cutscene = False
        room.enter(self.hp_scale())
        if room.passive and room.spawned and not room.aggro and not self.sky_hint:
            self.sky_hint = True
            self.notes.push("Небесная стража спит. Тронь одного — и проснутся все. Дверь откроется, только когда бой кончится.", "grey", 5)
        mini = self.miniboss()
        if room.kind == "miniboss" and mini is not None:
            self.sfx("boss")
            self.notes.push(mini.name.upper(), "red", 3)

    def _start_imp_cutscene(self):
        self.pending_cutscene = False
        self.cutscene = True
        self.chain = list(self.IMP_SCENE)
        self.chain_end = self._start_imp_fight
        self.game.audio.music.stop()
        self._next_chain()

    def _start_imp_fight(self):
        boss = self.boss()
        if boss is not None:
            boss.spawn_t = 1.0   # короткая пауза перед началом боя
        self.hud_layout = 0

    def _next_chain(self):
        if not self.chain:
            self.cutscene = False
            fn, self.chain_end = (self.chain_end or self._start_fight), None
            fn()
            return
        speaker, text, fx_name = self.chain.pop(0)
        fx = self.game.effects
        if fx_name == "laugh":
            fx.flash((255, 255, 255), 0.5)
            fx.shake(4, 0.7)
            self.sfx("boss")
        elif fx_name == "collapse":   # Ад: стены обрушиваются, остаётся платформа посреди лавы
            self.room.set_arena(pygame.Rect(int(CENTER.x) - 130, int(CENTER.y) - 72, 260, 144))
            fx.shake(9, 1.6)
            fx.flash((255, 120, 40), 0.8)
            fx.burst(CENTER, (90, 80, 90), 40, 170, 1.2, 3)
            self.sfx("death")
        elif fx_name == "emerge":     # Бес поднимается из лавы
            self.room.enter(self.hp_scale())
            boss = self.boss()
            if boss is not None:
                boss.pos = pygame.Vector2(CENTER.x, self.room.arena.top - 36)
                boss.spawn_t = boss.SPAWN_TIME * 0.5
            fx.shake(5, 0.8)
            fx.flash((255, 190, 80), 0.5)
            self.sfx("boss")
        elif fx_name == "appear":     # Небеса: Бог раскрывает крылья
            self.room.enter(self.hp_scale())
            boss = self.boss()
            if boss is not None:
                boss.spawn_t = boss.SPAWN_TIME
            fx.flash((255, 255, 255), 0.9)
            fx.shake(5, 0.9)
            self.sfx("boss")
        elif fx_name == "smite":      # приговор
            fx.flash((255, 255, 255), 0.9)
            fx.shake(7, 1.0)
            self.sfx("death")
        elif fx_name == "possess":    # раненый Шайн вселяется в игрока
            fx.flash((70, 0, 110), 0.8)
            fx.burst(self.player.pos, (190, 90, 235), 36, 120, 0.9, 2)
            fx.shake(4, 0.8)
            self.sfx("story")
        elif fx_name == "transform":  # игрок разорван, дальше играем за Шайна
            self.player.set_form("shine")
            fx.flash((255, 255, 255), 1.0)
            fx.burst(self.player.pos, (255, 230, 140), 48, 170, 1.0, 3)
            fx.shake(9, 1.0)
            self.sfx("boss")
        elif fx_name == "shatter":
            fx.flash((255, 255, 255), 0.9)
            fx.shake(7, 1.0)
            self.room.set_theme(self.zone["judgment_theme"])
            self.sfx("death")
        self.dialogue = DialogueBox(speaker, text)
        self.on_dialogue_end = self._next_chain

    def _start_fight(self):
        """Начало боя с The Shine (иллюзия рая уже рассыпалась)."""
        self.room.set_theme(self.zone["judgment_theme"])
        self.hud_layout = 0
        self.room.enter(self.hp_scale())
        boss = self.boss()
        if boss is not None and hasattr(boss, "opening_comment"):
            boss.opening_comment(self.room, self.player.inv.items)
        self.save_snapshot()

    def heaven_open(self):
        """Небеса открыты, если игрок видел злую концовку (победа над Бесом)."""
        return "evil" in self.game.save.data.get("endings", [])

    def _finish_ending(self):
        kind = "true" if self.zone.get("final_boss") else ("secret" if self.secret_ready else "good")
        if kind == "secret":
            self.morality.add_testimony("shine_was_human")
        self.finish_run(True)
        self.game.go_ending(self, kind)

    def landlord_house_key(self):
        """Ключ дома, в котором живёт Домовладелец (один из домов Пригорода, выбирается по сиду)."""
        if not self.zone.get("house_miniboss") or self.stack:
            return None
        houses = sorted(pos for pos, spec in self.dungeon.specs.items() if spec.kind == "house")
        if not houses:
            return None
        chosen = random.Random(f"{self.zone_seed}:landlord").choice(houses)
        return f"{self.ns}{chosen}:house"

    def enter_house(self, prop):
        mini_kind = "miniboss" if prop.key == self.landlord_house_key() else None
        rng = random.Random(f"{self.ctx_seed}:{prop.key}")
        assigned = {i for ids in self.dungeon.item_for_room.values() for i in ids}
        pool = [i for i in self.zone_pool if i not in self.player.inv.items and i not in assigned]
        self.stack.append({"zone": self.zone, "dungeon": self.dungeon, "rooms": self.rooms, "ctx_seed": self.ctx_seed,
                           "ns": self.ns, "prop": prop})
        self.zone = ZONES["house"]
        self.ctx_seed = f"{self.ctx_seed}:{prop.key}"
        self.ns = f"{prop.key}:"
        self.dungeon = Dungeon(self.ctx_seed, rng.randint(3, 4), pool, house=True, mini_kind=mini_kind)
        self.rooms = {}
        self._swap_room(self.dungeon.pos)
        self.sfx("door")
        self.notes.push("ДОМ. Здесь кто-то есть.", "gold", 3)

    def leave_house(self):
        entry = self.stack.pop()
        looted = any(k.startswith(self.ns) and k.endswith(":0") for k in self.taken)
        self.zone, self.dungeon, self.rooms = entry["zone"], entry["dungeon"], entry["rooms"]
        self.ctx_seed, self.ns = entry["ctx_seed"], entry["ns"]
        self._swap_room(self.dungeon.pos)
        self.player.pos = entry["prop"].pos + pygame.Vector2(0, 30)
        self.sfx("door")
        if looted and self.morality.add_testimony("house_explored"):
            self.notes.push("Новое свидетельство: " + TESTIMONIES["house_explored"][0], "gold", 4)

    def _swap_room(self, pos):
        self.pshots.clear()
        self.eshots.clear()
        self.room = self.get_room(pos)
        self._enter_room()
        self.player.pos = pygame.Vector2(CENTER)
        self.player.knock.update(0, 0)
        self.player.cur_vel.update(0, 0)
        self.room_hit = False

    def _resolve_event(self, ev, prop, choice):
        c = ev["choices"][choice]
        apply_effects(c.get("effects", []), self)
        prop.used = True
        self.taken.add(prop.key)
        self.sfx("story")
        self.dialogue = DialogueBox(ev["name"], c["result"])
        self.after_dialogue = None

    # --- тест-меню (F4 + T) ---
    def toggle_debug(self):
        if self.debug is None:
            self.debug = {"sel": 0}
        else:
            self.debug = None

    def _debug_entries(self):
        """Список пунктов: (подпись, adjust(направление, крупный шаг) | None, activate | None)."""
        p = self.player
        entries = [
            (f"Неуязвимость: {'ВКЛ' if p.god else 'выкл'}", None, self._dbg_god),
            (f"Урон: {p.stats['damage']:.1f}   [←/→, Shift — крупный шаг]", self._dbg_damage, None),
            (f"Макс. здоровье: {p.max_hp} ({p.max_hp / 2:g} сердец)   [←/→]", self._dbg_max_hp, None),
            ("Сбросить значения урона и здоровья", None, self._dbg_reset),
            ("+10 монет", None, lambda: self._dbg_touch(lambda: self.add_coins(10))),
            ("Полное лечение", None, lambda: self._dbg_touch(lambda: setattr(p, "hp", p.max_hp))),
            ("Дать карточку (выбор из трёх)", None, lambda: self._dbg_touch(self._dbg_card)),
            ("Телепорт в комнату босса", None, self.debug_goto_boss),
            ("Телепорт к мини-боссу", None, self.debug_goto_miniboss),
        ]
        for i, zid in enumerate(ZONE_ORDER):
            suffix = " (сразу бой)" if ZONES[zid].get("arena") else ""
            entries.append((f"Локация: {ZONES[zid]['name']}{suffix}", None, lambda i=i: self.debug_goto_zone(i)))
        entries.append(("Закрыть (Esc)", None, self.toggle_debug))
        return entries

    def _dbg_touch(self, fn):
        self.cheated = True
        fn()

    def _dbg_card(self):
        self.debug = None
        self.open_cards()

    def _dbg_god(self):
        self._dbg_touch(lambda: setattr(self.player, "god", not self.player.god))

    def _dbg_damage(self, direction, big):
        p = self.player
        p.debug_damage = max(0.5, round(p.stats["damage"] + direction * (5.0 if big else 0.5), 1))
        self._dbg_touch(p.recompute)

    def _dbg_max_hp(self, direction, big):
        p = self.player
        p.debug_max_hp = max(2, min(200, p.max_hp + direction * (10 if big else 2)))
        self._dbg_touch(p.recompute)

    def _dbg_reset(self):
        self.player.debug_damage = self.player.debug_max_hp = None
        self.player.recompute()

    def debug_goto_zone(self, index):
        """Переход в локацию из тест-меню (финальная арена начинается сразу с боя)."""
        self.cheated = True
        self.dialogue = self.on_dialogue_end = self.after_dialogue = self.trans = None
        self.cutscene, self.chain = False, []
        self.pshots.clear()
        self.eshots.clear()
        self.inverted_t, self.hud_layout = 0.0, 0
        self._setup_zone(index)
        self.room = self.get_room(self.dungeon.pos)
        self.player.pos = pygame.Vector2(CENTER)
        if self.zone.get("arena"):
            self._start_fight()
        else:
            self._enter_room()
        self.notes.push(f"ТЕСТ: {self.zone['name']}", "red", 3)
        self.debug = None

    def debug_goto_boss(self):
        self.cheated = True
        while self.stack:
            self.leave_house()
        pos = next(p for p, s in self.dungeon.specs.items() if s.kind == "boss")
        self.dungeon.visited.add(pos)
        self.dungeon.pos = pos
        self._swap_room(pos)
        self.debug = None

    def debug_goto_miniboss(self):
        """Тест-меню: комната мини-босса текущей локации (в Пригороде — дом Домовладельца)."""
        self.cheated = True
        self.debug = None
        while self.stack:
            self.leave_house()
        pos = next((q for q, sp in sorted(self.dungeon.specs.items()) if sp.kind == "miniboss"), None)
        if pos is None and self.zone.get("house_miniboss"):
            key = self.landlord_house_key()
            house = next((q for q, sp in sorted(self.dungeon.specs.items()) if key == f"{self.ns}{q}:house"), None)
            if house is not None:
                self.dungeon.visited.add(house)
                self.dungeon.pos = house
                self._swap_room(house)
                prop = next((pr for pr in self.room.props if pr.kind == "house"), None)
                if prop is not None:
                    self.enter_house(prop)
                    pos = next((q for q, sp in sorted(self.dungeon.specs.items()) if sp.kind == "miniboss"), None)
        if pos is None:
            self.notes.push("В этой локации нет мини-босса.", "grey", 3)
            return
        self.dungeon.visited.add(pos)
        self.dungeon.pos = pos
        self._swap_room(pos)

    def _debug_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        entries = self._debug_entries()
        sel = self.debug["sel"] = max(0, min(self.debug["sel"], len(entries) - 1))
        k = event.key
        big = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        if k == pygame.K_ESCAPE:
            self.debug = None
        elif k in (pygame.K_UP, pygame.K_w):
            self.debug["sel"] = (sel - 1) % len(entries)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.debug["sel"] = (sel + 1) % len(entries)
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            adjust = entries[sel][1]
            if adjust:
                adjust(-1 if k in (pygame.K_LEFT, pygame.K_a) else 1, big)
        elif k in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            activate = entries[sel][2]
            if activate:
                activate()

    def _draw_debug(self, surf):
        veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 190))
        surf.blit(veil, (0, 0))
        entries = self._debug_entries()
        _draw_text(surf, "ТЕСТ-МЕНЮ (F4 + T)", (GAME_W // 2, 8), "red", 13, "midtop")
        y = 28
        for i, (label, _, _) in enumerate(entries):
            sel = i == self.debug["sel"]
            _draw_text(surf, ("> " if sel else "  ") + label, (60, y), "gold" if sel else "white", 11)
            y += 15
        _draw_text(surf, "Тест-забег не сохраняется и не даёт прогресса. ↑/↓ — выбор, Enter — применить",
                   (GAME_W // 2, GAME_H - 6), "grey", 9, "midbottom")

    # --- обновление ---
    def update(self, dt):
        fx = self.game.effects
        fx.update(dt)
        self.notes.update(dt)
        if self.dying <= 0 and not self.cutscene:
            self.game.audio.music.play(self._desired_track())
        self.game.audio.update_glitch(self.ui_glitch() and not (self.paused or self.overlay or self.debug), dt)
        if self.dialogue:
            if self.dialogue.done:
                choice, cb = self.dialogue.choice, self.after_dialogue
                self.dialogue = None
                if cb and choice is not None:
                    cb(choice)
                elif self.on_dialogue_end:
                    fn, self.on_dialogue_end = self.on_dialogue_end, None
                    fn()
            return
        if self.paused or self.overlay or self.debug is not None or self.cards is not None or self.stats_open:
            return
        if self.dying > 0:
            self.dying -= dt
            if self.dying <= 0:
                self.finish_run(False)
                self.game.go_death(self)
            return
        if self.trans:
            self._update_trans(dt)
            return
        self._update_play(dt)

    def _desired_track(self):
        kind = self.room.kind
        if kind == "miniboss":   # на любом мини-боссе играет mini-bosses.mp3
            return "calm" if self.room.cleared else "miniboss"
        if kind == "boss":
            if self.pending_cutscene:
                return "calm"
            return "calm" if self.boss_dead else self.zone.get("music_boss", "boss")
        return self.zone.get("music_combat", "combat") if kind == "combat" else "calm"

    def _update_play(self, dt):
        self.day_clock += dt
        g, p, room, fx = self.game, self.player, self.room, self.game.effects
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
        if self.inverted_t > 0:  # правило The Shine: управление инвертировано
            move = -move
            self.inverted_t = max(0.0, self.inverted_t - dt)
        mouse = g.display.to_game(pygame.mouse.get_pos())
        aim = mouse - p.pos
        if aim.length_squared() > 4:
            p.aim = aim.normalize()
        room.update_dynamic(dt, p.pos)
        p.update(dt, move, room, None if p.gravity_immune else room.drift())
        if p.needles.update(dt, p.pos.x, p.pos.y) and p.hurt(p.needles.stab_damage()):   # иголки колют при каждом движении
            self._on_player_hurt()
        if self.pending_cutscene and (self.zone.get("boss_cutscene") == "god" or p.pos.distance_to(CENTER) < 28):
            self._start_boss_cutscene()   # Ад: игрок дошёл до центра комнаты; Небеса: Бог говорит сразу
            return
        mouse_down = pygame.mouse.get_pressed()[0]
        if "balancer" not in p.flags:
            self.balancer_charge.cancel()
        if "balancer" in p.flags:   # Балансатор заменяет обычную стрельбу
            self.anchor.cancel_orbit()
            self._update_balancer(dt, mouse_down)
        elif "anchor" in p.flags:   # якорь заменяет обычную стрельбу
            self._update_anchor(dt, mouse_down)
        else:
            self.anchor.cancel_orbit()
            if mouse_down and p.shoot_cd <= 0 and p.dodge_t <= 0:
                if len(self.pshots) < self.cfg["max_player_projectiles"]:
                    self.pshots.extend(combat.build_player_shots(p, p.aim))
                    self.sfx("shoot")
                p.shoot_cd = p.stats["fire_delay"]
        self._update_geysers(dt)
        self._item_effects(dt)
        self._update_thorns(dt)
        self._update_imp(dt)
        self._update_grenades(dt)
        # враги и снаряды
        scale = 0.0 if self.freeze_t > 0 else (0.45 if self.slow_t > 0 else 1.0)
        edt = dt * scale
        room.player_shots = self.pshots
        drift = room.drift()
        dormant = room.dormant
        for e in room.enemies:
            if dormant:   # Небеса: стражи стоят смирно, пока кого-нибудь не тронут
                e.idle(edt)
                continue
            if drift.length_squared() and e.spawn_t <= 0 and not getattr(e, "is_boss", False):
                e.pos += drift * edt
            e.update(edt, room, p, self.enemy_shoot)
        if dormant and any(e.provoked for e in room.enemies):
            room.aggro = True   # тронули одного — бой начинают все
            self.notes.push("Небесная стража проснулась!", "red", 3)
            self.sfx("boss")
        room.process_spawns(self.hp_scale())
        for pr in self.eshots:
            pr.update(edt, room)
        targets = [e for e in room.enemies if e.harmful] if "homing" in p.flags else []
        for pr in self.pshots:
            if pr.homing:
                combat.steer_homing(pr, targets, dt)
            pr.update(dt, room)
        if room.shake_request:
            fx.shake(*room.shake_request)
            room.shake_request = None
        for stat, op, value, secs, text in room.player_effects:
            p.temp_buffs.append([stat, op, value, secs])
            p.recompute()
            if text:
                self.notes.push(text, "red", 3.5)
        room.player_effects.clear()
        for rule, value in room.rule_requests:
            if rule == "invert":
                self.inverted_t = value
                self.notes.push("ПРАВИЛО: управление инвертировано (6 с)", "red", 4)
            elif rule == "scramble_ui":
                self.hud_layout = random.choice([k for k in (1, 2, 3) if k != self.hud_layout])
                self.notes.push("Интерфейс переставлен!", "red", 3)
        room.rule_requests.clear()
        for text, color in room.notices:
            self.notes.push(text, color, 3.5)
        room.notices.clear()
        for h in room.hazards:
            h.update(edt)
            if h.active and h.hits(p.pos, p.RADIUS) and p.hurt(h.damage, h.center):
                self._on_player_hurt()
        room.hazards = [h for h in room.hazards if not h.dead]
        for rect, dmg in room.damage_zones:
            if circle_rect_overlap(p.pos, p.RADIUS, rect) and p.hurt(dmg, pygame.Vector2(rect.center)):
                self._on_player_hurt()
        room.damage_zones.clear()
        self._collisions()
        self._pickups(dt)
        for prop in room.props:
            if prop.kind == "apparition" and not prop.used and prop.pos.distance_to(p.pos) < 70:
                prop.used = True
                apply_effects(self.game.data.events[prop.event_id]["effects"], self)
                fx.burst(prop.pos, (255, 250, 200), 24, 120, 0.8)
                self.sfx("story")
        self.pshots = [s for s in self.pshots if not s.dead]
        self.eshots = [s for s in self.eshots if not s.dead]
        self._check_clear()
        if p.hp <= 0 and not self.cfg["god_mode"]:
            self.dying = 1.3
            self.sfx("death")
            fx.burst(p.pos, (255, 80, 80), 30, 140, 0.9)
            return
        if p.hp <= 0:
            p.hp = p.max_hp
        d = room.check_exit(p.pos)
        if d:
            self.trans = {"dir": d, "t": 0.0, "swapped": False}

    def _item_effects(self, dt):
        p, room, f = self.player, self.room, self.player.flags
        self.slow_t = max(0.0, self.slow_t - dt)
        self.freeze_t = max(0.0, self.freeze_t - dt)
        alive = [e for e in room.enemies if e.harmful]
        if "soldier" in f:
            self.soldier_t -= dt
            if self.soldier_t <= 0 and alive and len(self.pshots) < self.cfg["max_player_projectiles"]:
                origin = p.pos + pygame.Vector2(-10, -8)
                target = min(alive, key=lambda e: e.pos.distance_to(origin))
                self.pshots.extend(combat.soldier_shot(p, origin, target.pos))
                self.soldier_t = 1.4
        if "thorn_cannon" in f:
            self.thorn_t -= dt
            if self.thorn_t <= 0 and alive and len(self.pshots) < self.cfg["max_player_projectiles"]:
                origin = p.pos + pygame.Vector2(12, -10)
                target = min(alive, key=lambda e: e.pos.distance_to(origin))
                self.pshots.extend(combat.thorn_shot(p, origin, target.pos))
                self.thorn_t = 1.1
        if "slow_clock" in f:
            self.clock_t -= dt
            if self.clock_t <= 0:
                self.slow_t, self.clock_t = 3.0, 14.0
                self.notes.push("Часы тикнули: враги замедлены", "blue", 2)
        if "burger_buff" in f:
            self.burger_t -= dt
            if self.burger_t <= 0:
                stat, op, val, label = random.choice(BURGER_BUFFS)
                p.temp_buffs.append([stat, op, val, 8.0])
                p.recompute()
                self.notes.push(f"Гамбургер светится: {label} (8 с)", "green", 2.5)
                self.burger_t = random.uniform(18, 28)
        if "feather" in f:
            self.feather_t -= dt
            if self.feather_t <= 0:
                self.notes.push(random.choice(FEATHER_LINES), "gold", 3)
                self.feather_t = random.uniform(40, 70)

    def enemy_shoot(self, pos, direction, speed, dmg, radius=3, color=(255, 110, 60), kind="shot"):
        if len(self.eshots) < self.cfg["max_enemy_projectiles"]:
            self.eshots.append(Projectile(pos, direction * speed, dmg, 3.0, radius, False, color, kind=kind))

    def _boss_comment(self, key):
        boss = self.boss()
        if boss is not None and hasattr(boss, "comment"):
            boss.comment(key, self.room)

    def _on_player_hurt(self):
        self._boss_comment("hurt")
        self._imp_on_hurt()
        self.room_hit = True
        self.sfx("hurt")
        self.game.effects.shake(3, 0.2)
        self.game.effects.flash((255, 60, 60), 0.18)
        self.game.effects.burst(self.player.pos, (255, 80, 80), 10)

    def _collisions(self):
        p, room, fx = self.player, self.room, self.game.effects
        for pr in self.pshots:
            for e in room.enemies:
                if pr.dead and not pr.pierce:
                    break
                if e.dead or e.spawn_t > 0 or id(e) in pr.hit:
                    continue
                if circles_overlap(pr.pos, pr.radius, e.pos, e.radius):
                    pr.hit.add(id(e))
                    if e.take_damage(pr.damage, pr.vel, pr.knockback):
                        fx.burst(pr.pos, (255, 255, 200), 4, 70, 0.25)
                        self.sfx("hit")
                        if pr.kind == "thorn":   # колючка застревает во враге и ранит его при каждом его движении
                            if getattr(e, "_thorns", None) is None:
                                e._thorns = Needles()
                            e._thorns.add()
                    if pr.poison:
                        e.poison_t = 3.0
                    if pr.explode:
                        self._explode(pr)
                    if not pr.pierce:
                        pr.dead = True
        for pr in self.eshots:
            if circles_overlap(pr.pos, pr.radius, p.pos, p.RADIUS):
                pr.dead = True
                if pr.kind == "needle":   # иголка Живой ели: не ранит сама, а застревает в игроке
                    self._stick_needle()
                    continue
                if p.hurt(pr.damage, pr.pos):
                    self._on_player_hurt()
        for e in room.enemies:
            if not (e.harmful and circles_overlap(e.pos, e.radius, p.pos, p.RADIUS)):
                continue
            if room.dormant:   # спящего можно только задеть: он не ранит, но просыпается вся стража
                e.provoked = True
                continue
            if p.hurt(e.contact, e.pos):
                self._on_player_hurt()
        for pr in self.pshots:   # Шипастая ярость: колючка взрывается, когда исчезает
            if pr.dead and pr.expire_explode and not pr.exploded:
                pr.exploded = True
                self._explode(pr)
        dead = [e for e in room.enemies if e.dead]
        for e in dead:
            self._enemy_died(e)
        room.enemies = [e for e in room.enemies if not e.dead]

    def _stick_needle(self):
        p, fx = self.player, self.game.effects
        if p.invulnerable or p.god:   # во время перекатa иголки пролетают насквозь
            return
        p.needles.add()
        fx.burst(p.pos, (170, 215, 90), 4, 60, 0.2)
        self.sfx("hit")
        if not self.needle_hint:
            self.needle_hint = True
            self.notes.push("Иголки застряли! Каждый шаг ранит 3 с — замри или перекатись.", "red", 4.5)

    def _update_thorns(self, dt):
        """Колючки Колючки-пушки ранят врага при каждом его движении."""
        dmg = max(1.0, self.player.stats["damage"] * 0.4)
        for e in self.room.enemies:
            thorns = getattr(e, "_thorns", None)
            if thorns is None or e.dead:
                continue
            if e.spawn_t <= 0 and thorns.update(dt, e.pos.x, e.pos.y):
                e.take_damage(dmg * thorns.count ** 0.5)
                self.game.effects.burst(e.pos, (170, 215, 90), 3, 50, 0.2)

    def _explode(self, pr):
        fx = self.game.effects
        fx.burst(pr.pos, (255, 160, 60), 16, 130, 0.4, 3)
        fx.shake(2, 0.15)
        for e in self.room.enemies:
            if not e.dead and e.spawn_t <= 0 and e.pos.distance_to(pr.pos) < 40:
                e.take_damage(pr.damage * 0.5, e.pos - pr.pos, 120)

    def _enemy_died(self, e):
        if not self.cheated:   # записи бестиария открываются победой (тест-забег прогресса не даёт)
            self.game.record_defeat(("boss:" + e.kind) if getattr(e, "is_boss", False) else e.kind)
        self.player.inv.register_kill()
        fx = self.game.effects
        fx.burst(e.pos, (255, 255, 255), 12, 120, 0.5, 3)
        fx.burst(e.pos, (130, 240, 90), 8, 80, 0.5, 2)
        self.sfx("hit")
        luck = max(0.0, self.player.stats["luck"])
        if random.random() < e.coin_chance + luck * 0.03:
            from .world.room import Pickup
            item_id = self._channel_loot_item() if "channel_loot" in self.player.flags else None
            if item_id:   # Старый пульт + Старый телевизор: вместо монеты выпадает случайный предмет
                self.room.pickups.append(Pickup("item", e.pos, item_id))
            else:
                self.room.pickups.append(Pickup("coin", e.pos, 1))
        if getattr(e, "is_boss", False):
            self.on_boss_dead(e)
        elif getattr(e, "is_miniboss", False):
            self.on_miniboss_dead(e)

    def _channel_loot_item(self):
        """Случайный предмет для «Переключения каналов»: ещё не твой, не лежащий в комнате и не награда мини-босса."""
        lying = {pk.value for pk in self.room.pickups if pk.kind == "item"}
        pool = [i for i in self.db.regular_ids() if i not in self.player.inv.items and i not in lying]
        return random.choice(pool) if pool else None

    def on_miniboss_dead(self, boss):
        room = self.room
        self.eshots.clear()
        room.hazards.clear()
        room.spawn_requests.clear()
        self.player.needles.clear()
        self.game.effects.flash((255, 255, 255), 0.4)
        self.game.effects.shake(4, 0.4)
        self.sfx("death")
        for other in room.enemies:   # собаки и прочая свита исчезают вместе с мини-боссом
            if other is not boss and not other.dead:
                self.game.effects.burst(other.pos, (255, 255, 255), 8, 80, 0.4, 2)
                other.dead = True
        room.enemies = [e for e in room.enemies if e is boss]
        self._miniboss_reward(room)
        self.notes.push(f"{boss.name} повержен. Он что-то обронил.", "gold", 4)

    def _miniboss_reward(self, room):
        """Предмет-награда мини-босса на пьедестале в центре комнаты (пока не забран)."""
        cls = MINIBOSSES.get(room.zone.get("miniboss"))
        if cls is None or cls.drop_item is None:
            return
        key = f"{room.ns}{room.spec.pos}:mb"
        if key in self.taken or any(p.key == key for p in room.props):
            return
        if cls.drop_item in self.player.inv.items:   # уже есть (тест-меню): вместо предмета монеты
            from .world.room import Pickup
            for _ in range(3):
                room.pickups.append(Pickup("coin", CENTER, 1))
            return
        from .world.room import Prop
        room.props.append(Prop("pedestal", (CENTER.x, CENTER.y), key, item_id=cls.drop_item))

    def _count_boss_kill(self):
        """Считает победу над боссом (для открытия персонажей). Тест-режим не засчитывается."""
        if self.cheated:
            return
        game = self.game
        for char_id in char_logic.record_boss_kill(game.save.data, game.characters, self.zone["boss"]):
            name = game.characters[char_id]["name"]
            self.notes.push(f"ОТКРЫТ ПЕРСОНАЖ: {name}!", "gold", 6)
            game.steam.unlock("CHAR_" + char_id.upper())
            self.sfx("story")
        game.save.write()

    def _boss_rewards(self, room, silent=False):
        from .world.room import Prop
        if self.zone.get("final_boss"):   # Бог повержен: остаются только врата к истинной концовке
            room.props.append(Prop("gates", (CENTER.x, CENTER.y), f"{room.ns}{room.spec.pos}:gates"))
            return
        if self.zone.get("arena"):
            room.props.append(Prop("gates", (CENTER.x, CENTER.y), f"{room.ns}{room.spec.pos}:gates"))
            if self.heaven_open():   # злая концовка открыта: рядом с вратами появляется портал на Небеса
                room.props.append(Prop("sky_portal", (CENTER.x + 70, CENTER.y), f"{room.ns}{room.spec.pos}:sky"))
            if self.morality.secret_unlocked():   # секретная концовка открыта: в стене появляется дверь с разломом в Ад
                room.props.append(Prop("rift", (CENTER.x - 70, CENTER.y), f"{room.ns}{room.spec.pos}:rift"))
            return
        items = self.dungeon.item_for_room.get(room.spec.pos, [])
        key = f"{room.ns}{room.spec.pos}:r"
        if items and key not in self.taken:
            room.props.append(Prop("pedestal", (CENTER.x - 40, CENTER.y), key, item_id=items[0]))
        room.props.append(Prop("portal", (CENTER.x + 40, CENTER.y), f"{room.ns}{room.spec.pos}:portal"))

    def on_boss_dead(self, boss):
        self.boss_dead = True
        self.eshots.clear()
        self.game.effects.flash((255, 255, 255), 0.6)
        self.game.effects.shake(6, 0.6)
        self.sfx("death")
        self.room.hazards.clear()
        self.room.cancel_dynamic()
        self.inverted_t, self.hud_layout = 0.0, 0
        self.secret_ready = self.morality.secret_unlocked()
        self._count_boss_kill()
        self.room.spawn_requests.clear()
        for other in self.room.enemies:  # клоны, призванные существа и т. п. исчезают вместе с боссом
            if other is not boss and not other.dead:
                self.game.effects.burst(other.pos, (255, 255, 255), 10, 90, 0.5, 2)
                other.dead = True
        self.room.enemies = [e for e in self.room.enemies if e is boss]
        tid = self.zone["boss_testimony"]
        if self.morality.add_testimony(tid):
            self.notes.push("Новое свидетельство: " + TESTIMONIES[tid][0], "gold", 4)
        self._boss_rewards(self.room)
        if self.zone.get("arena"):
            if self.secret_ready:
                self.notes.push("Его силуэт дрогнул. В голосе было что-то знакомое...", "gold", 6)
                self.notes.push("В стене открылась дверь. За ней — разлом, в котором виден ад.", "red", 6)
            if self.heaven_open():
                self.notes.push("Рядом с вратами раскрылся белый портал. Куда он ведёт — на небеса?", "gold", 6)
            self.notes.push("Он пал. Врата перед тобой открыты.", "gold", 5)
        elif self.zone.get("final_boss"):
            self.notes.push("Бог пал. Всё стихло. Врата перед тобой открыты.", "gold", 6)
        else:
            self.notes.push(f"{self.zone['boss_name'].capitalize()} повержен. Забери награду и войди в портал.", "gold", 5)

    def _pickups(self, dt):
        p = self.player
        for pk in self.room.pickups:
            pk.pos += pk.vel * dt
            pk.vel *= max(0.0, 1 - 4 * dt)
            d = pk.pos.distance_to(p.pos)
            if d < 50:
                pk.pos += (p.pos - pk.pos).normalize() * 90 * dt if d > 0 else pygame.Vector2()
            if d < 9:
                if pk.kind == "coin":
                    p.coins += pk.value
                    pk.dead = True
                    self.sfx("buy")
                elif pk.kind == "heart" and p.hp < p.max_hp:
                    p.heal(2)
                    pk.dead = True
                    self.sfx("pickup")
                elif pk.kind == "item":
                    pk.dead = True
                    self.give_item(pk.value)
        self.room.pickups = [k for k in self.room.pickups if not k.dead]

    def _check_clear(self):
        room = self.room
        if room.locked and not room.enemies and not room.spawn_requests:
            room.locked, room.cleared = False, True
            self.rooms_cleared += 1
            self.sfx("door")
            self.eshots.clear()
            from .world.room import Pickup
            luck = max(0.0, self.player.stats["luck"])
            if random.random() < 0.3 + luck * 0.03:
                room.pickups.append(Pickup("heart", CENTER + pygame.Vector2(0, 20)))
            if "photo" in self.player.flags and not self.room_hit and room.kind == "combat":
                self.photo_count += 1
                if self.photo_count == 2:
                    self.morality.add_testimony("memory_photo")
                    self.notes.push("Фотография проявилась: ты спишь в своей спальне.", "gold", 5)
                    self.player.heal(2)
                    self.sfx("story")
            if room.kind != "boss":
                self.save_snapshot()

    def _update_trans(self, dt):
        t = self.trans
        t["t"] += dt
        if t["t"] >= 0.18 and not t["swapped"]:
            t["swapped"] = True
            new_pos = self.room.spec.doors[t["dir"]]
            self.dungeon.pos = new_pos
            self.dungeon.visited.add(new_pos)
            self.room = self.get_room(new_pos)
            self._enter_room()
            self.player.pos = self.room.door_pos(OPP[t["dir"]])
            self.player.knock.update(0, 0)
            self.player.cur_vel.update(0, 0)
            self.pshots.clear()
            self.eshots.clear()
            self.room_hit = False
            self.sfx("door")
            if self.room.kind == "boss" and not self.room.cleared:
                self.sfx("boss")
                self.notes.push(self.zone["boss_name"], "red", 3)
            if self.room.kind in ("shop", "treasure"):
                self.save_snapshot()
        if t["t"] >= 0.36:
            self.trans = None

    # --- отрисовка ---
    def draw(self, surf):
        fx = self.game.effects
        sprites = self.game.sprites
        off = fx.offset()
        room = self.room
        room.draw_floor(surf, off)
        t_sec = pygame.time.get_ticks() / 1000
        room.draw_lava(surf, off, t_sec)
        room.draw_hazards(surf, off)
        for prop in room.props:
            self._draw_prop(surf, off, prop)
        for pk in room.pickups:
            if pk.kind == "item":   # выпавший предмет (Переключение каналов)
                icon = sprites.icon(pk.value)
                bob = int(math.sin(t_sec * 5 + pk.pos.x) * 2)
                surf.blit(icon, icon.get_rect(center=(int(pk.pos.x + off.x), int(pk.pos.y + off.y) + bob)))
                continue
            img = sprites.get("coin" if pk.kind == "coin" else "gem_heart")
            surf.blit(img, (pk.pos.x + off.x - 3, pk.pos.y + off.y - 3))
        room.draw_obstacles(surf, off, sprites)
        self._draw_shadows(surf, off, sprites)
        for e in sorted(room.enemies, key=lambda e: e.pos.y):
            e.draw(surf, off, sprites)
        if "soldier" in self.player.flags:
            surf.blit(sprites.get("soldier"), (self.player.pos.x - 16 + off.x, self.player.pos.y - 14 + off.y))
        self.player.draw(surf, off, sprites)
        self._draw_extras(surf, off, sprites)
        for pr in self.pshots + self.eshots:
            pr.draw(surf, off)
        fx.draw_particles(surf, off)
        room.draw_embers(surf, off, t_sec)
        self._apply_lighting(surf, off, t_sec)
        surf.blit(self.game.vignette, (0, 0))
        if self.freeze_t > 0 or self.slow_t > 0:
            tint = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            tint.fill((120, 160, 255, 35))
            surf.blit(tint, (0, 0))
        draw_hud(surf, self, sprites)
        near = self.nearest_prop()
        if near is not None and not self.dialogue:
            self._draw_prompt(surf, near)
        if self.ui_glitch():
            self._draw_glitch(surf)
        fx.draw_flash(surf)
        if self.trans:
            a = 1 - abs(self.trans["t"] - 0.18) / 0.18
            veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * max(0, min(1, a)))))
            surf.blit(veil, (0, 0))
        if self.dying > 0:
            veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * (1 - self.dying / 1.3))))
            surf.blit(veil, (0, 0))
        if self.dialogue:
            self.dialogue.draw(surf)
        if self.overlay:
            draw_journal(surf, self.db, self.tab, self.player.inv.items, self.morality.all_testimonies())
        if self.paused:
            veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 160))
            surf.blit(veil, (0, 0))
            self.pause_menu.draw(surf)
        if self.cards is not None:
            self._draw_cards(surf)
        if self.stats_open:
            self._draw_stats(surf)
        if self.debug is not None:
            self._draw_debug(surf)

    # --- освещение, тени, время суток ---
    def light_state(self):
        gfx = self.game.gfx
        return effective_state(self.zone, self.day_clock, self.cfg.get("day_length_seconds", 480), gfx["time_mode"],
                               NIGHT_MULT[gfx["night_brightness"]], gfx["lights"])

    def _shadow_actors(self, sprites):
        """Кто отбрасывает тень: игрок, мобы, боссы, NPC и компаньон. (x, y ног, ширина, высота)."""
        p = self.player
        img = sprites.get("player_" + p.char_id)
        actors = [(p.pos.x, p.pos.y + p.RADIUS + 4, img.get_width() * 0.8, img.get_height())]
        for e in self.room.enemies:
            if e.dead or e.spawn_t > 0:
                continue
            w, h = sprites.get(e.sprite).get_size()
            floating = e.kind in ("shine", "imp", "drone", "crow", "eye_swarm", "ember")
            actors.append((e.pos.x, e.pos.y + h / 2 + (10 if floating else 0), w * 0.8, h * (0.6 if floating else 1.0)))
        for prop in self.room.props:
            if prop.kind == "npc":
                actors.append((prop.pos.x, prop.pos.y + 8, 10, 20))
        if self.imp is not None:
            actors.append((self.imp["pos"].x, self.imp["pos"].y + 16, 8, 8))
        return actors

    def _draw_shadows(self, surf, off, sprites):
        gfx = self.game.gfx
        if not (gfx["shaders"] and gfx["shadows"]):
            return
        self.game.lighting.draw_shadows(surf, off, self._shadow_actors(sprites), self.light_state(), gfx)

    BOSS_LIGHTS = {"lumberjack": ((255, 170, 80), 68, 0.7), "neighbor_boss": ((255, 220, 120), 72, 0.7),
                   "mayor": ((255, 240, 200), 84, 0.75), "chaos": ((255, 80, 220), 104, 0.85),
                   "shine": ((255, 235, 150), 124, 0.95), "imp": ((255, 120, 40), 116, 0.9),
                   "living_spruce": ((150, 225, 100), 54, 0.6), "landlord": ((200, 225, 255), 46, 0.55),
                   "tank": ((255, 190, 90), 50, 0.55)}
    MOB_LIGHTS = {"ember": ((255, 140, 40), 34), "fire_imp": ((255, 120, 40), 30), "magma_golem": ((255, 110, 30), 36),
                  "hellhound": ((255, 100, 30), 26), "glitch": ((80, 255, 220), 30), "eye_swarm": ((255, 60, 90), 20),
                  "drone": ((255, 70, 70), 18), "ad_tv": ((140, 200, 255), 30)}

    def _collect_lights(self, off, state, t):
        """Свет излучают игрок, боссы, часть мобов, снаряды, взрывы и особые объекты комнаты."""
        lights = []
        p = self.player
        lights.append((p.pos.x + off.x, p.pos.y + off.y, int(36 + 54 * state.darkness), (255, 236, 190), 0.5 + 0.5 * state.darkness))
        for e in self.room.enemies:
            if e.dead or e.spawn_t > 0:
                continue
            if e.kind in self.BOSS_LIGHTS:
                color, radius, power = self.BOSS_LIGHTS[e.kind]
                flicker = 1.0 + 0.06 * math.sin(t * 7 + e.pos.x)
                lights.append((e.pos.x + off.x, e.pos.y + off.y, int(radius * flicker), color, power))
            elif e.kind in self.MOB_LIGHTS:
                color, radius = self.MOB_LIGHTS[e.kind]
                lights.append((e.pos.x + off.x, e.pos.y + off.y, radius, color, 0.7))
        for pr in self.eshots[:40]:
            lights.append((pr.pos.x + off.x, pr.pos.y + off.y, 16, pr.color, 0.6))
        for pr in self.pshots[:20]:
            lights.append((pr.pos.x + off.x, pr.pos.y + off.y, 14, (255, 240, 150), 0.5))
        for b in self.blasts:
            lights.append((b["pos"].x + off.x, b["pos"].y + off.y, int(b["r"] * 2.2), (255, 170, 60), 1.0 - b["t"] / 0.4))
        if self.imp is not None:
            lights.append((self.imp["pos"].x + off.x, self.imp["pos"].y + off.y, 26, (255, 120, 50), 0.7))
        for pos, radius, color, power in self.room.light_sources():
            lights.append((pos.x + off.x, pos.y + off.y, radius, color, power))
        return lights

    def _apply_lighting(self, surf, off, t):
        gfx = self.game.gfx
        if not gfx["shaders"]:
            return
        state = self.light_state()
        self.game.lighting.apply(surf, state, self._collect_lights(off, state, t), gfx)

    def _draw_extras(self, surf, off, sprites):
        """Якорь с цепью, летящие гранаты, взрывы и компактный бес."""
        p = self.player
        if "anchor" in p.flags:
            a = self.anchor
            apos = pygame.Vector2(a.pos) if a.state != "idle" else p.pos + pygame.Vector2(12, 4)
            if a.state != "idle":
                pygame.draw.line(surf, (170, 180, 200), (p.pos.x + off.x, p.pos.y + off.y), (apos.x + off.x, apos.y + off.y), 1)
            icon = sprites.icon("anchor")
            big = pygame.transform.scale(icon, (icon.get_width() * 3 // 2, icon.get_height() * 3 // 2))
            surf.blit(big, big.get_rect(center=(int(apos.x + off.x), int(apos.y + off.y))))
            if a.state == "orbit":   # индикатор дальности броска
                w = int(26 * min(1.0, a.hold / FULL_CHARGE))
                pygame.draw.rect(surf, (30, 20, 45), (p.pos.x - 14 + off.x, p.pos.y - 22 + off.y, 28, 4))
                pygame.draw.rect(surf, (255, 215, 90), (p.pos.x - 13 + off.x, p.pos.y - 21 + off.y, w, 2))
        for g in self.grenades:
            f = g["t"] / g["dur"]
            ground = g["start"].lerp(g["target"], f)
            height = math.sin(math.pi * f) * 28
            gx, gy = int(ground.x + off.x), int(ground.y + off.y)
            pygame.draw.ellipse(surf, (20, 12, 28), (gx - 4, gy - 1, 8, 4))
            pygame.draw.circle(surf, (90, 110, 70), (gx, gy - int(height)), 4)
            pygame.draw.circle(surf, (230, 230, 100), (gx + 1, gy - int(height) - 4), 1)
            if int(pygame.time.get_ticks() / 100) % 2:   # зона будущего взрыва
                pygame.draw.circle(surf, (255, 90, 60), (int(g["target"].x + off.x), int(g["target"].y + off.y)), int(g["radius"]), 1)
        for b in self.blasts:
            k = b["t"] / 0.4
            r = int(b["r"] * (0.4 + 0.6 * k))
            pos = (int(b["pos"].x + off.x), int(b["pos"].y + off.y))
            if k < 0.35:
                pygame.draw.circle(surf, (255, 235, 160), pos, int(r * 0.8))
            pygame.draw.circle(surf, (255, 170, 60), pos, r, 3 if k < 0.6 else 1)
        if self.imp is not None:
            img = sprites.get("imp_mini", self.imp["flip"])
            surf.blit(img, img.get_rect(center=(int(self.imp["pos"].x + off.x), int(self.imp["pos"].y + off.y))))
        self._draw_geyser(surf, off, self.balancer)
        self._draw_geyser(surf, off, self.scream)
        self._draw_balancer_charge(surf, off)
        if "thorn_cannon" in p.flags:   # Колючка-пушка парит рядом с игроком
            icon = sprites.icon("thorn_cannon")
            bob = int(math.sin(pygame.time.get_ticks() / 260) * 2)
            surf.blit(icon, icon.get_rect(center=(int(p.pos.x + 15 + off.x), int(p.pos.y - 12 + off.y) + bob)))
        self._draw_stuck(surf, off, p.pos, p.needles, 7)
        for e in self.room.enemies:
            if getattr(e, "_thorns", None):
                self._draw_stuck(surf, off, e.pos, e._thorns, e.radius)

    def _draw_stuck(self, surf, off, pos, needles, radius):
        """Застрявшие иголки торчат из цели; тонкая полоска показывает, сколько ещё они продержатся."""
        if not needles:
            return
        cx, cy = pos.x + off.x, pos.y + off.y
        for i, left in enumerate(needles.timers):
            a = i * 2.4 + 0.7
            ca, sa = math.cos(a), math.sin(a)
            pygame.draw.line(surf, (34, 24, 48), (cx + ca * radius * 0.6, cy + sa * radius * 0.6),
                             (cx + ca * (radius + 5), cy + sa * (radius + 5)), 3)
            pygame.draw.line(surf, (170, 215, 90), (cx + ca * radius * 0.6, cy + sa * radius * 0.6),
                             (cx + ca * (radius + 5), cy + sa * (radius + 5)), 1)
        frac = max(timers_left / needles.stick_time for timers_left in needles.timers)
        pygame.draw.rect(surf, (30, 20, 45), (cx - 8, cy - radius - 11, 16, 3))
        pygame.draw.rect(surf, (170, 215, 90), (cx - 7, cy - radius - 10, int(14 * frac), 1))

    def _draw_glitch(self, surf):
        """Несколько горизонтальных полос сдвигаются на пару пикселей (читаемость сохраняется)."""
        if random.random() < 0.5:
            return
        for _ in range(2):
            y = random.randrange(ROOM_Y, ROOM_Y + ROOM_H - 12)
            h = random.randint(3, 10)
            dx = random.choice((-5, -3, 3, 5))
            strip = surf.subsurface((0, y, GAME_W, h)).copy()
            surf.blit(strip, (dx, y))

    def _draw_prompt(self, surf, prop):
        label = {"pedestal": "забрать", "heal": "купить сердце", "npc": "говорить", "altar": "алтарь",
                 "portal": "войти в портал", "sky_portal": "войти в белый портал", "rift": "прыгнуть в разлом", "card": "карточка (выбор из трёх)", "gates": "пройти через врата", "house": "войти в дом", "exit": "выйти на улицу"}.get(prop.kind, "")
        if prop.kind == "pedestal":
            item = self.db.items[prop.item_id]
            label = item.name + (f" — {prop.price} мон." if prop.price else "")
        elif prop.kind == "heal":
            label = f"сердце — {prop.price} мон."
        draw_text(surf, f"[E] {label}", (prop.pos.x, prop.pos.y - 26), "white", 10, "midbottom")

    def _draw_prop(self, surf, off, prop):
        x, y = int(prop.pos.x + off.x), int(prop.pos.y + off.y)
        t = pygame.time.get_ticks() / 1000
        if prop.kind == "pedestal":
            pygame.draw.rect(surf, (140, 140, 160), (x - 8, y - 2, 16, 10))
            pygame.draw.rect(surf, (34, 24, 48), (x - 8, y - 2, 16, 10), 1)
            icon = self.game.sprites.icon(prop.item_id)
            surf.blit(icon, icon.get_rect(midbottom=(x, y - 3 + int(math.sin(t * 3) * 2))))
            if prop.price:
                draw_text(surf, str(prop.price), (x, y + 9), "gold", 9, "midtop")
        elif prop.kind == "card":
            pygame.draw.rect(surf, (140, 140, 160), (x - 8, y - 2, 16, 10))
            pygame.draw.rect(surf, (34, 24, 48), (x - 8, y - 2, 16, 10), 1)
            bob = int(math.sin(t * 3) * 2)
            card = pygame.Rect(x - 7, y - 20 + bob, 14, 18)
            pygame.draw.rect(surf, (255, 215, 90), card, border_radius=2)
            pygame.draw.rect(surf, (34, 24, 48), card, 1, border_radius=2)
            _draw_text(surf, "?", card.center, (60, 30, 90), 12, "center", shadow=False)
        elif prop.kind == "heal":
            surf.blit(self.game.sprites.get("heart_full"), (x - 5, y - 5))
            draw_text(surf, str(prop.price), (x, y + 6), "gold", 9, "midtop")
        elif prop.kind == "npc":
            col = (120, 120, 140) if prop.used else (200, 140, 90)
            pygame.draw.rect(surf, col, (x - 5, y - 4, 10, 12))
            pygame.draw.circle(surf, (255, 205, 170), (x, y - 8), 5)
            pygame.draw.rect(surf, (34, 24, 48), (x - 5, y - 4, 10, 12), 1)
        elif prop.kind == "altar" and self.game.data.events[prop.event_id].get("prop") == "bed":
            pygame.draw.rect(surf, (110, 160, 210), (x - 14, y - 6, 28, 16))
            pygame.draw.rect(surf, (255, 250, 240), (x - 14, y - 6, 9, 16))
            pygame.draw.rect(surf, (34, 24, 48), (x - 14, y - 6, 28, 16), 1)
        elif prop.kind == "altar":
            pygame.draw.rect(surf, (110, 110, 130), (x - 10, y - 6, 20, 14))
            pygame.draw.rect(surf, (34, 24, 48), (x - 10, y - 6, 20, 14), 1)
            if not prop.used:
                pygame.draw.circle(surf, (200, 120, 255), (x, y - 12 + int(math.sin(t * 4) * 2)), 4)
        elif prop.kind == "apparition" and not prop.used:
            for i in range(5):
                pygame.draw.ellipse(surf, (255, 250, 220), (x - 4 + i * 5, y - 14 + i * 3, 10, 24), 1)
        elif prop.kind == "rift":   # дверь с разломом, в котором виден ад
            frame = pygame.Rect(x - 20, y - 36, 40, 50)
            pygame.draw.rect(surf, (30, 24, 30), frame.inflate(8, 8), border_radius=6)
            pygame.draw.rect(surf, (120, 30, 20), frame, border_radius=4)
            for i in range(6):   # пляшущее пламя внутри разлома
                fx_ = x - 14 + i * 6
                h = 16 + int(math.sin(t * 6 + i * 1.7) * 7)
                pygame.draw.polygon(surf, (255, 150 + i * 12, 40), [(fx_, y + 12), (fx_ + 3, y + 12 - h), (fx_ + 6, y + 12)])
            pygame.draw.lines(surf, (255, 220, 90), False, [(x - 2, y - 36), (x + 3, y - 22), (x - 3, y - 8), (x + 2, y + 6)], 1)
            pygame.draw.rect(surf, (20, 12, 20), frame, 2, border_radius=4)
        elif prop.kind == "gates":
            pygame.draw.rect(surf, (255, 245, 200), (x - 18, y - 30, 36, 40), border_radius=18)
            pygame.draw.rect(surf, (255, 255, 255), (x - 12, y - 24, 24, 34), border_radius=12)
            pygame.draw.rect(surf, (255, 215, 90), (x - 18, y - 30, 36, 40), 2, border_radius=18)
        elif prop.kind == "house":
            pygame.draw.rect(surf, (225, 205, 170), (x - 22, y - 14, 44, 30))
            pygame.draw.polygon(surf, (190, 70, 60), [(x - 27, y - 14), (x, y - 36), (x + 27, y - 14)])
            pygame.draw.rect(surf, (110, 70, 45), (x - 5, y, 10, 16))
            pygame.draw.rect(surf, (120, 190, 240), (x - 18, y - 8, 9, 9))
            pygame.draw.rect(surf, (120, 190, 240), (x + 9, y - 8, 9, 9))
            pygame.draw.rect(surf, (34, 24, 48), (x - 22, y - 14, 44, 30), 1)
        elif prop.kind == "exit":
            pygame.draw.rect(surf, (110, 70, 45), (x - 8, y - 4, 16, 14))
            pygame.draw.rect(surf, (255, 235, 150), (x - 6, y - 2, 12, 10), 1)
        elif prop.kind == "sky_portal":   # белый вихрь в золотой оправе: ведёт на Небеса
            pygame.draw.circle(surf, (255, 205, 80), (x, y), 19, 3)
            for i in range(4):
                pygame.draw.circle(surf, (255, 255, 255), (x, y), 15 - i * 4 + int(math.sin(t * 4 + i) * 2), 1 if i % 2 else 2)
            for i in range(6):
                a = t * 3 + i * math.tau / 6
                pygame.draw.circle(surf, (255, 250, 220), (int(x + math.cos(a) * 12), int(y + math.sin(a) * 12)), 1)
        elif prop.kind == "portal":
            for i in range(3):
                pygame.draw.circle(surf, (255, 255, 200 - i * 50), (x, y), 14 - i * 4 + int(math.sin(t * 5 + i) * 2), 2)
