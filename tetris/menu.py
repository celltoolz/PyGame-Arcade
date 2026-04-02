from core.screen import SM
from core.game_menu import GameMenu
from .app import TetrisApp

# ══════════════════════════════════════════════════════════════════
#  TETRIS MENU
# ══════════════════════════════════════════════════════════════════

class TetrisMenu:
    """Pre-game menu for Tetris. Returns a config dict or 'back'/'quit'."""

    MODE_ITEMS = [
        {'label': 'Single Player', 'sub': 'Classic solo play',
         'key': 'Enter', 'enabled': True},
        {'label': 'vs AI',         'sub': 'Battle the computer',
         'key': 'Enter', 'enabled': True},
        {'label': 'Watch AI',      'sub': 'Sit back and watch the AI play',
         'key': 'Enter', 'enabled': True},
        {'label': '2 Player',      'sub': 'Coming soon — controller support',
         'key': '',      'enabled': False},
    ]

    DIFFICULTY_ITEMS = [
        {'label': 'Easy',   'sub': 'Relaxed pace, forgiving play',
         'key': 'Enter', 'enabled': True},
        {'label': 'Medium', 'sub': 'Balanced challenge',
         'key': 'Enter', 'enabled': True},
        {'label': 'Hard',   'sub': 'Fast and aggressive',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_KEYS = ['easy', 'medium', 'hard']

    def run(self):
        mode_menu = GameMenu(
            title    = "TETRIS",
            subtitle = "Select a game mode",
            items    = self.MODE_ITEMS,
            accent   = (0, 200, 180),
        )
        while True:
            result = mode_menu.run()
            if result in ('quit', 'back'):
                return result

            if result == 0:
                # Solo — no difficulty selection needed
                app = TetrisApp({'mode': 'solo'})
                game_result = app.run()
                if game_result == 'quit':
                    return 'quit'

            elif result == 1:
                # vs AI — show difficulty submenu
                diff_menu = GameMenu(
                    title    = "vs AI",
                    subtitle = "Select difficulty",
                    items    = self.DIFFICULTY_ITEMS,
                    accent   = (0, 200, 180),
                )
                diff_result = diff_menu.run()
                if diff_result == 'quit':
                    return 'quit'
                if diff_result == 'back':
                    continue
                difficulty = self.DIFFICULTY_KEYS[diff_result]
                app = TetrisApp({'mode': 'vs_ai', 'difficulty': difficulty})
                game_result = app.run()
                if game_result == 'quit':
                    return 'quit'

            elif result == 2:
                # Watch AI — show difficulty submenu
                diff_menu = GameMenu(
                    title    = "Watch AI",
                    subtitle = "Select difficulty",
                    items    = self.DIFFICULTY_ITEMS,
                    accent   = (0, 200, 180),
                )
                diff_result = diff_menu.run()
                if diff_result == 'quit':
                    return 'quit'
                if diff_result == 'back':
                    continue
                difficulty = self.DIFFICULTY_KEYS[diff_result]
                app = TetrisApp({'mode': 'watch', 'difficulty': difficulty})
                game_result = app.run()
                if game_result == 'quit':
                    return 'quit'

            SM.set_title("Tetris")
