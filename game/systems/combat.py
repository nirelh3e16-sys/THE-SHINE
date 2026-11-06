"""Создание снарядов игрока и применение эффектов предметов в бою."""
import math
import random

import pygame

from ..entities.projectile import Projectile

TV_KINDS = ("normal", "fast", "big", "spread", "pierce")
HOMING_TURN = 5.0       # Старый пульт: насколько быстро снаряд поворачивает к цели, рад/с
HOMING_RANGE = 280.0    # дальше этого расстояния снаряд цель не «видит»
THORN_SPEED = 190.0     # скорость колючки из Колючки-пушки (Шипастая ярость ускоряет её)
THORN_FURY_SPEED = 1.7
THORN_LIFE = 1.2


def _rot(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return pygame.Vector2(v.x * c - v.y * s, v.x * s + v.y * c)


def build_player_shots(player, aim, rng=random, force_kind=None, allow_melee=True):
    """Возвращает список снарядов для одного выстрела с учётом предметов."""
    st, flags = player.stats, player.flags
    dmg, speed, life = st["damage"], st["shot_speed"], st["range"]
    crit = rng.random() < min(0.4, max(0.0, st["luck"]) * 0.04)
    if crit:
        dmg *= 2
    if "smg" in flags:   # небольшой разброс у автомата
        aim = _rot(aim, rng.uniform(-0.06, 0.06))
    origin = player.pos + aim * 8
    homing = "homing" in flags
    pierce = "pierce" in flags
    explode = "explosive_shots" in flags and "heavy" in flags
    color = (255, 90, 90) if crit else (255, 240, 120)

    if "axe" in flags and allow_melee:   # широкий тяжёлый взмах
        return [Projectile(origin + aim * 8, aim * 150, dmg * 1.5, life, 16, True, color, pierce=True,
                           knockback=340, poison="toxic_sweep" in flags, kind="swing")]
    if "bat" in flags and allow_melee:   # аналог топора: чуть меньше урон, сильнее отбрасывание
        return [Projectile(origin + aim * 8, aim * 150, dmg * 1.3, life, 14, True, color, pierce=True,
                           knockback=430, poison="toxic_sweep" in flags, kind="swing")]

    if "melee" in flags and allow_melee:
        return [Projectile(origin + aim * 6, aim * 160, dmg * 1.2, life, 12, True, color, pierce=True,
                           knockback=260, poison="toxic_sweep" in flags, kind="swing")]

    kind = force_kind or (rng.choice(TV_KINDS) if "random_shot" in flags else "normal")
    radius = 3.0
    knock = 60.0
    if "heavy" in flags:
        radius, knock, color = 5.0, 140.0, (200, 130, 80)
    shots = []
    if kind == "fast":
        speed, dmg = speed * 1.6, dmg * 0.8
    elif kind == "big":
        speed, dmg, radius = speed * 0.7, dmg * 1.6, 6.0
    elif kind == "pierce":
        pierce, color = True, (150, 220, 255)
    if "shotgun" in flags:   # пять дробин веером, короткая дальность
        for i in range(5):
            a = (i - 2) * 0.17 + rng.uniform(-0.04, 0.04)
            shots.append(Projectile(origin, _rot(aim, a) * speed * rng.uniform(0.9, 1.1), dmg * 0.55,
                                    life * 0.6, 2.5, True, color, pierce, knock, explode, homing=homing))
        return shots
    if kind == "spread":
        for a in (-0.22, 0.0, 0.22):
            shots.append(Projectile(origin, _rot(aim, a) * speed, dmg * 0.6, life, radius, True, color, pierce, knock, explode,
                                    homing=homing))
    else:
        shots.append(Projectile(origin, aim * speed, dmg, life, radius, True, color, pierce, knock, explode, homing=homing))
    return shots


def soldier_shot(player, origin, target_pos, rng=random):
    aim = (target_pos - origin)
    if aim.length_squared() == 0:
        return []
    aim = aim.normalize()
    kind = rng.choice(TV_KINDS) if "tv_soldier" in player.flags else "normal"
    shots = build_player_shots(player, aim, rng, force_kind=kind, allow_melee=False)
    for s in shots:
        s.pos = pygame.Vector2(origin)
        s.damage *= 0.5
    return shots


def steer_homing(pr, targets, dt):
    """Старый пульт: плавно поворачивает снаряд к ближайшему врагу, не меняя его скорость."""
    if not targets or pr.vel.length_squared() == 0:
        return
    target = min(targets, key=lambda e: e.pos.distance_squared_to(pr.pos))
    to = target.pos - pr.pos
    if to.length_squared() == 0 or to.length() > HOMING_RANGE:
        return
    speed = pr.vel.length()
    cur = math.atan2(pr.vel.y, pr.vel.x)
    diff = (math.atan2(to.y, to.x) - cur + math.pi) % math.tau - math.pi
    limit = HOMING_TURN * dt
    ang = cur + max(-limit, min(limit, diff))
    pr.vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * speed


def thorn_shot(player, origin, target_pos):
    """Выстрел Колючки-пушки по ближайшему врагу. С Шипастой яростью колючка быстрее и взрывается на исходе."""
    aim = pygame.Vector2(target_pos) - origin
    if aim.length_squared() == 0:
        return []
    fury = "thorn_fury" in player.flags
    speed = THORN_SPEED * (THORN_FURY_SPEED if fury else 1.0)
    dmg = max(1.5, player.stats["damage"] * 0.6)
    return [Projectile(origin, aim.normalize() * speed, dmg, THORN_LIFE, 3, True, (140, 225, 90), knockback=40.0,
                       kind="thorn", homing="homing" in player.flags, expire_explode=fury)]
