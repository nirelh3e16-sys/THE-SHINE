"""Иконка окна и панели задач (icon.ico рядом с игрой). Без файла — запасная иконка."""
import io
import struct

from .settings import ICON_PATHS

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def extract_ico_png(data):
    """Достаёт самое большое PNG-изображение из ICO (современные .ico хранят PNG). Иначе None."""
    try:
        reserved, kind, count = struct.unpack_from("<HHH", data, 0)
        if reserved != 0 or kind != 1:
            return None
        best = None
        for i in range(count):
            width, _h, _c, _r, _planes, _bits, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
            chunk = data[offset:offset + size]
            if chunk[:8] == PNG_MAGIC and (best is None or (width or 256) > best[0]):
                best = (width or 256, chunk)
        return best[1] if best else None
    except struct.error:
        return None


def _load_ico(path):
    import pygame
    try:  # SDL_image умеет читать ICO в большинстве сборок pygame
        return pygame.image.load(str(path))
    except (pygame.error, FileNotFoundError):
        pass
    try:
        png = extract_ico_png(path.read_bytes())
    except OSError:
        return None
    if png:
        try:
            return pygame.image.load(io.BytesIO(png), "icon.png")
        except pygame.error:
            return None
    return None


def _fallback_icon():
    import pygame
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (255, 235, 150), (2, 8, 28, 16), 2)
    pygame.draw.circle(s, (255, 255, 255), (16, 17), 7)
    pygame.draw.circle(s, (80, 140, 240), (16, 17), 4)
    pygame.draw.ellipse(s, (255, 215, 90), (8, 1, 16, 6), 2)
    return s


def apply_icon():
    """Вызывать до создания окна. True, если использован настоящий icon.ico."""
    import pygame
    for path in ICON_PATHS:
        if path.is_file():
            surf = _load_ico(path)
            if surf is not None:
                pygame.display.set_icon(surf)
                return True
    pygame.display.set_icon(_fallback_icon())
    return False
