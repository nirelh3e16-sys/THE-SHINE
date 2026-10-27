"""Создание снарядов игрока и применение эффектов предметов в бою."""
import math
import random

import pygame

from ..entities.projectile import Projectile

TV_KINDS = ("normal", "fast", "big", "spread", "pierce")


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
    origin = player.pos + aim * 8
    pierce = "pierce" in flags
    explode = "explosive_shots" in flags and "heavy" in flags
    color = (255, 90, 90) if crit else (255, 240, 120)

    if "axe" in flags and allow_melee:   # широкий тяжёлый взмах
        return [Projectile(origin + aim * 8, aim * 150, dmg * 1.5, life, 16, True, color, pierce=True,
                           knockback=340, poison="toxic_sweep" in flags, kind="swing")]

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
                                    life * 0.6, 2.5, True, color, pierce, knock, explode))
        return shots
    if kind == "spread":
        for a in (-0.22, 0.0, 0.22):
            shots.append(Projectile(origin, _rot(aim, a) * speed, dmg * 0.6, life, radius, True, color, pierce, knock, explode))
    else:
        shots.append(Projectile(origin, aim * speed, dmg, life, radius, True, color, pierce, knock, explode))
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
