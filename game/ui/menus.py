"""Меню, журнал свидетельств и просмотр предметов."""
import math

import pygame

from .text import draw_text, wrap
from ..i18n import tr
from ..settings import GAME_W, GAME_H, SPR_DIR
from ..systems.morality import TESTIMONIES


_logo = None


def load_logo():
    """Логотип из spr/logo_big.png: обрезаем прозрачные поля и уменьшаем вдвое (исходник нарисован в 2x)."""
    global _logo
    if _logo is None:
        try:
            img = pygame.image.load(str(SPR_DIR / "logo_big.png")).convert_alpha()
            img = img.subsurface(img.get_bounding_rect()).copy()
            k = 2 if img.get_width() > 400 else 1
            _logo = pygame.transform.scale(img, (max(1, img.get_width() // k), max(1, img.get_height() // k)))
        except (pygame.error, FileNotFoundError, ValueError):
            _logo = False
    return _logo or None


class Menu:
    def __init__(self, title, entries, corner=False, top=120, step=22, title_y=50, logo=None):
        self.logo = logo   # картинка вместо текста названия
        self.title = title
        self.entries = entries  # [(label, callback)]
        self.selected = 0
        self.corner = corner    # True — название и кнопки прижаты к правому нижнему углу
        self.top, self.step, self.title_y = top, step, title_y

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.entries)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.entries)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self.entries[self.selected][1]()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos_game
            for i, (label, cb) in enumerate(self.entries):
                near_x = pos.x > GAME_W - 230 if self.corner else abs(pos.x - GAME_W / 2) < 90
                if abs(pos.y - self._y(i)) < 10 and near_x:
                    self.selected = i
                    cb()
                    break

    def _y(self, i):
        if self.corner:
            return GAME_H - 22 - (len(self.entries) - 1 - i) * 24
        return self.top + i * self.step

    def draw(self, surf):
        if self.corner:
            if self.logo is not None:   # логотип по центру сверху, слегка покачивается
                bob = int(math.sin(pygame.time.get_ticks() / 520) * 2)
                surf.blit(self.logo, self.logo.get_rect(center=(GAME_W // 2, 66 + bob)))
            else:
                draw_text(surf, self.title, (GAME_W - 14, self._y(0) - 22), "gold", 30, "bottomright")
            for i, (label, _) in enumerate(self.entries):
                sel = i == self.selected
                label = tr(label)
                draw_text(surf, (label + " <") if sel else label, (GAME_W - 14, self._y(i)),
                          "gold" if sel else "white", 15, "midright")
            return
        draw_text(surf, self.title, (GAME_W // 2, self.title_y), "gold", 26, "center")
        for i, (label, _) in enumerate(self.entries):
            sel = i == self.selected
            label = tr(label)
            draw_text(surf, ("> " if sel else "") + label + (" <" if sel else ""), (GAME_W // 2, self._y(i)),
                      "gold" if sel else "white", 14, "center")


def draw_journal(surf, db, tab, owned, testimonies, scroll=0):
    surf.fill((18, 12, 30))
    draw_text(surf, "ИНВЕНТАРЬ / ЖУРНАЛ", (GAME_W // 2, 8), "gold", 14, "midtop")
    draw_text(surf, ("[ПРЕДМЕТЫ]" if tab == 0 else " ПРЕДМЕТЫ ") + "   " +
              ("[СВИДЕТЕЛЬСТВА]" if tab == 1 else " СВИДЕТЕЛЬСТВА "), (GAME_W // 2, 28), "white", 11, "midtop")
    draw_text(surf, "Q/E — вкладка, Tab/Esc — закрыть", (GAME_W // 2, GAME_H - 6), "grey", 9, "midbottom")
    y = 46
    if tab == 0:
        if not owned:
            draw_text(surf, "Пока ничего нет.", (40, y), "grey")
        for item_id in owned:
            item = db.items[item_id]
            draw_text(surf, item.name, (40, y), "gold", 11)
            for line in wrap(item.desc, GAME_W - 80, 10):
                y += 11
                draw_text(surf, line, (48, y), "white", 10)
            y += 14
        for c in db.active_combos(owned):
            draw_text(surf, f"Комбо: {c['name']} — {c['desc']}", (40, y), "green", 10)
            y += 12
    else:
        if not testimonies:
            draw_text(surf, "Ничего не записано. Пока.", (40, y), "grey")
        for tid in testimonies[scroll:scroll + 7]:
            title, text = TESTIMONIES[tid]
            draw_text(surf, title, (40, y), "gold", 11)
            for line in wrap(text, GAME_W - 80, 10):
                y += 11
                draw_text(surf, line, (48, y), "white", 10)
            y += 14
