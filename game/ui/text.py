"""Текст: шрифты с поддержкой кириллицы, перенос строк, тень, перевод и кэши.

Каждый вызов draw_text/wrap переводит строку на текущий язык (game/i18n.py). Отрисованные строки и результаты
переноса кэшируются: раньше каждый кадр текст рендерился заново (и ещё раз для тени), это самая частая работа HUD и меню.
"""
import pygame

from ..i18n import tr

_cache = {}
_render_cache = {}   # (текст, размер, цвет, тень) -> (картинка, картинка тени)
_wrap_cache = {}     # (текст, ширина, размер) -> список строк
RENDER_CACHE_LIMIT = 800
WRAP_CACHE_LIMIT = 600
SHADOW_COLOR = (20, 12, 30)
COLORS = {"white": (245, 240, 230), "gold": (255, 215, 90), "red": (255, 100, 100),
          "green": (140, 240, 120), "grey": (150, 145, 165), "blue": (140, 190, 255)}


def font(size=11):
    if size not in _cache:
        f = None
        for name in ("segoeui", "arial", "dejavusans", "liberationsans"):
            path = pygame.font.match_font(name, bold=True)
            if path:
                f = pygame.font.Font(path, size)
                break
        _cache[size] = f or pygame.font.Font(None, size + 6)
    return _cache[size]


def clear_caches():
    """Сбросить кэши текста (после смены языка тексты в них уже не актуальны)."""
    _render_cache.clear()
    _wrap_cache.clear()


def _rendered(text, size, col, shadow):
    key = (text, size, col, shadow)
    hit = _render_cache.get(key)
    if hit is None:
        f = font(size)
        hit = (f.render(text, False, col), f.render(text, False, SHADOW_COLOR) if shadow else None)
        if len(_render_cache) >= RENDER_CACHE_LIMIT:
            _render_cache.clear()
        _render_cache[key] = hit
    return hit


def draw_text(surf, text, pos, color="white", size=11, anchor="topleft", shadow=True):
    text = tr(text)
    col = COLORS.get(color, color)
    img, shade = _rendered(text, size, tuple(col), shadow)
    rect = img.get_rect(**{anchor: pos})
    if shade is not None:
        surf.blit(shade, rect.move(1, 1))
    surf.blit(img, rect)
    return rect


def wrap(text, width, size=11):
    text = tr(text)
    key = (text, width, size)
    hit = _wrap_cache.get(key)
    if hit is None:
        f = font(size)
        lines, line = [], ""
        for word in text.split():
            trial = (line + " " + word).strip()
            if f.size(trial)[0] <= width:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        if len(_wrap_cache) >= WRAP_CACHE_LIMIT:
            _wrap_cache.clear()
        hit = _wrap_cache[key] = lines
    return list(hit)
