import math
import pygame

from core.screen import SM
from core.drawing import lerp_color
from core.particles import ParticleSystem
from .game import (CheckersGame, CK_SIZE, CK_EMPTY, CK_BLACK, CK_RED, CK_BLACK_K, CK_RED_K,
                   CK_LIGHT, CK_DARK, CK_BOARD_BG, CK_BORDER,
                   CK_BLACK_COL, CK_BLACK_RIM, CK_RED_COL, CK_RED_RIM,
                   CK_CROWN, CK_SEL_COL, CK_MOVE_COL, CK_CAPTURE_COL,
                   _ck_is_black, _ck_is_red, _ck_is_king, _ck_owner)
from .ai import CheckersAI

# ══════════════════════════════════════════════════════════════════
#  CHECKERS APP
# ══════════════════════════════════════════════════════════════════

class CheckersApp:
    """Checkers — vs Human or vs AI. Returns 'menu' or 'quit'."""

    def __init__(self, config=None):
        self.config     = config or {'opponent': 'human', 'difficulty': 'medium'}
        self.vs_ai      = (self.config.get('opponent') == 'ai')
        self.difficulty = self.config.get('difficulty', 'medium')
        self.force_jump = self.config.get('force_jump', True)
        self.ai         = CheckersAI(self.difficulty) if self.vs_ai else None
        self.game       = CheckersGame(force_jump=self.force_jump)
        self.screen     = SM.screen
        self.clock      = SM.clock
        SM.set_title(f"Checkers  —  vs AI ({self.difficulty.capitalize()})"
                     if self.vs_ai else "Checkers  —  2 Player")
        self._build_layout()
        self._result_anim = 0.0
        self._ai_pending  = False
        self._ai_timer    = 0.0
        self._ai_delay    = 0.6
        self.particles    = ParticleSystem()
        # Animation state
        self._anim_path   = []    # list of (r,c) waypoints remaining
        self._anim_piece  = CK_EMPTY
        self._anim_t      = 0.0   # 0..1 progress through current segment
        self._anim_speed  = 5.0   # segments per second
        self._anim_from   = None  # pixel (x,y)
        self._anim_to     = None  # pixel (x,y)
        self._anim_pending_ai = False
        # Keyboard navigation state
        self._kb_mode      = False   # True when keyboard was last used
        self._kb_cursor    = (5, 0)  # (r, c) — starts on a dark square
        self._kb_dest_list = []      # ordered list of valid_move dests (phase 2)
        self._kb_dest_idx  = 0       # index into _kb_dest_list
        self._maybe_trigger_ai()

    def _build_layout(self):
        W, H   = self.screen.get_size()
        margin = max(30, int(min(W, H) * 0.05))
        avail  = min(W - margin*2, H - margin*2 - 80)
        self.cell  = max(48, avail // CK_SIZE)
        self.bsize = self.cell * CK_SIZE
        self.bx    = W//2 - self.bsize//2
        self.by    = H//2 - self.bsize//2 + 10

    def _sq_center(self, r, c):
        return (self.bx + c*self.cell + self.cell//2,
                self.by + r*self.cell + self.cell//2)

    def _sq_at(self, mx, my):
        c = (mx - self.bx) // self.cell
        r = (my - self.by) // self.cell
        if 0 <= r < CK_SIZE and 0 <= c < CK_SIZE:
            return r, c
        return None, None

    def _new_game(self):
        self.game         = CheckersGame(force_jump=self.force_jump)
        self._result_anim = 0.0
        self._ai_pending  = False
        self._ai_timer    = 0.0
        self._anim_path   = []
        self._anim_piece  = CK_EMPTY
        self._anim_t      = 0.0
        self._anim_from   = None
        self._anim_to     = None
        self._anim_pending_ai = False
        self._kb_mode      = False
        self._kb_cursor    = (5, 0)
        self._kb_dest_list = []
        self._kb_dest_idx  = 0
        self.particles    = ParticleSystem()
        self._maybe_trigger_ai()

    def _maybe_trigger_ai(self):
        if self.vs_ai and self.game.turn == CK_RED and not self.game.game_over:
            self._ai_pending = True
            self._ai_timer   = 0.0

    def _handle_click(self, mx, my):
        if self._anim_path: return          # busy animating
        if self.game.game_over: return
        if self.vs_ai and self.game.turn == CK_RED: return
        r, c = self._sq_at(mx, my)
        if r is None: return
        g = self.game
        if g.selected and (r, c) in g.valid_moves:
            path = g.valid_moves[(r, c)]
            piece = g.board[path[0][0]][path[0][1]]
            g.move_full_path(path)
            self._start_anim(path, piece, trigger_ai=True)
            return
        g.select(r, c)

    def _do_ai_move(self):
        mv = self.ai.best_move(self.game)
        if mv is None: return
        fr, fc, tr, tc = mv
        self.game.select(fr, fc)
        path  = self.game.valid_moves.get((tr, tc), [(fr, fc), (tr, tc)])
        piece = self.game.board[path[0][0]][path[0][1]]
        self.game.move_full_path(path)
        self._start_anim(path, piece, trigger_ai=False)

    def _start_anim(self, path, piece, trigger_ai=False):
        """Kick off piece animation along a waypoint path."""
        self._anim_path        = list(path)   # copy
        self._anim_piece       = piece
        self._anim_t           = 0.0
        self._anim_pending_ai  = trigger_ai
        if len(self._anim_path) >= 2:
            r0, c0 = self._anim_path[0]
            r1, c1 = self._anim_path[1]
            self._anim_from = self._sq_center(r0, c0)
            self._anim_to   = self._sq_center(r1, c1)

    def _kb_movable_pieces(self):
        """Sorted list of (r,c) that the current player can move."""
        return sorted(self.game.all_moves.keys())

    def _kb_snap_to_nearest(self, pieces):
        """Snap _kb_cursor to the nearest square in pieces list."""
        if not pieces: return
        cr, cc = self._kb_cursor
        self._kb_cursor = min(pieces,
            key=lambda sq: abs(sq[0]-cr) + abs(sq[1]-cc))

    def _kb_move_cursor_phase1(self, dr, dc):
        """Move cursor among movable pieces using arrow key direction."""
        pieces = self._kb_movable_pieces()
        if not pieces: return
        cr, cc = self._kb_cursor
        # Filter pieces in the requested direction, else wrap around list
        candidates = [sq for sq in pieces
                      if (dr == 0 or (sq[0]-cr)*dr > 0)
                      and (dc == 0 or (sq[1]-cc)*dc > 0)]
        if candidates:
            self._kb_cursor = min(candidates,
                key=lambda sq: abs(sq[0]-cr) + abs(sq[1]-cc))
        else:
            # wrap: cycle through list
            idx = pieces.index(self._kb_cursor) if self._kb_cursor in pieces else 0
            self._kb_cursor = pieces[(idx + (1 if dc+dr > 0 else -1)) % len(pieces)]

    def _kb_move_cursor_phase2(self, dr, dc):
        """Cycle through valid move destinations with arrow keys."""
        if not self._kb_dest_list: return
        n = len(self._kb_dest_list)
        cr, cc = self._kb_dest_list[self._kb_dest_idx]
        candidates = []
        for i, sq in enumerate(self._kb_dest_list):
            if (dr == 0 or (sq[0]-cr)*dr > 0) and \
               (dc == 0 or (sq[1]-cc)*dc > 0):
                candidates.append(i)
        if candidates:
            self._kb_dest_idx = min(candidates,
                key=lambda i: abs(self._kb_dest_list[i][0]-cr)
                            + abs(self._kb_dest_list[i][1]-cc))
        else:
            self._kb_dest_idx = (self._kb_dest_idx + (1 if dc+dr > 0 else -1)) % n

    def _kb_enter(self):
        """Handle Enter key — select piece or execute move."""
        g = self.game
        if self._anim_path: return
        if g.game_over: return
        if self.vs_ai and g.turn == CK_RED: return

        if g.selected is None:
            # Phase 1 — try to select the piece under cursor
            r, c = self._kb_cursor
            if g.select(r, c):
                self._kb_dest_list = sorted(g.valid_moves.keys())
                self._kb_dest_idx  = 0
                if self._kb_dest_list:
                    self._kb_cursor = self._kb_dest_list[0]
        else:
            # Phase 2 — execute the highlighted destination
            if not self._kb_dest_list: return
            dest = self._kb_dest_list[self._kb_dest_idx]
            if dest in g.valid_moves:
                path  = g.valid_moves[dest]
                piece = g.board[path[0][0]][path[0][1]]
                g.move_full_path(path)
                self._start_anim(path, piece, trigger_ai=True)
                # Reset to phase 1 after move
                self._kb_dest_list = []
                self._kb_dest_idx  = 0
                self._kb_cursor    = path[-1]

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.screen = SM.toggle_fs(); self._build_layout()
                    elif event.key == pygame.K_ESCAPE: return 'menu'
                    elif event.key == pygame.K_r:      self._new_game()
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                       pygame.K_UP,   pygame.K_DOWN):
                        if not self._kb_mode and self.game.selected:
                            # Switching from mouse with a piece selected —
                            # enter phase 2 directly on that piece's destinations
                            self._kb_dest_list = sorted(self.game.valid_moves.keys())
                            self._kb_dest_idx  = 0
                            if self._kb_dest_list:
                                self._kb_cursor = self._kb_dest_list[0]
                        self._kb_mode = True
                        # Map arrow keys to diagonal directions on the board
                        dr = -1 if event.key == pygame.K_UP   else \
                              1 if event.key == pygame.K_DOWN  else 0
                        dc = -1 if event.key == pygame.K_LEFT  else \
                              1 if event.key == pygame.K_RIGHT else 0
                        if self.game.selected is None:
                            # Phase 1: navigate pieces
                            pieces = self._kb_movable_pieces()
                            if self._kb_cursor not in pieces:
                                self._kb_snap_to_nearest(pieces)
                            else:
                                self._kb_move_cursor_phase1(dr, dc)
                        else:
                            # Phase 2: navigate destinations
                            self._kb_move_cursor_phase2(dr, dc)
                            self._kb_cursor = self._kb_dest_list[self._kb_dest_idx] \
                                              if self._kb_dest_list else self._kb_cursor
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._kb_mode = True
                        self._kb_enter()
                    elif event.key == pygame.K_BACKSPACE:
                        if self.game.selected:
                            self._kb_mode          = True
                            self._kb_cursor        = self.game.selected
                            self.game.selected     = None
                            self.game.valid_moves  = {}
                            self._kb_dest_list     = []
                            self._kb_dest_idx      = 0
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._kb_mode = False
                    self._handle_click(*event.pos)
                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    self.screen = SM.on_resize(event.w, event.h)
                    self._build_layout()
            self.screen = SM.screen
            self._update(dt)
            self._draw()

    def _update(self, dt):
        self.particles.update(dt)
        if self.game.game_over:
            self._result_anim = min(1.0, self._result_anim + dt * 2.5)

        # Drive piece animation
        if self._anim_path and len(self._anim_path) >= 2:
            self._anim_t += dt * self._anim_speed
            if self._anim_t >= 1.0:
                # Segment complete — particle burst at landing
                r1, c1 = self._anim_path[1]
                cx, cy = self._sq_center(r1, c1)
                col = CK_BLACK_RIM if _ck_is_black(self._anim_piece) else CK_RED_RIM
                self.particles.burst(cx, cy, col, count=10)
                # Advance to next segment
                self._anim_path.pop(0)
                self._anim_t = 0.0
                if len(self._anim_path) >= 2:
                    r0, c0 = self._anim_path[0]
                    r1, c1 = self._anim_path[1]
                    self._anim_from = self._sq_center(r0, c0)
                    self._anim_to   = self._sq_center(r1, c1)
                else:
                    # Animation finished
                    self._anim_path  = []
                    self._anim_from  = None
                    self._anim_to    = None
                    if self._kb_mode:
                        self._kb_snap_to_nearest(self._kb_movable_pieces())
                    if self._anim_pending_ai:
                        self._maybe_trigger_ai()
            return

        if self._ai_pending:
            self._ai_timer += dt
            if self._ai_timer >= self._ai_delay:
                self._ai_pending = False
                self._do_ai_move()

    # ── drawing ───────────────────────────────────────────────────

    def _draw(self):
        W, H = self.screen.get_size()
        surf = self.screen
        surf.fill((40, 25, 10))
        for x in range(0, W, 40):
            pygame.draw.line(surf, (48, 30, 12), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(surf, (48, 30, 12), (0, y), (W, y))
        self._draw_header(surf, W)
        self._draw_board(surf)
        self._draw_highlights(surf)
        self._draw_pieces(surf)
        self.particles.draw(surf)
        self._draw_status(surf, W, H)
        if self.game.game_over and self._result_anim > 0.4:
            self._draw_overlay(surf, W, H)
        pygame.display.flip()

    def _draw_header(self, surf, W):
        fam = next((c for c in ['segoeui','helvetica','freesans']
                    if pygame.font.match_font(c)), None)
        fnt = pygame.font.SysFont(fam, 28, bold=True) if fam else pygame.font.Font(None, 28)
        t   = fnt.render("CHECKERS", True, (235, 200, 140))
        surf.blit(t, (W//2 - t.get_width()//2, 14))
        uw = t.get_width() + 20
        ux = W//2 - uw//2
        pygame.draw.line(surf, CK_DARK, (ux, 14+t.get_height()+3),
                         (ux+uw, 14+t.get_height()+3), 2)

    def _draw_board(self, surf):
        cell = self.cell
        bx, by = self.bx, self.by
        pygame.draw.rect(surf, CK_BORDER,
            (bx-8, by-8, self.bsize+16, self.bsize+16), border_radius=6)
        pygame.draw.rect(surf, CK_BOARD_BG,
            (bx-5, by-5, self.bsize+10, self.bsize+10), border_radius=4)
        for r in range(CK_SIZE):
            for c in range(CK_SIZE):
                col = CK_LIGHT if (r+c)%2==0 else CK_DARK
                pygame.draw.rect(surf, col, (bx+c*cell, by+r*cell, cell, cell))
        pygame.draw.rect(surf, CK_BORDER, (bx, by, self.bsize, self.bsize), 2)

    def _draw_highlights(self, surf):
        g = self.game
        cell = self.cell
        bx, by = self.bx, self.by
        mp = pygame.mouse.get_pos()
        hr, hc = self._sq_at(*mp)

        # Hover on selectable pieces (mouse mode only)
        if not self._kb_mode and hr is not None and (hr,hc) in g.all_moves \
                and g.selected != (hr,hc):
            if not (self.vs_ai and g.turn == CK_RED) and not self._anim_path:
                s = pygame.Surface((cell, cell), pygame.SRCALPHA)
                s.fill((255,255,255,30))
                surf.blit(s, (bx+hc*cell, by+hr*cell))

        # Selected piece border
        if g.selected and not self._anim_path:
            sr, sc = g.selected
            pygame.draw.rect(surf, CK_SEL_COL,
                (bx+sc*cell+2, by+sr*cell+2, cell-4, cell-4), 3, border_radius=3)

        # Valid move squares
        if not self._anim_path:
            for (tr, tc), path in g.valid_moves.items():
                is_cap = len(path) > 2 or (len(path)==2 and abs(path[1][0]-path[0][0])==2)
                col    = CK_CAPTURE_COL if is_cap else CK_MOVE_COL
                # In kb mode, highlight the currently selected destination brighter
                is_kb_dest = (self._kb_mode and g.selected is not None
                              and self._kb_dest_list
                              and (tr, tc) == self._kb_dest_list[self._kb_dest_idx])
                alpha_fill   = 90  if is_kb_dest else 50
                alpha_border = 255 if is_kb_dest else 210
                s = pygame.Surface((cell, cell), pygame.SRCALPHA)
                s.fill((*col, alpha_fill))
                surf.blit(s, (bx+tc*cell, by+tr*cell))
                pygame.draw.rect(surf, (*col, alpha_border),
                    (bx+tc*cell+2, by+tr*cell+2, cell-4, cell-4),
                    3 if is_kb_dest else 2, border_radius=3)

        # Keyboard cursor — animated pulsing ring
        if self._kb_mode and not self._anim_path and not self.game.game_over:
            if not (self.vs_ai and g.turn == CK_RED):
                kr, kc = self._kb_cursor
                cx = bx + kc*cell + cell//2
                cy = by + kr*cell + cell//2
                pulse = (math.sin(pygame.time.get_ticks() * 0.007) + 1) / 2
                radius = cell//2 - 2
                # Outer glow
                for i in range(4, 0, -1):
                    gs = pygame.Surface((radius*2+i*4, radius*2+i*4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (255,255,255, int(pulse*30)),
                        (radius+i*2, radius+i*2), radius+i*2)
                    surf.blit(gs, (cx-radius-i*2, cy-radius-i*2))
                # Solid ring
                ring_col = CK_CAPTURE_COL if g.selected else (255, 255, 255)
                lw = 3
                pygame.draw.circle(surf, ring_col, (cx, cy), radius, lw)

    def _draw_pieces(self, surf):
        radius = self.cell//2 - 5

        # Which square to skip (the piece currently animating)
        anim_px = anim_py = None
        if self._anim_path and len(self._anim_path) >= 2:
            t  = self._anim_t
            t  = t * t * (3 - 2 * t)   # smoothstep
            fx, fy = self._anim_from
            tx, ty = self._anim_to
            anim_px = int(fx + (tx - fx) * t)
            anim_py = int(fy + (ty - fy) * t)

        for r in range(CK_SIZE):
            for c in range(CK_SIZE):
                p = self.game.board[r][c]
                if p == CK_EMPTY: continue
                if self._anim_path and (r, c) == self._anim_path[0]:
                    continue
                cx, cy = self._sq_center(r, c)
                self._draw_piece(surf, cx, cy, p, radius)

        # Draw animating piece on top
        if anim_px is not None:
            self._draw_piece(surf, anim_px, anim_py, self._anim_piece, radius)

    def _draw_piece(self, surf, cx, cy, piece, radius):
        is_b     = _ck_is_black(piece)
        main_col = CK_BLACK_COL if is_b else CK_RED_COL
        rim_col  = CK_BLACK_RIM  if is_b else CK_RED_RIM
        # Shadow
        s = pygame.Surface((radius*2+6, radius*2+6), pygame.SRCALPHA)
        pygame.draw.circle(s, (0,0,0,80), (radius+3, radius+5), radius)
        surf.blit(s, (cx-radius-3, cy-radius-3))
        # Disc
        pygame.draw.circle(surf, main_col, (cx, cy), radius)
        pygame.draw.circle(surf, rim_col,  (cx, cy), radius, 3)
        # Highlight arc
        hi = tuple(min(255, v+60) for v in main_col)
        pygame.draw.arc(surf, hi,
            (cx-radius+6, cy-radius+6, (radius-6)*2, (radius-6)*2),
            math.radians(30), math.radians(150), 3)
        # King marker
        if _ck_is_king(piece):
            pygame.draw.circle(surf, CK_CROWN, (cx, cy), radius//2, 2)
            pygame.draw.circle(surf, CK_CROWN, (cx, cy), radius//4)

    def _draw_status(self, surf, W, H):
        fam    = next((c for c in ['segoeui','helvetica','freesans']
                       if pygame.font.match_font(c)), None)
        fnt    = pygame.font.SysFont(fam, 18, bold=True) if fam else pygame.font.Font(None, 18)
        fnt_sm = pygame.font.SysFont(fam, 13)             if fam else pygame.font.Font(None, 13)

        # Turn indicator above board
        if not self.game.game_over:
            is_black_turn = self.game.turn == CK_BLACK
            if self._anim_path and len(self._anim_path) > 2:
                label = "Multi-jump!"
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
                col   = lerp_color(CK_CAPTURE_COL, (255, 255, 255), pulse * 0.4)
            elif self.vs_ai and not is_black_turn and self._ai_pending:
                label = "AI is thinking..."
                col   = lerp_color(CK_RED_RIM, (255,200,200),
                                   abs(math.sin(pygame.time.get_ticks()*0.003)))
            elif self.vs_ai:
                label = "Your turn (Black)" if is_black_turn else "AI's turn (Red)"
                col   = CK_BLACK_RIM if is_black_turn else CK_RED_RIM
            else:
                label = "Black's turn" if is_black_turn else "Red's turn"
                col   = CK_BLACK_RIM if is_black_turn else CK_RED_RIM
            t = fnt.render(label, True, col)
            surf.blit(t, (W//2 - t.get_width()//2, self.by - 38))

        # ── Right-side scoreboard ─────────────────────────────────
        b_count = sum(1 for r in range(CK_SIZE) for c in range(CK_SIZE)
                      if _ck_is_black(self.game.board[r][c]))
        r_count = sum(1 for r in range(CK_SIZE) for c in range(CK_SIZE)
                      if _ck_is_red(self.game.board[r][c]))

        sb_x     = self.bx + self.bsize + 18
        sb_w     = 64
        sb_pad   = 6
        item_h   = sb_w + 4
        total_h  = item_h * 2 + sb_pad
        sb_y     = self.by + self.bsize // 2 - total_h // 2

        fnt_cnt  = pygame.font.SysFont(fam, 26, bold=True) if fam \
                   else pygame.font.Font(None, 26)

        for i, (count, piece_col, rim_col, active) in enumerate([
            (r_count, CK_RED_COL,   CK_RED_RIM,   self.game.turn == CK_RED),
            (b_count, CK_BLACK_COL, CK_BLACK_RIM, self.game.turn == CK_BLACK),
        ]):
            iy = sb_y + i * (item_h + sb_pad)
            # Card background
            card_col = (30, 30, 30) if active else (18, 18, 20)
            border   = rim_col if active else (45, 45, 50)
            pygame.draw.rect(surf, card_col,
                (sb_x, iy, sb_w, item_h), border_radius=10)
            pygame.draw.rect(surf, border,
                (sb_x, iy, sb_w, item_h), 2, border_radius=10)

            # Piece disc icon
            disc_cx = sb_x + sb_w // 2
            disc_cy = iy + sb_w // 2 - 4
            disc_r  = sb_w // 2 - 10
            pygame.draw.circle(surf, piece_col, (disc_cx, disc_cy), disc_r)
            pygame.draw.circle(surf, rim_col,   (disc_cx, disc_cy), disc_r, 3)
            hi = tuple(min(255, v+60) for v in piece_col)
            pygame.draw.arc(surf, hi,
                (disc_cx-disc_r+4, disc_cy-disc_r+4,
                 (disc_r-4)*2, (disc_r-4)*2),
                math.radians(30), math.radians(150), 2)

            # Count
            ct = fnt_cnt.render(str(count), True, (240, 240, 240))
            surf.blit(ct, (disc_cx - ct.get_width()//2,
                           iy + item_h - ct.get_height() - 4))

        # Bottom hint
        hint = fnt_sm.render(
            "Click or arrow keys to navigate  ·  Enter to select/move  ·  R restart  ·  Esc menu",
            True, (100, 70, 35))
        surf.blit(hint, (W//2 - hint.get_width()//2,
                         self.by + self.bsize + 10))

    def _draw_overlay(self, surf, W, H):
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 155))
        surf.blit(dim, (0, 0))
        fam     = next((c for c in ['segoeui','helvetica','freesans']
                        if pygame.font.match_font(c)), None)
        fnt_big = pygame.font.SysFont(fam, 52, bold=True) if fam else pygame.font.Font(None, 52)
        fnt_sm  = pygame.font.SysFont(fam, 20)             if fam else pygame.font.Font(None, 20)
        w = self.game.winner
        if w == CK_BLACK:
            msg, col = ("YOU WIN!" if self.vs_ai else "BLACK WINS!"), (180, 180, 180)
        elif w == CK_RED:
            msg, col = ("AI WINS!" if self.vs_ai else "RED WINS!"), CK_RED_RIM
        else:
            msg, col = "DRAW!", (200, 180, 120)
        t1 = fnt_big.render(msg, True, col)
        t2 = fnt_sm.render("(R) play again   ·   (Esc) menu", True, (160, 130, 80))
        surf.blit(t1, (W//2 - t1.get_width()//2, H//2 - 55))
        surf.blit(t2, (W//2 - t2.get_width()//2, H//2 + 14))
