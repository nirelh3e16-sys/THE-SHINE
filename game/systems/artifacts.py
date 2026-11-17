"""Артефакты 1.1.0: поведение 30 предметов и их синергий.

Сами предметы описаны в data/items.json (характеристики — mods, особые свойства — flags, активные — active).
Здесь живёт то, что нельзя выразить числами: волны света, молнии, духи, щиты, заморозка, проклятия комнат.
PlayState создаёт один ArtifactState на забег и вызывает его хуки (on_shot, on_kill, update, draw и т. д.);
Player знает о нём только через несколько проверок в hurt() и recompute().

Принцип баланса всех предметов: каждый дар требует жертвы — у сильного бонуса всегда есть цена.
"""
import math
import random
from types import SimpleNamespace

import pygame

from ..entities.projectile import Projectile
from ..settings import ROOM_X, ROOM_Y, ROOM_W, ROOM_H

# активные предметы 1.1.0 (поле active.type в items.json)
ARTIFACT_ACTIVES = ("prophecy", "mortar", "pandora", "helm", "thread", "zeus")

LIGHT = (255, 240, 170)
FIRE = (255, 140, 50)
GHOST = (190, 220, 255)
BONE = (235, 230, 210)
SMALL_HAZARD_AREA = 2500     # Венок русалки: зоны не больше 50x50 пикселей считаются «малыми»
MAX_PATCHES = 90

PROPHECY_SMITE = "Пророчество: враги повержены!"
PROPHECY_HEAL = "Пророчество: ты исцелён."
PROPHECY_BLESS = "Пророчество: ты усилен (12 с)."
PROPHECY_FALSE = "Ложное пророчество: ты ослаблен."


def _rot(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return pygame.Vector2(v.x * c - v.y * s, v.x * s + v.y * c)


def dist_point_segment(p, a, b):
    """Расстояние от точки до отрезка (для молнии по линии прицела)."""
    ab = b - a
    n = ab.length_squared()
    if n == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / n))
    return p.distance_to(a + ab * t)


def _is_big(e):
    return bool(getattr(e, "is_boss", False) or getattr(e, "is_miniboss", False))


