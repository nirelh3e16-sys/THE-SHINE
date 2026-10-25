"""THE SHINE — точка входа. Запуск: python main.py"""
import sys
import traceback
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Не найден pygame. Установите: python -m pip install -r requirements.txt")
    sys.exit(1)


def main():
    if sys.platform == "win32":  # отдельный идентификатор приложения: в панели задач будет иконка игры
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FreeDomStudio.TheShine")
        except (AttributeError, OSError):
            pass
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    from game.app_icon import apply_icon
    apply_icon()
    try:
        from game.game import Game
        Game().run()
    except (pygame.error, OSError, ValueError, KeyError) as exc:
        from game.settings import SAVE_DIR
        log = SAVE_DIR / "crash.log"
        try:
            log.parent.mkdir(exist_ok=True)
            log.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        print(f"Ошибка: {exc}\nПодробности: {log}")
        sys.exit(1)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
