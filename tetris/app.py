import math
import pygame

from core.screen import SM
from .game import TetrisGame, TETROMINOES, TETRIS_COLS, TETRIS_ROWS, TETRIS_FPS
from .ai import TetrisAI

# ══════════════════════════════════════════════════════════════════
#  TETRIS APP
# ══════════════════════════════════════════════════════════════════

class TetrisApp:
    """Tetris — solo or vs AI. Returns 'menu' or 'quit'."""

    def __init__(self, config=None):
        self.config     = config or {'mode': 'solo'}
        self.vs_mode    = (self.config.get('mode') == 'vs_ai')
        self.watch_mode = (self.config.get('mode') == 'watch')
        difficulty      = self.config.get('difficulty', 'medium')
        self.screen     = SM.screen
        self.clock      = SM.clock
        self.game       = TetrisGame()
        self.ai_game    = TetrisGame() if self.vs_mode else None
        # AI drives both watch mode and vs mode
        self.ai         = TetrisAI(difficulty) if (self.vs_mode or self.watch_mode) else None
        self.watch_ai   = TetrisAI(difficulty) if self.watch_mode else None
        if self.vs_mode:
            SM.set_title(f"Tetris  —  vs AI  ({difficulty.capitalize()})")
        elif self.watch_mode:
            SM.set_title(f"Tetris  —  Watch AI  ({difficulty.capitalize()})")
        else:
            SM.set_title("Tetris")
        self._build_layout()
        self._das_dir    = 0
        self._das_timer  = 0.0
        self._das_delay  = 0.17
        self._das_repeat = 0.05
        self._soft_drop  = False

    def toggle_fs(self):
        self.screen = SM.toggle_fs()
        self._build_layout()

    def _build_layout(self):
        W, H = self.screen.get_size()
        if self.vs_mode:
            # Two boards side by side with a centre gap
            cell  = min((H - 80) // TETRIS_ROWS, (W - 80) // (TETRIS_COLS * 2 + 8))
            cell  = max(12, cell)
            bw    = cell * TETRIS_COLS
            bh    = cell * TETRIS_ROWS
            self.cell = cell
            self.bh   = bh
            self.bw   = bw
            sidebar_w = cell * 4 + 8
            centre_gap = max(24, int(W * 0.05))
            total_w = bw * 2 + sidebar_w * 2 + centre_gap
            ox      = (W - total_w) // 2
            self.by = (H - bh) // 2
            # Player board (left)
            self.bx        = ox + sidebar_w
            self.sidebar_x = ox
            # AI board (right)
            self.ai_bx        = ox + sidebar_w + bw + centre_gap
            self.ai_sidebar_x = self.ai_bx + bw + 4
            # Centre panel
            self.centre_x = self.bx + bw
            self.centre_w = centre_gap
        else:
            cell  = min((H - 80) // TETRIS_ROWS, (W // 2) // TETRIS_COLS)
            cell  = max(16, cell)
            bw    = cell * TETRIS_COLS
            bh    = cell * TETRIS_ROWS
            self.cell      = cell
            self.bw        = bw
            self.bh        = bh
            self.bx        = W // 2 - bw // 2 - cell * 2
            self.by        = (H - bh) // 2
            self.sidebar_x = self.bx + bw + cell

    def _new_game(self):
        difficulty = self.config.get('difficulty', 'medium')
        self.game  = TetrisGame()
        if self.vs_mode:
            self.ai_game = TetrisGame()
            self.ai      = TetrisAI(difficulty)
        if self.watch_mode:
            self.ai       = TetrisAI(difficulty)
            self.watch_ai = TetrisAI(difficulty)

    def run(self):
        while True:
            dt = self.clock.tick(TETRIS_FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fs()
                    elif event.key == pygame.K_ESCAPE:
                        return 'menu'
                    elif not self.watch_mode and not self.game.game_over and not self.game.paused:
                        if event.key == pygame.K_LEFT:
                            self.game.move(0, -1)
                            self._das_dir, self._das_timer = -1, 0.0
                        elif event.key == pygame.K_RIGHT:
                            self.game.move(0,  1)
                            self._das_dir, self._das_timer =  1, 0.0
                        elif event.key == pygame.K_DOWN:
                            self._soft_drop = True
                            self.game.move(1, 0)
                            self.game.score += 1
                        elif event.key == pygame.K_UP:
                            self.game.rotate(1)
                        elif event.key == pygame.K_z:
                            self.game.rotate(-1)
                        elif event.key == pygame.K_SPACE:
                            self.game.hard_drop()
                        elif event.key == pygame.K_p:
                            self.game.paused = not self.game.paused
                            if self.vs_mode and self.ai_game:
                                self.ai_game.paused = self.game.paused
                    if event.key == pygame.K_r:
                        self._new_game()

                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        self._das_dir = 0
                    if event.key == pygame.K_DOWN:
                        self._soft_drop = False

                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    self.screen = SM.on_resize(event.w, event.h)
                    self._build_layout()

            # DAS
            if self._das_dir != 0 and not self.game.game_over:
                self._das_timer += dt
                threshold = self._das_delay if self._das_timer < self._das_delay + self._das_repeat \
                            else self._das_repeat
                if self._das_timer >= threshold:
                    self._das_timer -= self._das_repeat
                    self.game.move(0, self._das_dir)

            self.screen = SM.screen

            # In vs mode, freeze both games once either player has lost
            vs_over = self.vs_mode and (self.game.game_over or
                      (self.ai_game and self.ai_game.game_over))

            if self.watch_mode:
                # AI fully controls the game — no player input processed
                if not self.game.game_over:
                    self.game.update(dt)
                    self.ai.update(dt, self.game)
            else:
                if not vs_over:
                    self.game.update(dt, soft_drop=self._soft_drop)

                if self.vs_mode and self.ai_game and self.ai and not vs_over:
                    self.ai_game.update(dt)
                    self.ai.update(dt, self.ai_game)

                    GARBAGE = {2: 1, 3: 2, 4: 4}
                    p_cleared  = self.game.last_clear
                    ai_cleared = self.ai_game.last_clear
                    self.game.last_clear    = 0
                    self.ai_game.last_clear = 0
                    if p_cleared >= 2 and not self.ai_game.game_over:
                        self.ai_game.add_garbage(GARBAGE.get(p_cleared, 1))
                    if ai_cleared >= 2 and not self.game.game_over:
                        self.game.add_garbage(GARBAGE.get(ai_cleared, 1))

            self._draw()

    # ── drawing ──────────────────────────────────────────────────

    def _draw(self):
        W, H = self.screen.get_size()
        self.screen.fill((8, 10, 18))
        for x in range(0, W, 32): pygame.draw.line(self.screen,(15,18,30),(x,0),(x,H))
        for y in range(0, H, 32): pygame.draw.line(self.screen,(15,18,30),(0,y),(W,y))

        if self.vs_mode:
            self._draw_board(self.game,    self.bx,    self.by, self.sidebar_x,    player=True)
            self._draw_board(self.ai_game, self.ai_bx, self.by, self.ai_sidebar_x, player=False)
            self._draw_vs_centre()
            both_over = self.game.game_over or self.ai_game.game_over
            if self.game.paused:
                self._draw_overlay("PAUSED", "(P) resume  ·  (R) restart  ·  (Esc) menu")
            elif both_over:
                if self.game.game_over and self.ai_game.game_over:
                    msg = "DRAW!"
                elif self.game.game_over:
                    msg = "AI WINS!"
                else:
                    msg = "YOU WIN!"
                self._draw_overlay(msg, "(R) play again  ·  (Esc) menu")
        else:
            self._draw_board(self.game, self.bx, self.by, self.sidebar_x, player=True)
            if self.watch_mode:
                # "WATCH MODE" badge in top-left of board
                W, H = self.screen.get_size()
                fnt = pygame.font.SysFont('segoeui', max(12, self.cell//2))
                badge = fnt.render("● WATCH MODE  —  Esc menu  ·  R restart", True, (0, 200, 180))
                self.screen.blit(badge, (self.bx, self.by - badge.get_height() - 6))
                if self.game.game_over:
                    self._draw_overlay("GAME OVER",
                        f"Score: {self.game.score}    (R) play again  ·  (Esc) menu")
            elif self.game.paused:
                self._draw_overlay("PAUSED", "(P) resume  ·  (R) restart  ·  (Esc) menu")
            elif self.game.game_over:
                self._draw_overlay("GAME OVER",
                    f"Score: {self.game.score}    (R) restart  ·  (Esc) menu")

        pygame.display.flip()

    def _draw_board(self, game, bx, by, sx, player=True):
        cell = self.cell
        bw   = self.bw
        bh   = self.bh

        # Board bg + border
        pygame.draw.rect(self.screen, (12,14,24), (bx-2, by-2, bw+4, bh+4))
        border_col = (35,40,65) if not game.game_over else (80,30,30)
        pygame.draw.rect(self.screen, border_col, (bx-2, by-2, bw+4, bh+4), 2)

        # Grid lines
        for r in range(TETRIS_ROWS+1):
            pygame.draw.line(self.screen,(20,24,38),(bx,by+r*cell),(bx+bw,by+r*cell))
        for c in range(TETRIS_COLS+1):
            pygame.draw.line(self.screen,(20,24,38),(bx+c*cell,by),(bx+c*cell,by+bh))

        # Placed cells
        for r in range(TETRIS_ROWS):
            for c in range(TETRIS_COLS):
                color = game.board[r][c]
                if color:
                    flash    = r in game._flash_rows
                    draw_col = (255,255,255) if flash and int(game._flash_t*10)%2==0 else color
                    self._draw_cell(bx+c*cell, by+r*cell, cell, draw_col)

        # Ghost + active piece
        if not game.game_over:
            gr = game._ghost_row()
            for r, c in game.piece.cells(row=gr):
                if 0 <= r < TETRIS_ROWS:
                    gx, gy = bx+c*cell, by+r*cell
                    s = pygame.Surface((cell-1,cell-1), pygame.SRCALPHA)
                    s.fill((*game.piece.color, 45))
                    self.screen.blit(s,(gx,gy))
                    pygame.draw.rect(self.screen,(*game.piece.color,90),(gx,gy,cell-1,cell-1),1)
            for r, c in game.piece.cells():
                if 0 <= r < TETRIS_ROWS:
                    self._draw_cell(bx+c*cell, by+r*cell, cell, game.piece.color)

        # Sidebar
        self._draw_sidebar(game, sx, by, cell, bh, player)

    def _draw_cell(self, x, y, size, color):
        r = pygame.Rect(x+1, y+1, size-2, size-2)
        pygame.draw.rect(self.screen, color, r, border_radius=3)
        hi = tuple(min(255, c+70) for c in color)
        pygame.draw.line(self.screen, hi, (x+2,y+2),(x+size-3,y+2), 1)
        pygame.draw.line(self.screen, hi, (x+2,y+2),(x+2,y+size-3), 1)

    def _draw_sidebar(self, game, sx, sy, cell, bh, player=True):
        fnt_lg = pygame.font.SysFont('segoeui', max(14, cell*2//3), bold=True)
        fnt_sm = pygame.font.SysFont('segoeui', max(11, cell//2))

        def label(text, y, col=(100,110,145)):
            t = fnt_sm.render(text, True, col)
            self.screen.blit(t, (sx, sy+y))

        def value(text, y, col=(220,225,245)):
            t = fnt_lg.render(text, True, col)
            self.screen.blit(t, (sx, sy+y))

        label("NEXT", 0)
        px, py = sx, sy + cell
        ps = cell * 4
        pygame.draw.rect(self.screen,(12,14,24),(px-2,py-2,ps+4,ps+4))
        pygame.draw.rect(self.screen,(35,40,65),(px-2,py-2,ps+4,ps+4),1)
        for dr, dc in TETROMINOES[game.next_piece.shape][0]:
            self._draw_cell(px+dc*cell, py+dr*cell, cell, game.next_piece.color)

        y0 = cell*5 + cell//2
        label("SCORE", y0);         value(str(game.score), y0+cell*2//3)
        label("LEVEL", y0+cell*2);  value(str(game.level), y0+cell*2+cell*2//3)
        label("LINES", y0+cell*4);  value(str(game.lines), y0+cell*4+cell*2//3)

        # Controls only on player sidebar in solo mode
        if player and not self.vs_mode:
            hy = sy + bh - cell*2
            for i,(k,v) in enumerate([("←→","Move"),("↑/Z","Rotate"),("↓","Soft drop"),
                                       ("Spc","Hard drop"),("P","Pause"),
                                       ("F11","Fullscreen"),("Esc","Menu")]):
                t = fnt_sm.render(f"{k}  {v}", True, (60,70,100))
                self.screen.blit(t,(sx, hy+i*(cell//2+3)))

    def _draw_vs_centre(self):
        """VS label and player/AI name tags."""
        W, _ = self.screen.get_size()
        cell  = self.cell
        cx    = self.centre_x
        cw    = self.centre_w
        by    = self.by
        bh    = self.bh

        fnt_vs  = pygame.font.SysFont('segoeui', max(22, cell+cell//2), bold=True)
        fnt_lbl = pygame.font.SysFont('segoeui', max(11, cell//2+2))

        vs = fnt_vs.render("VS", True, (55,65,105))
        self.screen.blit(vs, (cx+cw//2-vs.get_width()//2, by+bh//2-vs.get_height()//2))

        you = fnt_lbl.render("YOU",  True, (100,130,210))
        ai  = fnt_lbl.render("AI",   True, (210,100,100))
        self.screen.blit(you, (self.bx    + self.bw//2 - you.get_width()//2, by-cell-2))
        self.screen.blit(ai,  (self.ai_bx + self.bw//2 - ai.get_width()//2,  by-cell-2))

        hint = fnt_lbl.render("P pause  ·  R restart  ·  Esc menu", True, (38,46,65))
        self.screen.blit(hint,(W//2-hint.get_width()//2, by+bh+6))

    def _draw_overlay(self, title, sub):
        W, H = self.screen.get_size()
        dim = pygame.Surface((W,H), pygame.SRCALPHA)
        dim.fill((0,0,0,160))
        self.screen.blit(dim,(0,0))
        fnt_big = pygame.font.SysFont('segoeui', 48, bold=True)
        fnt_sm  = pygame.font.SysFont('segoeui', 20)
        t1 = fnt_big.render(title, True, (255,255,255))
        t2 = fnt_sm.render(sub,   True, (140,150,180))
        self.screen.blit(t1,(W//2-t1.get_width()//2, H//2-50))
        self.screen.blit(t2,(W//2-t2.get_width()//2, H//2+10))
