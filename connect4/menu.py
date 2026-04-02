import pygame

from core.screen import SM
from core.game_menu import GameMenu
from .app import Connect4App

# ── Connect 4 box art for the Launcher card ───────────────────────

def _art_connect4(surf, rect):
    surf.fill((8, 12, 28))
    # Grid lines
    for x in range(0, rect.w, 18):
        pygame.draw.line(surf, (14, 20, 44), (x, 0), (x, rect.h))
    for y in range(0, rect.h, 18):
        pygame.draw.line(surf, (14, 20, 44), (0, y), (rect.w, y))

    cols, rows = 7, 6
    cell = min(rect.w // cols, rect.h // (rows + 1))
    ox   = (rect.w - cols * cell) // 2
    oy   = rect.h - rows * cell - 4

    # Board
    pygame.draw.rect(surf, (18, 36, 90),
        (ox - 4, oy - 4, cols*cell + 8, rows*cell + 8), border_radius=8)

    # Sample board state
    board = [
        [0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0],
        [0,0,0,2,0,0,0],
        [0,0,1,1,0,0,0],
        [0,1,2,2,1,0,0],
        [1,2,1,2,2,1,0],
    ]
    colors = {1: (230,55,75), 2: (240,195,30)}
    for r in range(rows):
        for c in range(cols):
            cx = ox + c*cell + cell//2
            cy = oy + r*cell + cell//2
            rad = cell//2 - 3
            pygame.draw.circle(surf, (6, 10, 22), (cx, cy), rad)
            if board[r][c]:
                col = colors[board[r][c]]
                pygame.draw.circle(surf, col, (cx, cy), rad)
                hi = tuple(min(255,v+80) for v in col)
                pygame.draw.circle(surf, hi,
                    (cx - rad//4, cy - rad//4), rad//3)

    # Win line glow (diagonal)
    win_cells = [(5,0),(4,1),(3,2),(2,3)]
    for r, c in win_cells:
        cx = ox + c*cell + cell//2
        cy = oy + r*cell + cell//2
        rad = cell//2 - 3
        gs = pygame.Surface((rad*2+8, rad*2+8), pygame.SRCALPHA)
        pygame.draw.circle(gs, (255,255,180,140), (rad+4, rad+4), rad+3)
        surf.blit(gs, (cx-rad-4, cy-rad-4))

    # Glow at top
    glow = pygame.Surface((rect.w, 30), pygame.SRCALPHA)
    for i in range(30):
        a = max(0, 60 - i*3)
        pygame.draw.line(glow, (80, 140, 255, a), (0, i), (rect.w, i))
    surf.blit(glow, (0, 0))


# ══════════════════════════════════════════════════════════════════
#  CONNECT 4 MENU
# ══════════════════════════════════════════════════════════════════

class Connect4Menu:
    """Pre-game menu for Connect 4."""

    MODE_ITEMS = [
        {'label': 'vs Human', 'sub': 'Local two-player',
         'key': 'Enter', 'enabled': True},
        {'label': 'vs AI',    'sub': 'Challenge the computer',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_ITEMS = [
        {'label': 'Easy',   'sub': 'Plays randomly — great for beginners',
         'key': 'Enter', 'enabled': True},
        {'label': 'Medium', 'sub': 'Looks 4 moves ahead',
         'key': 'Enter', 'enabled': True},
        {'label': 'Hard',   'sub': 'Looks 7 moves ahead — brutal',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_KEYS = ['easy', 'medium', 'hard']

    def run(self):
        mode_menu = GameMenu(
            title    = "CONNECT  4",
            subtitle = "Select a game mode",
            items    = self.MODE_ITEMS,
            accent   = (80, 140, 255),
        )
        while True:
            result = mode_menu.run()
            if result in ('quit', 'back'):
                return result

            if result == 0:
                app = Connect4App({'opponent': 'human'})
                game_result = app.run()
                if game_result == 'quit':
                    return 'quit'
            elif result == 1:
                diff_menu = GameMenu(
                    title    = "vs AI",
                    subtitle = "Select difficulty",
                    items    = self.DIFFICULTY_ITEMS,
                    accent   = (80, 140, 255),
                )
                diff_result = diff_menu.run()
                if diff_result == 'quit':
                    return 'quit'
                if diff_result == 'back':
                    continue
                difficulty = self.DIFFICULTY_KEYS[diff_result]
                app = Connect4App({'opponent': 'ai', 'difficulty': difficulty})
                game_result = app.run()
                if game_result == 'quit':
                    return 'quit'

            SM.set_title("Connect 4")
