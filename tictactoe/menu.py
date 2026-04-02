from core.screen import SM
from core.game_menu import GameMenu
from .app import TicTacToeApp

# ══════════════════════════════════════════════════════════════════
#  TIC TAC TOE MENU
# ══════════════════════════════════════════════════════════════════

class TicTacToeMenu:
    """Pre-game menu for Tic Tac Toe. Returns 'back', 'quit', or launches app."""

    MODE_ITEMS = [
        {'label': '2D  vs Human',  'sub': 'Classic two-player on one board',
         'key': 'Enter', 'enabled': True},
        {'label': '2D  vs AI',     'sub': 'Challenge the computer in 2D',
         'key': 'Enter', 'enabled': True},
        {'label': '3D  vs Human',  'sub': 'Six-face cube — win 3 faces',
         'key': 'Enter', 'enabled': True},
        {'label': '3D  vs AI',     'sub': 'Take on the AI in 3D',
         'key': 'Enter', 'enabled': True},
        {'label': '3D  AI vs AI',  'sub': 'Watch two AIs battle it out',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_ITEMS = [
        {'label': 'Easy',   'sub': 'Random moves — great for beginners',
         'key': 'Enter', 'enabled': True},
        {'label': 'Medium', 'sub': 'Balanced challenge',
         'key': 'Enter', 'enabled': True},
        {'label': 'Hard',   'sub': 'Full minimax — good luck',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_KEYS = ['Easy', 'Medium', 'Hard']

    # Modes that need a difficulty selection
    AI_MODES = {1, 3, 4}   # indices into MODE_ITEMS

    def run(self):
        mode_menu = GameMenu(
            title    = "TIC  TAC  TOE",
            subtitle = "Select a game mode",
            items    = self.MODE_ITEMS,
            accent   = (120, 100, 255),
        )
        while True:
            result = mode_menu.run()
            if result in ('quit', 'back'):
                return result

            difficulty = 'Hard'   # default for non-AI modes
            if result in self.AI_MODES:
                diff_menu = GameMenu(
                    title    = self.MODE_ITEMS[result]['label'],
                    subtitle = "Select difficulty",
                    items    = self.DIFFICULTY_ITEMS,
                    accent   = (120, 100, 255),
                )
                diff_result = diff_menu.run()
                if diff_result == 'quit':
                    return 'quit'
                if diff_result == 'back':
                    continue
                difficulty = self.DIFFICULTY_KEYS[diff_result]

            # Build config and launch
            configs = [
                {'mode': '2D', 'opponent': 'human', 'difficulty': difficulty},
                {'mode': '2D', 'opponent': 'ai',    'difficulty': difficulty},
                {'mode': '3D', 'opponent': 'human', 'difficulty': difficulty},
                {'mode': '3D', 'opponent': 'ai',    'difficulty': difficulty},
                {'mode': '3D', 'opponent': 'ai_vs_ai', 'difficulty': difficulty},
            ]
            app = TicTacToeApp(configs[result])
            game_result = app.run()
            if game_result == 'quit':
                return 'quit'
            # 'menu' → loop back to show mode select again
            SM.set_title("Tic  Tac  Toe")