class ArtifactState:
    FLIGHT_HEAT_LIMIT = 1.2

    def __init__(self, play):
        self.play = play
        self.t = 0.0
        self.decoy = SimpleNamespace(pos=pygame.Vector2(ROOM_X + 24, ROOM_Y + 24))   # куда смотрят враги, пока ты невидим
        self.waves, self.patches, self.bolts, self.mortars = [], [], [], []
        self.spirit = None
        self.absorb_msg = None
        self.invis_t = 0.0        # Шлем Аида
        self.lock_t = 0.0         # нельзя атаковать (цена Ступы и Молнии)
        self.curse_haste = False  # проклятие комнаты (Ящик Пандоры): враги быстрее до конца комнаты
        self.cur_dungeon = self.cur_pos = self.prev_pos = None
        self.immortality_used = False   # «Цена бессмертия»: раз за забег
        self.seal_kills = self.perun_n = 0
        self._sig = None
        self._last_fly_pos = None
        self._mortar_img = None
        self.reset_floor()

    # ------------------------------------------------------------------ состояние
    def reset_floor(self):
        """Всё, что действует «до конца этажа», сбрасывается при смене зоны."""
        p = self.play.player
        had = bool(p.floor_mods) or bool(getattr(self, "disabled", None))
        p.floor_mods.clear()
        self.disabled = set()      # предметы, потерявшие силу («Цена бессмертия»)
        self.shield_t, self.shield_ready = 0.0, False
        self.needle_used = False
        self.undo_ready = True     # Ящик Пандоры + Нить Ариадны: раз за этаж
        self.heat = 0.0            # Крылья Икара: перегрев от частых полётов
        self.feather_t = 15.0
        self.burn_self_t = 18.0
        self.waves.clear()
        self.patches.clear()
        if had:
            p.recompute()

    def snapshot(self):
        return {"immortality_used": self.immortality_used}

    def restore(self, data):
        self.immortality_used = bool((data or {}).get("immortality_used", False))

    @property
    def flags(self):
        return self.play.player.flags

    def attack_blocked(self):
        """Ступа, Молния Зевса и Шлем Аида запрещают атаковать."""
        return self.lock_t > 0 or self.invis_t > 0

    def _note(self, text, color="gold", secs=2.5):
        self.play.notes.push(text, color, secs)

    def _buff(self, stat, op, value, secs):
        """Временный модификатор; повторный такой же только продлевается (дебаффы не копятся бесконечно)."""
        p = self.play.player
        for b in p.temp_buffs:
            if b[0] == stat and b[1] == op and abs(b[2] - value) < 1e-9:
                b[3] = max(b[3], secs)
                return
        p.temp_buffs.append([stat, op, value, secs])
        p.recompute()

    def _fire_mult(self):
        return 1.5 if "prometheus" in self.flags else 1.0

    def _alive(self):
        return [e for e in self.play.room.enemies if e.harmful]

    # ------------------------------------------------------------------ характеристики
    def dynamic_mods(self, p):
        """Модификаторы, зависящие от текущего здоровья и монет (Весы правосудия)."""
        mods = []
        f = p.flags
        if "scales" in f and p.max_hp > 0:
            if p.hp >= p.max_hp:
                mods.append(("damage", "mul", 1.2))
            elif p.hp * 3 <= p.max_hp:
                bonus = 1.2
                if "silver_scales" in f:   # монеты постепенно усиливают бонус слабого состояния
                    bonus += min(0.2, p.coins * 0.01)
                mods.append(("speed", "mul", bonus))
        return mods

    def refresh(self):
        """Пересчитать характеристики, если изменилось состояние Весов (здоровье, монеты)."""
        p = self.play.player
        f = p.flags
        if "scales" not in f:
            self._sig = None
            return
        sig = (p.hp >= p.max_hp, p.hp * 3 <= p.max_hp, p.max_hp, p.coins // 5 if "silver_scales" in f else 0)
        if sig != self._sig:
            self._sig = sig
            p.recompute()

    def enemy_speed(self, e):
        """Множитель времени врага: Запретный плод и проклятие комнаты (боссов не трогаем)."""
        if _is_big(e):
            return 1.0
        k = 1.0
        if "enemy_haste" in self.flags:
            k *= 1.15
        if self.curse_haste:
            k *= 1.25
        return k

    def target_for(self, e, player):
        """Обычные враги теряют невидимого игрока из виду; боссы видят, но ранить не могут."""
        return self.decoy if self.invis_t > 0 and not _is_big(e) else player

    # ------------------------------------------------------------------ урон врагам
    def _hit(self, e, dmg, src, knock=0.0, fire=False):
        if e.dead or e.spawn_t > 0:
            return False
        if fire:
            dmg *= self._fire_mult()
            if "prometheus" in self.flags:
                self._ignite(e)
        if _is_big(e):
            knock = 0.0
        return e.take_damage(dmg, e.pos - src, knock)

    def _ignite(self, e):
        if getattr(e, "burn_t", 0.0) <= 0:
            self.play.game.effects.burst(e.pos, FIRE, 4, 60, 0.3, 2)
        e.burn_t = 3.0
        e.burn_dps = max(0.8, self.play.player.stats["damage"] * 0.25) * self._fire_mult()

    def _freeze(self, e, secs, kind):
        if _is_big(e) or getattr(e, "frozen_t", 0.0) > 0:
            return
        e.frozen_t, e.frozen_kind = secs, kind
        fx = self.play.game.effects
        fx.burst(e.pos, (170, 220, 255) if kind == "ice" else (170, 170, 180), 8, 70, 0.4, 2)
        if kind == "ice" and "rusalka_morana" in self.flags:
            self._buff("speed", "mul", 1.25, 2.5)

    def _wave(self, pos, color, max_r, speed, dmg, delay=0.0, fire=False):
        self.waves.append({"pos": pygame.Vector2(pos), "r": 6.0, "max": max_r, "speed": speed, "dmg": dmg,
                           "color": color, "delay": delay, "hit": set(), "fire": fire})

    def _patch(self, pos, r=6.0, life=1.3, dmg=None, fire=True, color=(255, 120, 40)):
        if dmg is None:
            dmg = max(0.6, self.play.player.stats["damage"] * 0.18)
        self.patches.append({"pos": pygame.Vector2(pos), "r": r, "t": life, "life": life, "tick": 0.0,
                             "dmg": dmg, "fire": fire, "color": color})
        if len(self.patches) > MAX_PATCHES:
            del self.patches[0]

    def _bolt(self, a, b, color=(255, 245, 160), dur=0.32):
        a, b = pygame.Vector2(a), pygame.Vector2(b)
        d = b - a
        n = max(2, int(d.length() / 24))
        perp = pygame.Vector2(-d.y, d.x)
        perp = perp.normalize() if perp.length_squared() else pygame.Vector2(0, 1)
        pts = [a]
        for i in range(1, n):
            pts.append(a + d * (i / n) + perp * random.uniform(-7, 7))
        pts.append(b)
        self.bolts.append({"pts": pts, "t": 0.0, "dur": dur, "color": color})

    def _strike(self, pos, dmg, radius=24, color=(255, 245, 160)):
        """Удар молнии с неба по точке."""
        pos = pygame.Vector2(pos)
        self._bolt(pos + pygame.Vector2(random.uniform(-10, 10), -150), pos, color)
        fx = self.play.game.effects
        fx.burst(pos, color, 10, 110, 0.35, 2)
        fx.shake(2, 0.15)
        for e in self.play.room.enemies:
            if not e.dead and e.spawn_t <= 0 and e.pos.distance_to(pos) <= radius + e.radius:
                self._hit(e, dmg, pos, 140)

    # ------------------------------------------------------------------ хуки боя
    def on_shot(self, shots, aim):
        """Выстрел игрока: Змеиный зуб, Топор Перуна, огненный след Пылающего меча."""
        p = self.play.player
        f = p.flags
        out = list(shots)
        if not out:
            return out
        luck = max(0.0, p.stats["luck"])
        if "fang" in f and out[0].kind != "swing" and random.random() < min(0.45, 0.2 + luck * 0.015):
            base = out[0]
            out = [self._clone(base, _rot(base.vel, a), 0.55, 2.5) for a in (-0.24, 0.0, 0.24)] + out[1:]
        if "perun" in f:
            self.perun_n += 1
            if self.perun_n % 5 == 0:
                self._perun_strike()
            else:
                for s in out:
                    s.damage *= 0.9   # цена Топора: обычные атаки слабее
        if "flame_trail" in f:
            if "flame_seraph" in f:   # с Крыльями серафима след становится широкой дугой пламени
                self._flame_arc(aim)
            else:
                for s in out:
                    s.trail = "fire"
        return out

    @staticmethod
    def _clone(base, vel, dmg_mult, radius):
        return Projectile(base.pos, vel, base.damage * dmg_mult, base.life, radius, True, base.color, pierce=base.pierce,
                          knockback=base.knockback * 0.6, explode=base.explode, poison=base.poison, kind=base.kind,
                          homing=base.homing)

    def _perun_strike(self):
        p, room = self.play.player, self.play.room
        alive = self._alive()
        if not alive:
            self.perun_n -= 1   # молнии не по кому бить: считаем эту атаку заново
            return
        target = min(alive, key=lambda e: e.pos.distance_to(p.pos))
        self._strike(target.pos, max(6.0, p.stats["damage"] * 2.5), 26, (150, 200, 255))
        self.play.sfx("nuke")
        if "veles_perun" in p.flags and random.random() < 0.35:   # Посох Велеса: молния оставляет монеты
            from ..world.room import Pickup
            for _ in range(2):
                room.pickups.append(Pickup("coin", target.pos, 1))

    def _flame_arc(self, aim):
        p = self.play.player
        base = max(0.8, p.stats["damage"] * 0.24)
        for a in (-0.75, -0.38, 0.0, 0.38, 0.75):
            for dist in (24, 40):
                self._patch(p.pos + _rot(aim, a) * dist, 8.0, 1.0, base)

    def on_hit(self, pr, e):
        """Снаряд игрока попал во врага: заморозка, окаменение, поджог."""
        p = self.play.player
        f = p.flags
        luck = max(0.0, p.stats["luck"]) * 0.01
        if "morana" in f and random.random() < 0.14 + luck:
            self._freeze(e, 2.0, "ice")
        if "medusa" in f and random.random() < 0.12 + luck:
            self._freeze(e, 2.5, "stone")
        if "prometheus" in f and random.random() < 0.2 + luck:
            self._ignite(e)

    def on_contact(self, e):
        """Враг касается игрока: Терновый венец возвращает урон (не чаще раза в 0.6 с на врага)."""
        if "thorns" not in self.flags or self.t < getattr(e, "_thorn_cd", 0.0):
            return
        e._thorn_cd = self.t + 0.6
        p = self.play.player
        self._hit(e, max(1.0, p.stats["damage"] * 0.6), p.pos, 120)
        self.play.game.effects.burst(e.pos, (170, 215, 90), 3, 50, 0.2)

    def on_kill(self, e):
        """Враг убит: волна Семи печатей."""
        if "seven_seals" not in self.flags:
            return
        self.seal_kills += 1
        if self.seal_kills % 7:
            return
        p = self.play.player
        book = "seals_book" in p.flags
        dmg = max(4.0, p.stats["damage"] * 2.0) * (1.5 if book else 1.0)
        self._wave(p.pos, LIGHT, 170 if book else 140, 300, dmg)
        if book:
            self._wave(p.pos, LIGHT, 170, 300, dmg, delay=0.45)
        self.play.game.effects.flash(LIGHT, 0.2)
        self.play.sfx("story")
        self._note("Печать сломана: волна света!", "gold", 2)
        self._buff("speed", "mul", 0.7, 3.0)   # цена: потеря скорости

    def kill_loot(self, e):
        """Дополнительные монеты с убитого врага (Тридцать сребреников, Посох Велеса)."""
        f = self.flags
        extra = 0
        if "silver" in f and random.random() < 0.55:
            extra += 1
        if "veles" in f and random.random() < 0.3:
            extra += 1
        if extra:
            from ..world.room import Pickup
            for _ in range(extra):
                self.play.room.pickups.append(Pickup("coin", e.pos, 1))

    def coin_bonus(self):
        """Прибавка к шансу выпадения монеты (Посох Велеса)."""
        return 0.15 if "veles" in self.flags else 0.0

    def on_hurt(self):
        if "achilles" in self.flags:   # цена Поножей: после удара пропадает бонус скорости
            self._buff("speed", "mul", 1 / 1.3, 4.0)

    def on_purchase(self, price):
        """Покупка: Тридцать сребреников отнимают здоровье (или, с Весами, ослабляют врагов)."""
        if price <= 0 or "silver" not in self.flags:
            return
        p = self.play.player
        if "silver_scales" in p.flags:
            self.play.slow_t = max(self.play.slow_t, 4.0)
            self._note("Весы взвесили серебро: враги замедлены.", "blue", 2.5)
            return
        loss = max(1, int(math.ceil(p.max_hp * 0.08)))
        p.floor_mods.append(("max_hp", "add", -loss))
        p.recompute()
        self._note("Сребреники жгут руки: макс. здоровье снижено до конца этажа.", "red", 3)

    # ------------------------------------------------------------------ щит, спасение, невидимость
    def try_absorb(self):
        """Скрижали Завета: щит поглощает один удар."""
        if not self.shield_ready or "tablets" not in self.flags:
            return False
        self.shield_ready = False
        self.shield_t = 0.0
        self.absorb_msg = "Скрижали Завета поглотили удар!"
        self._buff("speed", "mul", 0.75, 3.0)   # цена: скорость после разрушения щита
        return True

    def pop_absorb_msg(self):
        msg, self.absorb_msg = self.absorb_msg, None
        return msg

    def try_survive(self, amount):
        """Смертельный удар: Игла Кощея (раз за этаж) или «Цена бессмертия» (раз за забег)."""
        p = self.play.player
        f = p.flags
        if "needle" in f and not self.needle_used:
            self.needle_used = True
            p.hp = 1
            self._buff("max_hp", "add", -2, 60.0)   # цена: макс. здоровье падает на минуту
            self._rescued("Игла Кощея спасла тебя, но ты ослаб.")
            return True
        if "immortality" in f and not self.immortality_used:
            self.immortality_used = True
            p.hp = 2
            self.disabled |= {"koschei_needle", "holy_grail", "hades_helm"}   # цена: предметы теряют силу до конца этажа
            p.recompute()
            p.hp = min(2, p.max_hp)
            self._rescued("Цена бессмертия уплачена: три предмета потеряли силу.")
            return True
        return False

    def _rescued(self, text):
        fx = self.play.game.effects
        fx.flash((200, 255, 255), 0.4)
        fx.burst(self.play.player.pos, (200, 255, 255), 20, 120, 0.6, 3)
        self.play.sfx("story")
        self._note(text, "gold", 4)

    def _end_invisibility(self):
        p = self.play.player
        if "charon_hades" in p.flags:   # Монета Харона: выход из невидимости выпускает волну духов
            self._wave(p.pos, GHOST, 170, 260, max(6.0, p.stats["damage"] * 2.0))
            self.play.sfx("story")

    # ------------------------------------------------------------------ полёт
    def on_dash(self):
        """Игрок начал уклонение/полёт."""
        p = self.play.player
        f = p.flags
        if "hermes_icarus" in f:   # быстрое перемещение оставляет воздушный снаряд
            d = p.dodge_dir.normalize() if p.dodge_dir.length_squared() else p.aim
            self.play.pshots.append(Projectile(p.pos + d * 8, d * 300, max(2.0, p.stats["damage"] * 1.2), 0.7, 5, True,
                                               (190, 230, 255), pierce=True, knockback=120))
        self._last_fly_pos = None

    def on_land(self):
        """Полёт закончился: цена Крыльев."""
        p = self.play.player
        f = p.flags
        fx = self.play.game.effects
        fx.burst(p.pos, (220, 220, 230), 6, 60, 0.3, 2)
        if "seraph" in f:
            self._buff("speed", "mul", 0.7, 2.0)
        if "fall_heaven" in f:
            self._buff("speed", "mul", 0.65, 3.0)
        if "icarus" in f:
            self.heat += p.DODGE_TIME * p.FLIGHT_MULT
            if self.heat > self.FLIGHT_HEAT_LIMIT:
                self.heat = 0.0
                self._buff("speed", "mul", 0.7, 3.0)
                self._note("Солнце опалило крылья: ты замедлен.", "red", 2.5)

    # ------------------------------------------------------------------ комнаты и этажи
    def on_room_enter(self):
        play = self.play
        d, pos = play.dungeon, play.dungeon.pos
        if d is not self.cur_dungeon:
            self.cur_dungeon, self.cur_pos, self.prev_pos = d, pos, None
        elif pos != self.cur_pos:
            self.prev_pos, self.cur_pos = self.cur_pos, pos
        self.waves.clear()
        self.patches.clear()
        self.bolts.clear()
        self.mortars.clear()
        self.curse_haste = False
        if self.spirit is not None:
            self.spirit["pos"] = pygame.Vector2(play.player.pos)

    def on_zone_change(self):
        self.reset_floor()
        self.prev_pos = None

    def on_room_clear(self):
        """Комната зачищена: награда Домового оберега."""
        play, p = self.play, self.play.player
        if "domovoi" not in p.flags:
            return
        chance = 0.15 + max(0.0, p.stats["luck"]) * 0.02
        if p.hp * 3 <= p.max_hp:
            chance *= 0.4   # цена: при низком здоровье домовой скуп
        if random.random() >= chance:
            return
        from ..world.room import Pickup, CENTER
        roll = random.random()
        if roll < 0.5:
            for _ in range(random.randint(2, 4)):
                play.room.pickups.append(Pickup("coin", CENTER, 1))
        elif roll < 0.8:
            play.room.pickups.append(Pickup("heart", CENTER))
        else:
            pool = [i for i in play.db.regular_ids() if i not in p.inv.items]
            if pool:
                play.room.pickups.append(Pickup("item", CENTER, random.choice(pool)))
            else:
                play.room.pickups.append(Pickup("heart", CENTER))
        play.sfx("pickup")
        self._note("Домовой оставил подарок.", "gold", 2.5)

    def on_boss_dead(self, boss):
        """Босс убит: Святой Грааль полностью лечит; Монета Харона в паре с Шлемом шлёт призрачную атаку."""
        p = self.play.player
        if "grail" in p.flags and p.hp < p.max_hp:
            p.hp = p.max_hp
            self.play.game.effects.flash((255, 240, 170), 0.4)
            self._note("Святой Грааль исцелил тебя.", "gold", 3)
        if "charon_hades" in p.flags and "charon" in p.flags:
            self._wave(boss.pos, GHOST, 200, 240, 0.0)

    def charon_roll(self):
        """Монета Харона: None — предмета нет, 'ok' — награда удвоена, 'fail' — монета заняла место награды."""
        if "charon" not in self.flags:
            return None
        return "ok" if random.random() < 0.7 else "fail"

    # ------------------------------------------------------------------ опасные зоны (Венок русалки)
    @staticmethod
    def _small(h):
        rect = getattr(h, "rect", h if isinstance(h, pygame.Rect) else None)
        return rect is not None and rect.w * rect.h <= SMALL_HAZARD_AREA

    def hazard_immune(self, h):
        return "rusalka" in self.flags and getattr(h, "kind", "zone") in ("drop", "blast", "zone") and self._small(h)

    def hazard_extra(self, h):
        """Цена Венка: крупные зоны бьют на 1 сильнее."""
        return 1 if "rusalka" in self.flags and not self.hazard_immune(h) else 0

    def zone_immune(self, rect):
        return "rusalka" in self.flags and self._small(rect)

    # ------------------------------------------------------------------ обновление
    def update(self, dt):
        self.t += dt
        p, f = self.play.player, self.play.player.flags
        self.lock_t = max(0.0, self.lock_t - dt)
        if self.invis_t > 0:
            self.invis_t -= dt
            if self.invis_t <= 0:
                self.invis_t = 0.0
                self._end_invisibility()
        self.heat = max(0.0, self.heat - 0.35 * dt)
        enemies = self._alive()
        self._update_shield(dt, f)
        self._update_firebird(dt, f, enemies)
        self._update_prometheus(dt, f, enemies)
        self._update_leshy(dt, f, enemies)
        self._update_trails(dt, f)
        self._update_waves(dt)
        self._update_patches(dt)
        self._update_mortars(dt)
        self._update_burns(dt)
        for b in self.bolts:
            b["t"] += dt
        self.bolts = [b for b in self.bolts if b["t"] < b["dur"]]
        self.refresh()

    def _update_shield(self, dt, f):
        if "tablets" not in f:
            self.shield_t, self.shield_ready = 0.0, False
            return
        if not self.shield_ready:
            self.shield_t += dt
            if self.shield_t >= 10.0:
                self.shield_ready = True
                self._note("Скрижали Завета: щит готов.", "blue", 2)

    def _update_firebird(self, dt, f, enemies):
        if "firebird" not in f or not enemies:
            return
        self.feather_t -= dt
        if self.feather_t > 0:
            return
        self.feather_t = 15.0
        p, room = self.play.player, self.play.room
        radius = 130.0
        self._wave(p.pos, FIRE, radius, 240, max(4.0, p.stats["damage"] * 1.5), fire=True)
        self.play.game.effects.flash((255, 160, 60), 0.2)
        self.play.sfx("nuke")
        burned = 0
        for pk in room.pickups:   # цена: волна сжигает часть выпавшей добычи
            if pk.kind in ("coin", "heart") and pk.pos.distance_to(p.pos) <= radius and random.random() < 0.35:
                pk.dead = True
                burned += 1
                self.play.game.effects.burst(pk.pos, FIRE, 5, 60, 0.3, 2)
        if burned:
            self._note("Огненная волна сожгла часть добычи.", "red", 2.5)

    def _update_prometheus(self, dt, f, enemies):
        if "prometheus" not in f or not enemies:
            return
        self.burn_self_t -= dt
        if self.burn_self_t > 0:
            return
        self.burn_self_t = random.uniform(18.0, 24.0)
        p = self.play.player
        if p.hp > 1 and p.hurt(1, p.pos):   # собственный огонь ранит, но не убивает
            self.play._on_player_hurt()
            self._note("Огонь Прометея обжёг тебя.", "red", 2)

    def _update_leshy(self, dt, f, enemies):
        if "leshy" not in f:
            self.spirit = None
            return
        play, p = self.play, self.play.player
        if self.spirit is None:
            self.spirit = {"pos": pygame.Vector2(p.pos), "cd": 1.5}
        s = self.spirit
        home = p.pos + pygame.Vector2(-16, -14 + math.sin(self.t * 3.0) * 2)
        s["pos"] += (home - s["pos"]) * min(1.0, 6.0 * dt)
        s["cd"] -= dt
        if s["cd"] > 0:
            return
        if enemies:
            target = min(enemies, key=lambda e: e.pos.distance_to(s["pos"]))
            d = target.pos - s["pos"]
            if d.length_squared() > 0 and len(play.pshots) < play.cfg["max_player_projectiles"]:
                play.pshots.append(Projectile(s["pos"], d.normalize() * 210, max(1.5, p.stats["damage"] * 0.8), 1.2, 3, True,
                                              (120, 225, 110), knockback=50))
            s["cd"] = 1.6
            return
        s["cd"] = 2.5   # цена: в пустых комнатах дух иногда бьёт случайные предметы вокруг
        if random.random() < 0.4:
            loot = [pk for pk in play.room.pickups if pk.kind in ("coin", "heart")]
            if loot:
                pk = random.choice(loot)
                pk.dead = True
                play.game.effects.burst(pk.pos, (120, 225, 110), 6, 70, 0.3, 2)
                self._note("Леший разгулялся и испортил добычу.", "red", 2.5)
            else:
                play.game.effects.burst(s["pos"] + pygame.Vector2(random.uniform(-40, 40), random.uniform(-20, 30)),
                                        (120, 225, 110), 6, 60, 0.3, 2)

    def _update_trails(self, dt, f):
        p = self.play.player
        for pr in self.play.pshots:   # огненный след Пылающего меча
            if getattr(pr, "trail", None) and not pr.dead:
                pr._acc = getattr(pr, "_acc", 0.0) + pr.vel.length() * dt
                while pr._acc >= 10.0:
                    pr._acc -= 10.0
                    self._patch(pr.pos, 6.0, 1.2)
        if p.flying and ("fall_heaven" in f or "flame_seraph" in f):   # след в полёте
            if self._last_fly_pos is None or p.pos.distance_to(self._last_fly_pos) >= 9:
                self._last_fly_pos = pygame.Vector2(p.pos)
                strong = "fall_heaven" in f
                self._patch(p.pos, 8.0 if strong else 6.0, 1.7 if strong else 1.2,
                            max(0.9, p.stats["damage"] * (0.3 if strong else 0.2)), True,
                            (255, 220, 120) if strong else (255, 120, 40))
        elif not p.flying:
            self._last_fly_pos = None

    def _update_waves(self, dt):
        room = self.play.room
        for w in self.waves:
            if w["delay"] > 0:
                w["delay"] -= dt
                continue
            w["r"] += w["speed"] * dt
            if w["dmg"] > 0:
                for e in room.enemies:
                    if e.dead or e.spawn_t > 0 or id(e) in w["hit"]:
                        continue
                    if e.pos.distance_to(w["pos"]) <= w["r"] + e.radius:
                        w["hit"].add(id(e))
                        self._hit(e, w["dmg"], w["pos"], 160, w["fire"])
        self.waves = [w for w in self.waves if w["r"] < w["max"]]

    def _update_patches(self, dt):
        room = self.play.room
        for pt in self.patches:
            pt["t"] -= dt
            pt["tick"] -= dt
            if pt["tick"] <= 0:
                pt["tick"] = 0.3
                for e in room.enemies:
                    if not e.dead and e.spawn_t <= 0 and e.pos.distance_to(pt["pos"]) <= pt["r"] + e.radius:
                        self._hit(e, pt["dmg"], pt["pos"], 0.0, pt["fire"])
        self.patches = [pt for pt in self.patches if pt["t"] > 0]

    def _update_mortars(self, dt):
        room, fx = self.play.room, self.play.game.effects
        for m in self.mortars:
            m["pos"] += m["vel"] * dt
            m["t"] -= dt
            m["puff"] -= dt
            if m["puff"] <= 0:
                m["puff"] = 0.08
                fx.burst(m["pos"], BONE, 2, 40, 0.25, 2)
            for k in list(m["cd"]):
                m["cd"][k] -= dt
                if m["cd"][k] <= 0:
                    del m["cd"][k]
            for e in room.enemies:
                if e.dead or e.spawn_t > 0 or id(e) in m["cd"]:
                    continue
                if e.pos.distance_to(m["pos"]) <= 16 + e.radius:
                    m["cd"][id(e)] = 0.45
                    self._hit(e, m["dmg"], m["pos"], 240)
            self.play.eshots = [s for s in self.play.eshots if s.pos.distance_to(m["pos"]) > 16]
        self.mortars = [m for m in self.mortars if m["t"] > 0]

    def _update_burns(self, dt):
        for e in self.play.room.enemies:
            if getattr(e, "burn_t", 0.0) > 0 and not e.dead:
                e.burn_t -= dt
                e.take_damage(e.burn_dps * dt)

    # ------------------------------------------------------------------ активные предметы
    def use_active(self, kind):
        """Применить активный предмет 1.1.0. True — применён (запускается перезарядка)."""
        handler = getattr(self, "_use_" + kind, None)
        return bool(handler and handler())

    def _use_prophecy(self):
        """Книга Откровения: случайное пророчество, иногда ложное."""
        p, fx = self.play.player, self.play.game.effects
        fx.flash((200, 170, 255), 0.35)
        self.play.sfx("story")
        if "seals_book" not in p.flags and random.random() < 0.25:
            stat, op, value = random.choice((("damage", "mul", 0.6), ("speed", "mul", 0.65), ("fire_delay", "mul", 1.5)))
            self._buff(stat, op, value, 10.0)
            self._note(PROPHECY_FALSE, "red", 3.5)
            return True
        kind = random.choice(("smite", "heal", "bless"))
        if kind == "smite":
            dmg = max(12.0, p.stats["damage"] * 3.0)
            for e in self._alive():
                self._hit(e, dmg, p.pos, 120)
            fx.shake(4, 0.3)
            self._note(PROPHECY_SMITE, "gold", 3)
        elif kind == "heal":
            p.heal(4)
            self._note(PROPHECY_HEAL, "green", 3)
        else:
            self._buff("damage", "mul", 1.5, 12.0)
            self._buff("fire_delay", "mul", 0.75, 12.0)
            self._note(PROPHECY_BLESS, "gold", 3)
        return True

    def _use_mortar(self):
        """Костяная ступа: проезжает через комнату вдоль линии прицела."""
        p = self.play.player
        d = p.aim.normalize() if p.aim.length_squared() else pygame.Vector2(1, 0)
        self.mortars.append({"pos": p.pos - d * 230, "vel": d * 230, "t": 2.5, "puff": 0.0, "cd": {},
                             "dmg": max(6.0, p.stats["damage"] * 2.0)})
        self.lock_t = max(self.lock_t, 3.0)   # цена: 3 с нельзя атаковать
        self.play.sfx("nuke")
        self._note("Ступа вылетела! Атаковать нельзя 3 с.", "gold", 2.5)
        return True

    def _use_helm(self):
        """Шлем Аида: невидимость; враги теряют тебя, но и ты не можешь наносить урон."""
        self.invis_t = 4.0
        self.play.game.effects.burst(self.play.player.pos, (120, 120, 170), 14, 80, 0.5, 2)
        self.play.sfx("story")
        self._note("Ты невидим 4 с, но не можешь атаковать.", "blue", 2.5)
        return True

    def _use_thread(self):
        """Нить Ариадны: вернуться в предыдущую комнату."""
        play = self.play
        if play.room.locked or play.boss() is not None or play.zone.get("arena"):
            self._note("Нить не тянется во время боя.", "grey", 2.5)
            return False
        prev = self.prev_pos
        if prev is None or prev == play.dungeon.pos or prev not in play.dungeon.specs:
            self._note("Позади нет комнаты, куда можно вернуться.", "grey", 2.5)
            return False
        play.dungeon.visited.add(prev)
        play.dungeon.pos = prev
        play._swap_room(prev)
        play.game.effects.flash((255, 160, 170), 0.25)
        play.sfx("door")
        self._buff("speed", "mul", 0.7, 4.0)   # цена: замедление после возвращения
        self._note("Нить вернула тебя в прошлую комнату.", "gold", 2.5)
        return True

    def _use_zeus(self):
        """Молния Зевса: удар по линии прицела. С Топором Перуна расщепляется, с «Судом трёх богов» бьёт всю комнату."""
        play, p, fx = self.play, self.play.player, self.play.game.effects
        d = p.aim.normalize() if p.aim.length_squared() else pygame.Vector2(1, 0)
        start = p.pos + d * 6
        base = max(14.0, p.stats["damage"] * 4.0)
        f = p.flags
        lines = [(d, 1.0)]
        if "zeus_perun" in f or "three_gods" in f:
            lines += [(_rot(d, a), 0.7) for a in (-0.5, 0.5)]
        for dirv, mult in lines:
            end = start + dirv * 520
            self._bolt(start - pygame.Vector2(0, 0), end, (255, 245, 150), 0.4)
            for e in self._alive():
                if dist_point_segment(e.pos, start, end) <= e.radius + 10:
                    self._hit(e, base * mult, start, 220)
                    if "zeus_perun" in f:   # расщепление: добивает врагов вокруг поражённого
                        for other in self._alive():
                            if other is not e and other.pos.distance_to(e.pos) <= 48:
                                self._hit(other, base * 0.4, e.pos, 100)
        if "three_gods" in f:   # Суд трёх богов: цепная атака по почти всей комнате
            for e in self._alive():
                self._strike(e.pos, base * 0.9, 30, (255, 250, 200))
            self._wave(p.pos, LIGHT, 320, 420, base * 0.5)
            self._buff("speed", "mul", 0.6, 5.0)   # цена: скорость временно падает
            self._note("Суд трёх богов!", "gold", 3)
        fx.flash((255, 250, 200), 0.35)
        fx.shake(5, 0.35)
        play.sfx("nuke")
        self.lock_t = max(self.lock_t, 2.5)   # цена: 2.5 с нельзя атаковать
        return True

    def _use_pandora(self):
        """Ящик Пандоры: случайный эффект — добрый, смешанный (дар + проклятие) или злой."""
        play, p, fx = self.play, self.play.player, self.play.game.effects
        fx.flash((220, 180, 255), 0.4)
        play.sfx("story")
        outcomes = (
            (1.0, "heal", None), (1.0, "gold", None), (0.7, "gift", None), (1.0, "might", None), (1.0, "swift", None),
            (0.8, "wrath", "haste"), (0.8, "greed", "foes"), (0.8, None, "plague"),
        )
        _, good, bad = random.choices(outcomes, weights=[o[0] for o in outcomes])[0]
        if good == "heal":
            p.heal(p.max_hp)
            self._note("Ящик Пандоры: исцеление!", "green", 3)
        elif good == "gold":
            play.add_coins(8)
            self._note("Ящик Пандоры: золотой дождь!", "gold", 3)
        elif good == "gift":
            self._note("Ящик Пандоры: редкий дар!", "gold", 3)
            play.give_random_item()
        elif good == "might":
            self._buff("damage", "mul", 1.5, 30.0)
            self._note("Ящик Пандоры: сила титанов (30 с).", "gold", 3)
        elif good == "swift":
            self._buff("speed", "mul", 1.3, 30.0)
            self._buff("fire_delay", "mul", 0.7, 30.0)
            self._note("Ящик Пандоры: быстрые руки и ноги (30 с).", "gold", 3)
        elif good == "wrath":
            for e in self._alive():
                self._hit(e, 12.0, p.pos, 140)
            fx.shake(4, 0.3)
            self._note("Ящик Пандоры: гнев богов!", "gold", 3)
        elif good is None and bad == "plague":
            self._note("Ящик Пандоры: беды выпорхнули наружу!", "red", 3)
        if good == "greed":
            play.add_coins(15)
            self._note("Ящик Пандоры: жадность вознаграждена.", "gold", 3)
        if bad:
            if "pandora_ariadne" in p.flags and self.undo_ready:
                self.undo_ready = False   # Нить Ариадны: проклятие отменено, награда осталась
                self._note("Нить Ариадны отменила проклятие!", "green", 3.5)
            else:
                self._curse(bad)
        return True

    def _curse(self, kind):
        """Проклятие комнаты."""
        play, p = self.play, self.play.player
        room = play.room
        can_spawn = room.kind not in ("boss", "miniboss") and not play.zone.get("arena") and bool(play.zone.get("enemy_pool"))
        if kind in ("foes", "plague") and can_spawn:
            pool = play.zone["enemy_pool"]
            kinds, weights = [k for k, _ in pool], [w for _, w in pool]
            play.spawn(random.choices(kinds, weights=weights)[0], 3 if kind == "plague" else 2)
            self._note("Проклятие: из ящика вылезли враги!", "red", 3)
        else:
            self.curse_haste = True
            self._note("Проклятие комнаты: враги ускорились.", "red", 3)
        if kind == "plague":
            self._buff("damage", "mul", 0.7, 25.0)

    # ------------------------------------------------------------------ отрисовка
    def draw(self, surf, off, sprites):
        play, p, room = self.play, self.play.player, self.play.room
        ox, oy = off.x, off.y
        ticks = pygame.time.get_ticks()
        for i, pt in enumerate(self.patches):
            c = (int(pt["pos"].x + ox), int(pt["pos"].y + oy))
            k = max(0.0, min(1.0, pt["t"] / pt["life"]))
            col = tuple(int(v * (0.5 + 0.5 * k)) for v in pt["color"])
            pygame.draw.circle(surf, col, c, max(2, int(pt["r"] * (0.5 + 0.5 * k))))
            pygame.draw.circle(surf, (255, 235, 150), (c[0] + (ticks // 90 + i) % 3 - 1, c[1] - (ticks // 110 + i) % 3),
                               max(1, int(pt["r"]) // 3))
        for w in self.waves:
            if w["delay"] > 0:
                continue
            c = (int(w["pos"].x + ox), int(w["pos"].y + oy))
            pygame.draw.circle(surf, w["color"], c, int(w["r"]), 3)
            pygame.draw.circle(surf, (255, 255, 255), c, max(1, int(w["r"] * 0.9)), 1)
        for m in self.mortars:
            if self._mortar_img is None:
                img = sprites.icon("bone_mortar")
                self._mortar_img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            surf.blit(self._mortar_img, self._mortar_img.get_rect(center=(int(m["pos"].x + ox), int(m["pos"].y + oy))))
        if self.spirit is not None and "leshy" in p.flags:
            s = self.spirit["pos"]
            c = (int(s.x + ox), int(s.y + oy))
            pygame.draw.circle(surf, (50, 130, 64), c, 5)
            pygame.draw.circle(surf, (140, 235, 120), c, 4)
            pygame.draw.circle(surf, (255, 255, 230), (c[0] - 1, c[1] - 1), 1)
        if self.shield_ready and "tablets" in p.flags:
            c = (int(p.pos.x + ox), int(p.pos.y + oy))
            pygame.draw.circle(surf, LIGHT if ticks // 120 % 2 else (190, 200, 255), c, int(p.RADIUS) + 7, 1)
        for e in room.enemies:
            if getattr(e, "frozen_t", 0.0) > 0:
                col = (150, 210, 255) if getattr(e, "frozen_kind", "ice") == "ice" else (150, 150, 160)
                r = int(e.radius) + 3
                veil = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(veil, col + (110,), (r, r), r)
                surf.blit(veil, (int(e.pos.x + ox) - r, int(e.pos.y + oy) - r))
                pygame.draw.circle(surf, col, (int(e.pos.x + ox), int(e.pos.y + oy)), r, 1)
            if getattr(e, "burn_t", 0.0) > 0 and not e.dead:
                pygame.draw.circle(surf, FIRE, (int(e.pos.x + ox), int(e.pos.y + oy - e.radius - 2 + ticks // 100 % 3)), 2)
        for b in self.bolts:
            pts = [(int(q.x + ox), int(q.y + oy)) for q in b["pts"]]
            pygame.draw.lines(surf, b["color"], False, pts, 3)
            pygame.draw.lines(surf, (255, 255, 255), False, pts, 1)
