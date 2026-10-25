"""Текст: шрифты с поддержкой кириллицы, перенос строк, тень."""
import pygame

_cache = {}
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


def draw_text(surf, text, pos, color="white", size=11, anchor="topleft", shadow=True):
    col = COLORS.get(color, color)
    f = font(size)
    img = f.render(text, False, col)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        surf.blit(f.render(text, False, (20, 12, 30)), rect.move(1, 1))
    surf.blit(img, rect)
    return rect


def wrap(text, width, size=11):
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
    return lines
