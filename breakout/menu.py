import pygame

from core.screen import SM
from core.game_menu import GameMenu
from core.widgets import Slider
from .app import BreakoutApp
from .rival_app import RivalApp
from .game import BRICK_ROW_COLS


# ══════════════════════════════════════════════════════════════════
#  BREAKOUT BOX ART
# ══════════════════════════════════════════════════════════════════

def _art_breakout(surf, rect):
    """Neon breakout scene — partial brick grid, glowing ball, paddle."""
    W, H = rect.w, rect.h
    surf.fill((6, 8, 18))

    # Grid background
    for x in range(0, W, 18):
        pygame.draw.line(surf, (10, 13, 26), (x, 0), (x, H))
    for y in range(0, H, 18):
        pygame.draw.line(surf, (10, 13, 26), (0, y), (W, y))

    # Brick grid — top portion
    cols, rows = 8, 5
    bw   = (W - 4) // cols - 2
    bh   = 11
    gap  = 2
    top  = 8

    brick_layout = [
        [3, 3, 3, 3, 3, 3, 3, 3],
        [2, 2, 2, 2, 2, 2, 2, 2],
        [1, 1, 0, 1, 1, 0, 1, 1],
        [1, 0, 0, 1, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
    for r, row in enumerate(brick_layout):
        for c, hp in enumerate(row):
            if hp == 0:
                continue
            x = 2 + c * (bw + gap)
            y = top + r * (bh + gap)
            col = BRICK_ROW_COLS[r % len(BRICK_ROW_COLS)]
            pygame.draw.rect(surf, col, (x + 1, y + 1, bw - 2, bh - 2), border_radius=2)
            hi = tuple(min(255, v + 60) for v in col)
            pygame.draw.line(surf, hi, (x + 3, y + 2), (x + bw - 4, y + 2))

    # Ball with glow trail
    ball_x = W * 0.55
    ball_y = H * 0.58
    ball_r = 5
    trail_pts = [
        (ball_x - 18, ball_y + 14),
        (ball_x - 12, ball_y + 10),
        (ball_x - 7,  ball_y + 5),
    ]
    for ti, (tx, ty) in enumerate(trail_pts):
        a   = int(40 + ti * 35)
        tr  = max(1, ball_r - (len(trail_pts) - ti))
        ts  = pygame.Surface((tr * 2 + 2, tr * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(ts, (0, 200, 255, a), (tr + 1, tr + 1), tr)
        surf.blit(ts, (int(tx) - tr - 1, int(ty) - tr - 1))

    # Glow
    for gi in range(4, 0, -1):
        gr = ball_r + gi * 2
        gs = pygame.Surface((gr * 2 + 2, gr * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (0, 180, 255, 10 * gi), (gr + 1, gr + 1), gr)
        surf.blit(gs, (int(ball_x) - gr - 1, int(ball_y) - gr - 1))
    pygame.draw.circle(surf, (200, 240, 255), (int(ball_x), int(ball_y)), ball_r)
    pygame.draw.circle(surf, (255, 255, 255),
                       (int(ball_x) - ball_r // 3, int(ball_y) - ball_r // 3),
                       max(1, ball_r // 3))

    # Paddle
    pad_w = int(W * 0.30)
    pad_h = 8
    pad_x = int(W * 0.38)
    pad_y = H - 22
    col   = (0, 180, 255)
    gs = pygame.Surface((pad_w + 12, pad_h + 8), pygame.SRCALPHA)
    pygame.draw.rect(gs, (*col, 50), (0, 0, pad_w + 12, pad_h + 8), border_radius=5)
    surf.blit(gs, (pad_x - 6, pad_y - 3))
    pygame.draw.rect(surf, col, (pad_x, pad_y, pad_w, pad_h), border_radius=4)
    hi = tuple(min(255, v + 70) for v in col)
    pygame.draw.line(surf, hi, (pad_x + 3, pad_y + 2), (pad_x + pad_w - 3, pad_y + 2))

    # Scanlines
    scan = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 2):
        pygame.draw.line(scan, (0, 0, 0, 22), (0, y), (W, y))
    surf.blit(scan, (0, 0))

    # Top vignette
    glow = pygame.Surface((W, H // 3), pygame.SRCALPHA)
    for i in range(H // 3):
        a = max(0, 55 - i * 3)
        pygame.draw.line(glow, (0, 210, 255, a), (0, i), (W, i))
    surf.blit(glow, (0, 0))


# ══════════════════════════════════════════════════════════════════
#  BREAKOUT MENU
# ══════════════════════════════════════════════════════════════════

class BreakoutMenu:
    """Pre-game menu for Breakout."""

    MODE_ITEMS = [
        {'label': 'Classic', 'sub': 'Clear all bricks across 10 levels',
         'key': 'Enter', 'enabled': True},
        {'label': 'Endless', 'sub': 'No level cap — how far can you go?',
         'key': 'Enter', 'enabled': True},
        {'label': 'vs AI',   'sub': 'Rival Challenge · Paddle Battle · Watch AI',
         'key': 'Enter', 'enabled': True},
    ]

    VS_AI_ITEMS = [
        {'label': 'Rival Challenge', 'sub': 'Split-screen race — your board vs the AI\'s',
         'key': 'Enter', 'enabled': True},
        {'label': 'Paddle Battle',   'sub': 'AI controls the top paddle — outscore it',
         'key': 'Enter', 'enabled': True},
        {'label': 'Watch AI',        'sub': 'AI plays both paddles — sit back and watch',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_ITEMS = [
        {'label': 'Easy',   'sub': 'Slower ball, wider paddle',
         'key': 'Enter', 'enabled': True},
        {'label': 'Medium', 'sub': 'Balanced challenge',
         'key': 'Enter', 'enabled': True},
        {'label': 'Hard',   'sub': 'Fast ball, narrow paddle',
         'key': 'Enter', 'enabled': True},
    ]

    DIFFICULTY_KEYS = ['easy', 'medium', 'hard']

    def run(self):
        kb_speed_slider = Slider(
            min_val = 200, max_val = 1000, value = 600,
            label   = 'Keyboard Speed',
            accent  = (0, 200, 255),
        )
        mode_menu = GameMenu(
            title           = "BREAKOUT",
            subtitle        = "Select a game mode",
            items           = self.MODE_ITEMS,
            accent          = (0, 200, 255),
            footer_widgets  = [kb_speed_slider],
        )
        while True:
            mode_result = mode_menu.run()
            if mode_result in ('quit', 'back'):
                return mode_result

            # vs AI — show sub-menu first
            if mode_result == 2:
                vsai_menu = GameMenu(
                    title    = "vs AI",
                    subtitle = "Select a challenge",
                    items    = self.VS_AI_ITEMS,
                    accent   = (0, 200, 255),
                )
                vsai_result = vsai_menu.run()
                if vsai_result == 'quit':
                    return 'quit'
                if vsai_result == 'back':
                    continue
                vsai_label = self.VS_AI_ITEMS[vsai_result]['label']
            else:
                vsai_result = None
                vsai_label  = None

            # Difficulty
            title = vsai_label if vsai_label else self.MODE_ITEMS[mode_result]['label']
            diff_menu = GameMenu(
                title    = title,
                subtitle = "Select difficulty",
                items    = self.DIFFICULTY_ITEMS,
                accent   = (0, 200, 255),
            )
            diff_result = diff_menu.run()
            if diff_result == 'quit':
                return 'quit'
            if diff_result == 'back':
                continue

            difficulty = self.DIFFICULTY_KEYS[diff_result]
            kb_speed   = kb_speed_slider.value

            if mode_result == 2:
                if vsai_result == 0:    # Rival Challenge
                    app = RivalApp({'difficulty': difficulty, 'kb_speed': kb_speed})
                elif vsai_result == 1:  # Paddle Battle
                    app = BreakoutApp({'mode': 'vs_ai', 'difficulty': difficulty,
                                       'kb_speed': kb_speed})
                else:                   # Watch AI
                    app = BreakoutApp({'mode': 'vs_ai', 'difficulty': difficulty,
                                       'watch_ai': True, 'kb_speed': kb_speed})
            elif mode_result == 1:      # Endless
                app = BreakoutApp({'mode': 'endless', 'difficulty': difficulty,
                                   'kb_speed': kb_speed})
            else:                       # Classic
                app = BreakoutApp({'mode': 'classic', 'difficulty': difficulty,
                                   'kb_speed': kb_speed})

            result = app.run()
            if result == 'quit':
                return 'quit'

            SM.set_title("Breakout")
