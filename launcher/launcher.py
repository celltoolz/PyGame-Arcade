import sys
import pygame

from core.screen import SM
from tictactoe.menu import TicTacToeMenu
from tetris.menu import TetrisMenu
from connect4.menu import Connect4Menu
from checkers.menu import CheckersMenu
from breakout.menu import BreakoutMenu
from launcher.doom_app import DoomApp
from launcher.cards import GameCard, _art_tictactoe, _art_tetris, _art_doom
from connect4.menu import _art_connect4
from checkers.menu import _art_checkers
from breakout.menu import _art_breakout


class Launcher:
    """Main game selection screen — horizontal sliding tile rail."""

    CARD_W     = 260
    CARD_H     = 340
    CARD_GAP   = 28
    LIFT_PX    = 38
    LIFT_SCALE = 1.06
    INLAY_PAD  = 24

    def __init__(self):
        SM.set_title("Arcade  —  Select a Game")
        self.screen   = SM.screen
        self.clock    = SM.clock
        self.selected = 0
        self._rail_off    = 0.0
        self._rail_target = 0.0
        self._vel         = 0.0
        self._drag        = False
        self._drag_x0     = 0
        self._drag_rail0  = 0.0
        self._drag_moved  = 0
        self.cards        = []
        self._build()

    @property
    def _stride(self):
        return self.CARD_W + self.CARD_GAP

    def _target_for(self, idx):
        return idx * self._stride

    def _toggle_fs(self):
        self.screen = SM.toggle_fs()
        self._build()

    def _build(self):
        fam = next((c for c in ['segoeui','helvetica','dejavusans','freesans']
                    if pygame.font.match_font(c)), None)
        def F(sz, bold=False):
            return (pygame.font.SysFont(fam, sz, bold=bold) if fam
                    else pygame.font.Font(None, sz))
        self.font_head = F(44, bold=True)
        self.font_sub  = F(14)
        self.font_card = F(15, bold=True)
        self.font_csub = F(11)
        self.font_hint = F(11)

        self._card_defs = [
            ("TIC  TAC  TOE", "2D · 3D · AI Opponent",     "ENTER", _art_tictactoe, (120, 100, 255)),
            ("TETRIS",        "Classic · Levels · vs AI",   "ENTER", _art_tetris,    (0,   200, 180)),
            ("CONNECT  4",    "2 Player · vs AI",           "ENTER", _art_connect4,  (80,  140, 255)),
            ("CHECKERS",      "2 Player · vs AI",           "ENTER", _art_checkers,  (180, 100,  40)),
            ("BREAKOUT",      "Classic · Endless · Powerups","ENTER", _art_breakout, (0,   200, 255)),
            ("DOOM",          "Raycaster · Shoot · Survive", "ENTER", _art_doom,     (200,  40,  30)),
        ]
        if len(self.cards) != len(self._card_defs):
            self.cards = [
                GameCard(title, sub, key, art, accent, 0, 0, self.CARD_W, self.CARD_H)
                for title, sub, key, art, accent in self._card_defs
            ]

    def _card_cx(self, i, W):
        return W // 2 + i * self._stride - self._rail_off

    def _inlay_y(self, H):
        return int(90 + (H - 90 - 60) * 0.88)

    def _snap_to_nearest(self):
        W, _ = self.screen.get_size()
        best_i, best_d = 0, float('inf')
        for i in range(len(self.cards)):
            d = abs(self._card_cx(i, W) - W // 2)
            if d < best_d:
                best_d, best_i = d, i
        self.selected     = best_i
        self._rail_target = self._target_for(best_i)

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            W, H = self.screen.get_size()
            mp   = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self._toggle_fs()
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.selected = max(0, self.selected - 1)
                        self._rail_target = self._target_for(self.selected)
                        self._vel = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.selected = min(len(self.cards)-1, self.selected+1)
                        self._rail_target = self._target_for(self.selected)
                        self._vel = 0
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._launch(self.selected)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()

                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    self.screen = SM.on_resize(event.w, event.h)
                    self._build()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._drag       = True
                    self._drag_x0    = event.pos[0]
                    self._drag_rail0 = self._rail_off
                    self._drag_moved = 0
                    self._vel        = 0

                if event.type == pygame.MOUSEMOTION and self._drag:
                    dx = event.pos[0] - self._drag_x0
                    self._drag_moved  = abs(dx)
                    self._rail_off    = self._drag_rail0 - dx
                    self._rail_target = self._rail_off
                    self._vel         = -event.rel[0] * 0.6

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self._drag:
                        if self._drag_moved < 8:
                            for i, card in enumerate(self.cards):
                                if card.rect.collidepoint(event.pos):
                                    if self.selected == i:
                                        self._launch(i)
                                    else:
                                        self.selected     = i
                                        self._rail_target = self._target_for(i)
                                        self._vel         = 0
                                    break
                        else:
                            self._snap_to_nearest()
                        self._drag = False

            # Physics / animation
            if not self._drag:
                self._rail_off += self._vel
                self._vel      *= 0.88
                diff            = self._rail_target - self._rail_off
                self._rail_off += diff * min(1.0, dt * 9)

            min_off = 0
            max_off = self._target_for(len(self.cards) - 1)
            self._rail_off = max(min_off - self.CARD_W * 0.4,
                                 min(max_off + self.CARD_W * 0.4, self._rail_off))

            inlay_bot = self._inlay_y(H)
            for i, card in enumerate(self.cards):
                cx    = self._card_cx(i, W)
                scale = self.LIFT_SCALE if i == self.selected else 1.0
                lift  = self.LIFT_PX   if i == self.selected else 0
                cw    = int(self.CARD_W * scale)
                ch    = int(self.CARD_H * scale)
                card.rect = pygame.Rect(cx - cw // 2, inlay_bot - ch - lift, cw, ch)
                card.update(dt, i == self.selected or card.rect.collidepoint(mp))

            self._draw(W, H)

    def _launch(self, idx):
        if idx == 0:   menu = TicTacToeMenu()
        elif idx == 1: menu = TetrisMenu()
        elif idx == 2: menu = Connect4Menu()
        elif idx == 3: menu = CheckersMenu()
        elif idx == 4: menu = BreakoutMenu()
        else:          menu = DoomApp()
        result = menu.run()
        if result == 'quit':
            pygame.quit(); sys.exit()
        pygame.event.clear()
        self.screen = SM.screen
        SM.set_title("Arcade  —  Select a Game")
        self._build()

    def _draw(self, W, H):
        self.screen = SM.screen
        surf = self.screen
        surf.fill((8, 10, 18))
        for x in range(0, W, 40):
            pygame.draw.line(surf, (13, 16, 28), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(surf, (13, 16, 28), (0, y), (W, y))

        # Header
        title = self.font_head.render("ARCADE", True, (220, 225, 245))
        tx    = W // 2 - title.get_width() // 2
        surf.blit(title, (tx, 18))
        pygame.draw.line(surf, (120, 100, 255),
            (tx, 18 + title.get_height() + 4),
            (tx + title.get_width(), 18 + title.get_height() + 4), 2)
        sub = self.font_sub.render(
            "\u2190 \u2192 or drag to browse   \u00b7   Enter to play   \u00b7   Esc to quit",
            True, (50, 60, 95))
        surf.blit(sub, (W // 2 - sub.get_width() // 2, 18 + title.get_height() + 14))

        inlay_bot = self._inlay_y(H)
        inlay_top = inlay_bot - self.CARD_H - self.INLAY_PAD * 2
        inlay_h   = inlay_bot - inlay_top + self.LIFT_PX + 16
        # Trough shadow
        for i in range(14, 0, -1):
            s = pygame.Surface((W, 2), pygame.SRCALPHA)
            s.fill((0, 0, 0, max(0, 70 - i * 5)))
            surf.blit(s, (0, inlay_top - 10 - i))

        # Trough body
        trough_r = pygame.Rect(0, inlay_top - 10, W, inlay_h + 10)
        pygame.draw.rect(surf, (6, 8, 16), trough_r)

        # Inner shadow at top of trough (recessed look)
        for i in range(10):
            a = max(0, 130 - i * 13)
            s = pygame.Surface((W, 1), pygame.SRCALPHA)
            s.fill((0, 0, 0, a))
            surf.blit(s, (0, trough_r.top + i))

        # Trough borders
        pygame.draw.line(surf, (18, 22, 42), (0, trough_r.top),     (W, trough_r.top), 2)
        pygame.draw.line(surf, (35, 42, 70), (0, trough_r.top - 1), (W, trough_r.top - 1))
        pygame.draw.line(surf, (18, 22, 42), (0, trough_r.bottom),  (W, trough_r.bottom))
        # Selected card glow
        sel = self.cards[self.selected]
        gw, gh = sel.rect.w + 100, sel.rect.h + 100
        glow   = pygame.Surface((gw, gh), pygame.SRCALPHA)
        for i in range(50, 0, -1):
            a = max(0, 7 - i // 8)
            pygame.draw.rect(glow, (*sel.accent, a),
                (50-i, 50-i, sel.rect.w+i*2, sel.rect.h+i*2), border_radius=18+i)
        surf.blit(glow, (sel.rect.x - 50, sel.rect.y - 50))

        # Edge fades
        fade_w = 110
        for side in ('left', 'right'):
            fade = pygame.Surface((fade_w, inlay_h + 10), pygame.SRCALPHA)
            for x in range(fade_w):
                a = int(230 * (1 - x/fade_w)) if side=='left' else int(230 * (x/fade_w))
                pygame.draw.line(fade, (8, 10, 18, a), (x, 0), (x, inlay_h + 10))
            surf.blit(fade, (0 if side=='left' else W-fade_w, trough_r.top))

        # Cards — non-selected first, selected on top
        for i in [j for j in range(len(self.cards)) if j != self.selected]:
            self.cards[i].draw(surf, self.font_card, self.font_csub, self.font_hint)
        self.cards[self.selected].draw(surf, self.font_card, self.font_csub, self.font_hint)

        # Dots
        dot_y  = trough_r.bottom + 18
        n      = len(self.cards)
        dot_x0 = W // 2 - (n - 1) * 11
        for i in range(n):
            col = self.cards[i].accent if i == self.selected else (30, 36, 58)
            r   = 5 if i == self.selected else 3
            pygame.draw.circle(surf, col, (dot_x0 + i * 22, dot_y), r)

        # Game name hint
        name = self._card_defs[self.selected][0]
        hint = self.font_sub.render(f"{name}   —   press Enter to play", True, (45, 55, 88))
        surf.blit(hint, (W // 2 - hint.get_width() // 2, dot_y + 16))

        pygame.display.flip()
