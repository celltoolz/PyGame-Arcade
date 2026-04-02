import math
import pygame

from core.screen import SM
from core.drawing import lerp_color
from core.particles import ParticleSystem
from .game import (Connect4Game, C4_COLS, C4_ROWS, C4_EMPTY, C4_P1, C4_P2,
                   C4_BG, C4_BOARD_COL, C4_BOARD_RIM, C4_HOLE_DARK,
                   C4_P1_COL, C4_P1_GLOW, C4_P2_COL, C4_P2_GLOW,
                   C4_GHOST_ALPHA, C4_WIN_PULSE, C4_ACCENT)
from .ai import Connect4AI

# ══════════════════════════════════════════════════════════════════
#  CONNECT 4 APP
# ══════════════════════════════════════════════════════════════════

class Connect4App:
    """Connect 4 — vs Human or vs AI. Returns 'menu' or 'quit'."""

    def __init__(self, config=None):
        self.config     = config or {'opponent': 'human', 'difficulty': 'medium'}
        self.vs_ai      = (self.config.get('opponent') == 'ai')
        self.difficulty = self.config.get('difficulty', 'medium')
        self.ai         = Connect4AI(self.difficulty) if self.vs_ai else None
        self.game       = Connect4Game()
        self.screen     = SM.screen
        self.clock      = SM.clock
        title = f"Connect 4  —  vs AI ({self.difficulty.capitalize()})" \
                if self.vs_ai else "Connect 4  —  2 Player"
        SM.set_title(title)
        self._build_layout()

        # Animation state
        self._drop_anim   = None   # {'col','from_y','to_y','y','player','vel'}
        self._win_pulse   = 0.0
        self._result_anim = 0.0
        self._hover_col   = -1
        self._selected_col = C4_COLS // 2   # keyboard cursor, starts centre
        self._using_kb     = False           # True when keyboard was last used
        self._ai_pending  = False
        self._ai_timer    = 0.0
        self._ai_delay    = 0.55
        self._shake_t     = 0.0   # column shake on invalid
        self._shake_col   = -1
        self.particles    = ParticleSystem()

    def _build_layout(self):
        W, H   = self.screen.get_size()
        # Board fits snugly in the centre, square cells
        margin = max(40, int(min(W, H) * 0.06))
        avail_w = W - margin * 2
        avail_h = H - margin * 2 - 80   # leave room for status
        cell   = min(avail_w // C4_COLS, avail_h // (C4_ROWS + 1))
        cell   = max(48, cell)
        bw     = cell * C4_COLS
        bh     = cell * C4_ROWS
        self.cell   = cell
        self.bx     = W // 2 - bw // 2
        self.by     = H // 2 - bh // 2 + 20
        self.bw     = bw
        self.bh     = bh

    def _piece_center(self, r, c):
        return (self.bx + c * self.cell + self.cell // 2,
                self.by + r * self.cell + self.cell // 2)

    def _piece_color(self, player):
        return C4_P1_COL if player == C4_P1 else C4_P2_COL

    def _piece_glow(self, player):
        return C4_P1_GLOW if player == C4_P1 else C4_P2_GLOW

    def _new_game(self):
        self.game         = Connect4Game()
        self._drop_anim   = None
        self._win_pulse   = 0.0
        self._result_anim = 0.0
        self._hover_col   = -1
        self._selected_col = C4_COLS // 2
        self._using_kb     = False
        self._ai_pending  = False
        self._ai_timer    = 0.0
        self.particles    = ParticleSystem()
        self._maybe_trigger_ai()

    def _maybe_trigger_ai(self):
        if self.vs_ai and self.game.current == C4_P2 and not self.game.game_over:
            self._ai_pending = True
            self._ai_timer   = 0.0

    def _drop_piece(self, col):
        """Attempt to drop in col — starts animation if valid."""
        if self._drop_anim or self.game.game_over:
            return
        r = self.game.drop_row(col)
        if r < 0:
            self._shake_col = col
            self._shake_t   = 0.35
            return
        player = self.game.current
        _, _   = self._piece_center(r, col)
        from_y = self.by - self.cell
        to_y   = self.by + r * self.cell + self.cell // 2
        self._drop_anim = {
            'col': col, 'row': r, 'player': player,
            'y': float(from_y), 'to_y': float(to_y),
            'vel': 0.0,
        }

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.screen = SM.toggle_fs()
                        self._build_layout()
                    elif event.key == pygame.K_ESCAPE:
                        return 'menu'
                    elif event.key == pygame.K_r:
                        self._new_game()
                    elif event.key == pygame.K_LEFT:
                        self._using_kb = True
                        self._selected_col = max(0, self._selected_col - 1)
                    elif event.key == pygame.K_RIGHT:
                        self._using_kb = True
                        self._selected_col = min(C4_COLS - 1, self._selected_col + 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_RETURN, pygame.K_SPACE):
                        self._using_kb = True
                        self._try_player_drop(self._selected_col)
                    # Number keys 1-7 for quick column select
                    elif pygame.K_1 <= event.key <= pygame.K_7:
                        self._using_kb = True
                        col = event.key - pygame.K_1
                        self._selected_col = col
                        self._try_player_drop(col)
                if event.type == pygame.MOUSEMOTION:
                    mx = event.pos[0]
                    # Switch to mouse mode as soon as cursor moves
                    self._using_kb = False
                    if self.bx <= mx < self.bx + self.bw:
                        self._hover_col = (mx - self.bx) // self.cell
                    else:
                        self._hover_col = -1
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._using_kb = False
                    mx = event.pos[0]
                    if self.bx <= mx < self.bx + self.bw:
                        col = (mx - self.bx) // self.cell
                        self._selected_col = col
                        self._try_player_drop(col)
                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    self.screen = SM.on_resize(event.w, event.h)
                    self._build_layout()

            self.screen = SM.screen
            self._update(dt)
            self._draw()

    def _try_player_drop(self, col):
        """Drop for human player — blocked during AI turn or animation."""
        if self._drop_anim:            return
        if self.game.game_over:        return
        if self.vs_ai and self.game.current == C4_P2: return
        self._drop_piece(col)

    def _update(self, dt):
        self.particles.update(dt)

        # Shake timer
        if self._shake_t > 0:
            self._shake_t = max(0.0, self._shake_t - dt)

        # Win/result animation
        if self.game.game_over:
            self._win_pulse   = (self._win_pulse + dt * 4) % (2 * math.pi)
            self._result_anim = min(1.0, self._result_anim + dt * 2.5)

        # Drop animation — simple physics with bounce
        if self._drop_anim:
            a = self._drop_anim
            GRAVITY = 3200.0
            BOUNCE  = 0.28
            a['vel'] += GRAVITY * dt
            a['y']   += a['vel'] * dt
            if a['y'] >= a['to_y']:
                a['y']   = a['to_y']
                if abs(a['vel']) > 200:
                    a['vel'] = -a['vel'] * BOUNCE
                else:
                    # Commit move
                    col    = a['col']
                    player = a['player']
                    self._drop_anim = None
                    self.game.drop(col)
                    # Particle burst at landing position
                    cx, cy = self._piece_center(a['row'], col)
                    color  = self._piece_glow(player)
                    self.particles.burst(cx, cy, color, count=22)
                    # Schedule AI if needed
                    self._maybe_trigger_ai()
            return

        # AI move
        if self._ai_pending and not self._drop_anim and not self.game.game_over:
            self._ai_timer += dt
            if self._ai_timer >= self._ai_delay:
                self._ai_pending = False
                col = self.ai.best_move(self.game)
                self._drop_piece(col)

    # ── drawing ──────────────────────────────────────────────────

    def _draw(self):
        W, H = self.screen.get_size()
        surf = self.screen

        # Background
        surf.fill(C4_BG)
        for x in range(0, W, 36):
            pygame.draw.line(surf, (12, 16, 34), (x, 0), (x, H))
        for y in range(0, H, 36):
            pygame.draw.line(surf, (12, 16, 34), (0, y), (W, y))

        self._draw_header(surf, W)
        self._draw_board_frame(surf)
        self._draw_ghost(surf)
        self._draw_pieces(surf)
        self._draw_drop_anim(surf)
        self._draw_win_highlight(surf)
        self.particles.draw(surf)
        self._draw_status(surf, W, H)
        if self.game.game_over and self._result_anim > 0.4:
            self._draw_overlay(surf, W, H)

        pygame.display.flip()

    def _draw_header(self, surf, W):
        fam = next((c for c in ['segoeui','helvetica','freesans']
                    if pygame.font.match_font(c)), None)
        fnt = pygame.font.SysFont(fam, 28, bold=True) if fam else pygame.font.Font(None, 28)
        t   = fnt.render("CONNECT  4", True, (200, 210, 240))
        surf.blit(t, (W//2 - t.get_width()//2, 14))
        uw = t.get_width() + 20
        ux = W//2 - uw//2
        uy = 14 + t.get_height() + 3
        pygame.draw.line(surf, C4_ACCENT, (ux, uy), (ux + uw, uy), 2)

    def _draw_board_frame(self, surf):
        cell = self.cell
        bx, by = self.bx, self.by
        # Board shadow
        shadow = pygame.Surface((self.bw + 20, self.bh + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), (0, 0, self.bw+20, self.bh+20), border_radius=18)
        surf.blit(shadow, (bx - 10, by - 6))

        # Main board body
        pygame.draw.rect(surf, C4_BOARD_COL,
            (bx - 6, by - 6, self.bw + 12, self.bh + 12), border_radius=16)
        pygame.draw.rect(surf, C4_BOARD_RIM,
            (bx - 6, by - 6, self.bw + 12, self.bh + 12), 3, border_radius=16)

        # Cut-out holes
        for r in range(C4_ROWS):
            for c in range(C4_COLS):
                cx, cy = self._piece_center(r, c)
                radius = cell // 2 - 4
                pygame.draw.circle(surf, C4_HOLE_DARK, (cx, cy), radius)
                # Subtle inner rim
                pygame.draw.circle(surf, C4_BOARD_RIM, (cx, cy), radius, 2)

    def _draw_col_highlight(self, surf):
        """Keyboard column highlight — drawn on top of the board frame."""
        if not self._using_kb or self.game.game_over or self._drop_anim:
            return
        if self.vs_ai and self.game.current == C4_P2:
            return
        col   = self._selected_col
        color = self._piece_glow(self.game.current)
        x     = self.bx + col * self.cell
        # Bright tinted fill over the column
        bar = pygame.Surface((self.cell, self.bh + 12), pygame.SRCALPHA)
        bar.fill((*color, 70))
        surf.blit(bar, (x, self.by - 6))
        # Bold coloured border
        pygame.draw.rect(surf, (*color, 220),
            (x, self.by - 6, self.cell, self.bh + 12), 3, border_radius=4)

    def _draw_ghost(self, surf):
        """Translucent preview of where the piece will land + arrow indicator."""
        # Active column — keyboard cursor or mouse hover
        col = self._selected_col if self._using_kb else self._hover_col

        if col < 0 or self._drop_anim or self.game.game_over:
            return
        if self.vs_ai and self.game.current == C4_P2:
            return
        if col not in self.game.valid_cols():
            return
        r = self.game.drop_row(col)
        if r < 0:
            return

        cx, cy = self._piece_center(r, col)
        radius = self.cell // 2 - 6
        color  = self._piece_glow(self.game.current)

        s = pygame.Surface((radius*2+2, radius*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, C4_GHOST_ALPHA), (radius+1, radius+1), radius)
        surf.blit(s, (cx - radius - 1, cy - radius - 1))

        # Arrow above board
        arrow_cx = self.bx + col * self.cell + self.cell // 2
        arrow_y  = self.by - self.cell // 2
        if self._using_kb:
            bounce   = int(math.sin(pygame.time.get_ticks() * 0.006) * 4)
            arrow_y += bounce

        pygame.draw.polygon(surf, (*color, 220),
            [(arrow_cx,     arrow_y + 14),
             (arrow_cx - 9, arrow_y),
             (arrow_cx + 9, arrow_y)])

    def _draw_pieces(self, surf):
        # Shake offset for invalid column
        shake_off = 0
        if self._shake_t > 0:
            shake_off = int(math.sin(self._shake_t * 40) * 5)

        for r in range(C4_ROWS):
            for c in range(C4_COLS):
                v = self.game.board[r][c]
                if v == C4_EMPTY:
                    continue
                # Don't draw the animating piece at its board position yet
                if (self._drop_anim and
                        self._drop_anim['col'] == c and
                        self._drop_anim['row'] == r):
                    continue
                cx, cy = self._piece_center(r, c)
                off_x = shake_off if c == self._shake_col else 0
                self._draw_piece(surf, cx + off_x, cy, v)

    def _draw_piece(self, surf, cx, cy, player, alpha=255, radius_override=None):
        cell   = self.cell
        radius = radius_override or (cell // 2 - 6)
        color  = self._piece_color(player)
        glow   = self._piece_glow(player)

        # Glow halo
        for i in range(5, 0, -1):
            gs = pygame.Surface((radius*2+i*4, radius*2+i*4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow, int(alpha * 0.07 * i)),
                (radius+i*2, radius+i*2), radius + i*2)
            surf.blit(gs, (cx - radius - i*2, cy - radius - i*2))

        # Main circle
        s = pygame.Surface((radius*2+2, radius*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (radius+1, radius+1), radius)
        # Highlight
        hi = tuple(min(255, v+80) for v in color)
        pygame.draw.circle(s, (*hi, alpha),
            (radius+1 - radius//4, radius+1 - radius//4),
            radius // 3)
        surf.blit(s, (cx - radius - 1, cy - radius - 1))

    def _draw_drop_anim(self, surf):
        if not self._drop_anim:
            return
        a = self._drop_anim
        col = a['col']
        cx  = self.bx + col * self.cell + self.cell // 2
        cy  = int(a['y'])
        self._draw_piece(surf, cx, cy, a['player'])

    def _draw_win_highlight(self, surf):
        if not self.game.win_cells:
            return
        pulse = (math.sin(self._win_pulse) + 1) / 2   # 0..1
        alpha = int(120 + pulse * 135)
        radius = self.cell // 2 - 3
        for r, c in self.game.win_cells:
            cx, cy = self._piece_center(r, c)
            s = pygame.Surface((radius*2+8, radius*2+8), pygame.SRCALPHA)
            pygame.draw.circle(s, (*C4_WIN_PULSE, alpha),
                (radius+4, radius+4), radius)
            surf.blit(s, (cx - radius - 4, cy - radius - 4))

    def _draw_status(self, surf, W, H):
        fam = next((c for c in ['segoeui','helvetica','freesans']
                    if pygame.font.match_font(c)), None)
        fnt = pygame.font.SysFont(fam, 18, bold=True) if fam else pygame.font.Font(None, 18)
        fnt_sm = pygame.font.SysFont(fam, 13) if fam else pygame.font.Font(None, 13)

        if not self.game.game_over:
            cur = self.game.current
            color = C4_P1_COL if cur == C4_P1 else C4_P2_COL
            if self.vs_ai and cur == C4_P2 and self._ai_pending:
                label = "AI is thinking..."
                color = lerp_color(C4_P2_COL, (200, 200, 255),
                                   abs(math.sin(pygame.time.get_ticks() * 0.003)))
            elif self.vs_ai:
                label = "Your turn" if cur == C4_P1 else "AI's turn"
            else:
                label = f"Player {'1' if cur == C4_P1 else '2'}'s turn"

            t = fnt.render(label, True, color)
            surf.blit(t, (W//2 - t.get_width()//2, self.by - 44))

            # Draw a small indicator disc next to text
            disc_x = W//2 - t.get_width()//2 - 22
            disc_y = self.by - 44 + t.get_height()//2
            pygame.draw.circle(surf, color, (disc_x, disc_y), 8)

        # Bottom hint
        hint = fnt_sm.render(
            "← → select column  ·  ↓ / Enter drop  ·  1–7 keys  ·  R restart  ·  Esc menu",
            True, (40, 55, 90))
        surf.blit(hint, (W//2 - hint.get_width()//2, self.by + self.bh + 14))

    def _draw_overlay(self, surf, W, H):
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surf.blit(dim, (0, 0))

        fam = next((c for c in ['segoeui','helvetica','freesans']
                    if pygame.font.match_font(c)), None)
        fnt_big = pygame.font.SysFont(fam, 52, bold=True) if fam else pygame.font.Font(None, 52)
        fnt_sm  = pygame.font.SysFont(fam, 20)           if fam else pygame.font.Font(None, 20)

        w = self.game.winner
        if w == 'draw':
            msg, col = "DRAW!", (180, 180, 200)
        elif w == C4_P1:
            msg = "YOU WIN!" if self.vs_ai else "PLAYER 1 WINS!"
            col = C4_P1_GLOW
        else:
            msg = "AI WINS!" if self.vs_ai else "PLAYER 2 WINS!"
            col = C4_P2_GLOW

        t1 = fnt_big.render(msg, True, col)
        t2 = fnt_sm.render("(R) play again   ·   (Esc) menu", True, (130, 140, 170))
        surf.blit(t1, (W//2 - t1.get_width()//2, H//2 - 55))
        surf.blit(t2, (W//2 - t2.get_width()//2, H//2 + 14))
