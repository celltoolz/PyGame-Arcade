import random

# ══════════════════════════════════════════════════════════════════
#  TETRIS CONSTANTS
# ══════════════════════════════════════════════════════════════════

TETRIS_COLS   = 10
TETRIS_ROWS   = 20
TETRIS_FPS    = 60

# Tetrominoes: shape data [rotations][row][col]
TETROMINOES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)],
          [(1,0),(1,1),(1,2),(1,3)]],
    'O': [[(0,0),(0,1),(1,0),(1,1)]],
    'T': [[(0,1),(1,0),(1,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,1)],
          [(1,0),(1,1),(1,2),(2,1)],
          [(0,1),(1,0),(1,1),(2,1)]],
    'S': [[(0,1),(0,2),(1,0),(1,1)],
          [(0,1),(1,1),(1,2),(2,2)]],
    'Z': [[(0,0),(0,1),(1,1),(1,2)],
          [(0,2),(1,1),(1,2),(2,1)]],
    'J': [[(0,0),(1,0),(1,1),(1,2)],
          [(0,1),(0,2),(1,1),(2,1)],
          [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,0),(2,1)]],
    'L': [[(0,2),(1,0),(1,1),(1,2)],
          [(0,1),(1,1),(2,1),(2,2)],
          [(1,0),(1,1),(1,2),(2,0)],
          [(0,1),(0,2),(1,2),(2,2)]],
}

TETROMINO_COLORS = {
    'I': (0,   220, 220),
    'O': (220, 220,   0),
    'T': (160,   0, 220),
    'S': (0,   200,   0),
    'Z': (220,   0,   0),
    'J': (0,    80, 220),
    'L': (220, 140,   0),
}

TETRIS_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

# ══════════════════════════════════════════════════════════════════
#  TETRIS PIECE
# ══════════════════════════════════════════════════════════════════

class TetrisPiece:
    def __init__(self, shape=None):
        self.shape    = shape or random.choice(list(TETROMINOES.keys()))
        self.rotation = 0
        self.col      = TETRIS_COLS // 2 - 1
        self.row      = 0

    def cells(self, row=None, col=None, rotation=None):
        r = self.row      if row      is None else row
        c = self.col      if col      is None else col
        rot = self.rotation if rotation is None else rotation
        rotations = TETROMINOES[self.shape]
        pattern   = rotations[rot % len(rotations)]
        return [(r + dr, c + dc) for dr, dc in pattern]

    @property
    def color(self):
        return TETROMINO_COLORS[self.shape]


# ══════════════════════════════════════════════════════════════════
#  TETRIS GAME
# ══════════════════════════════════════════════════════════════════

class TetrisGame:
    def __init__(self):
        self.board      = [[None]*TETRIS_COLS for _ in range(TETRIS_ROWS)]
        self.piece      = TetrisPiece()
        self.next_piece = TetrisPiece()
        self.score      = 0
        self.level      = 1
        self.lines      = 0
        self.game_over  = False
        self.paused     = False
        self._drop_timer= 0.0
        self._lock_timer= 0.0
        self._locking   = False
        self._flash_rows= []
        self._flash_t   = 0.0
        self.last_clear = 0   # lines cleared by the most recent piece lock

    def _drop_interval(self):
        return max(0.05, 0.8 - (self.level - 1) * 0.07)

    def _valid(self, piece, row=None, col=None, rotation=None):
        for r, c in piece.cells(row, col, rotation):
            if r < 0 or r >= TETRIS_ROWS or c < 0 or c >= TETRIS_COLS:
                return False
            if r >= 0 and self.board[r][c] is not None:
                return False
        return True

    def move(self, dr, dc):
        nr, nc = self.piece.row + dr, self.piece.col + dc
        if self._valid(self.piece, row=nr, col=nc):
            self.piece.row, self.piece.col = nr, nc
            if dr > 0: self._locking = False
            return True
        return False

    def rotate(self, direction=1):
        new_rot = (self.piece.rotation + direction) % len(TETROMINOES[self.piece.shape])
        # Wall kick attempts
        for kick in [0, -1, 1, -2, 2]:
            if self._valid(self.piece, col=self.piece.col+kick, rotation=new_rot):
                self.piece.col      += kick
                self.piece.rotation  = new_rot
                return True
        return False

    def hard_drop(self):
        while self.move(1, 0):
            self.score += 2
        self._lock_piece()

    def _lock_piece(self):
        for r, c in self.piece.cells():
            if 0 <= r < TETRIS_ROWS:
                self.board[r][c] = self.piece.color
        self.last_clear = 0   # reset before _clear_lines sets it
        self._clear_lines()
        self.piece      = self.next_piece
        self.next_piece = TetrisPiece()
        self._locking   = False
        self._lock_timer= 0.0
        if not self._valid(self.piece):
            self.game_over = True

    def _clear_lines(self):
        full = [r for r in range(TETRIS_ROWS) if all(self.board[r])]
        if full:
            self._flash_rows = full
            self._flash_t    = 0.4
            n = len(full)
            self.last_clear  = n   # ← record how many lines this piece cleared
            self.score += TETRIS_SCORES.get(n, 0) * self.level
            self.lines += n
            self.level  = self.lines // 10 + 1
            for r in full:
                del self.board[r]
                self.board.insert(0, [None]*TETRIS_COLS)

    def _ghost_row(self):
        r = self.piece.row
        while self._valid(self.piece, row=r+1):
            r += 1
        return r

    def update(self, dt, soft_drop=False):
        if self.game_over or self.paused: return
        if self._flash_t > 0:
            self._flash_t -= dt
            return
        self._flash_rows = []

        # Auto-drop — soft drop uses a much faster interval
        interval = 0.05 if soft_drop else self._drop_interval()
        self._drop_timer += dt
        if self._drop_timer >= interval:
            self._drop_timer = 0.0
            if self.move(1, 0):
                if soft_drop: self.score += 1
            else:
                self._locking = True

        # Lock delay
        if self._locking:
            self._lock_timer += dt
            if self._lock_timer >= 0.5:
                self._lock_piece()

    def add_garbage(self, lines):
        """Send `lines` garbage rows from the bottom (one hole per row, random col)."""
        hole_col = random.randint(0, TETRIS_COLS - 1)
        for _ in range(lines):
            self.board.pop(0)
            row = [(180, 180, 180)] * TETRIS_COLS
            row[hole_col] = None
            self.board.append(row)
        # If current piece is now invalid, push it up
        while not self._valid(self.piece):
            self.piece.row -= 1
            if self.piece.row < -4:
                self.game_over = True
                break
