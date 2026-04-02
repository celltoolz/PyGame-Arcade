# ══════════════════════════════════════════════════════════════════
#  CONNECT 4 CONSTANTS
# ══════════════════════════════════════════════════════════════════

C4_COLS   = 7
C4_ROWS   = 6
C4_EMPTY  = 0
C4_P1     = 1   # crimson
C4_P2     = 2   # gold

# Colour palette — midnight ocean theme
C4_BG          = (8,   12,  28)
C4_BOARD_COL   = (18,  36,  90)
C4_BOARD_RIM   = (12,  24,  68)
C4_HOLE_DARK   = (6,   10,  22)
C4_P1_COL      = (230,  55,  75)   # crimson
C4_P1_GLOW     = (255, 120, 130)
C4_P2_COL      = (240, 195,  30)   # gold
C4_P2_GLOW     = (255, 230, 120)
C4_GHOST_ALPHA = 55
C4_WIN_PULSE   = (255, 255, 180)
C4_ACCENT      = (80, 140, 255)


# ══════════════════════════════════════════════════════════════════
#  CONNECT 4 GAME
# ══════════════════════════════════════════════════════════════════

class Connect4Game:
    """Pure game logic — no rendering."""

    def __init__(self):
        self.board      = [[C4_EMPTY]*C4_COLS for _ in range(C4_ROWS)]
        self.current    = C4_P1
        self.winner     = None      # C4_P1 / C4_P2 / 'draw'
        self.game_over  = False
        self.win_cells  = []        # list of (r,c) forming the winning 4
        self.last_col   = -1        # column of the most recent move
        self.last_row   = -1

    def reset(self):
        self.__init__()

    def valid_cols(self):
        return [c for c in range(C4_COLS) if self.board[0][c] == C4_EMPTY]

    def drop_row(self, col):
        """Return the row a piece would land in, or -1 if full."""
        for r in range(C4_ROWS - 1, -1, -1):
            if self.board[r][col] == C4_EMPTY:
                return r
        return -1

    def drop(self, col):
        """Place current player's piece. Returns True if successful."""
        if self.game_over or col < 0 or col >= C4_COLS:
            return False
        r = self.drop_row(col)
        if r < 0:
            return False
        self.board[r][col] = self.current
        self.last_col = col
        self.last_row = r
        win = self._check_win(r, col, self.current)
        if win:
            self.winner    = self.current
            self.win_cells = win
            self.game_over = True
        elif not self.valid_cols():
            self.winner    = 'draw'
            self.game_over = True
        else:
            self.current = C4_P2 if self.current == C4_P1 else C4_P1
        return True

    def _check_win(self, r, c, player):
        """Return list of 4 winning (r,c) cells, or None."""
        dirs = [(0,1),(1,0),(1,1),(1,-1)]
        for dr, dc in dirs:
            cells = [(r + dr*i, c + dc*i) for i in range(-3, 4)]
            for start in range(len(cells) - 3):
                window = cells[start:start+4]
                if all(0 <= wr < C4_ROWS and 0 <= wc < C4_COLS
                       and self.board[wr][wc] == player
                       for wr, wc in window):
                    return window
        return None

    def copy(self):
        g = Connect4Game()
        g.board    = [row[:] for row in self.board]
        g.current  = self.current
        g.winner   = self.winner
        g.game_over= self.game_over
        return g
