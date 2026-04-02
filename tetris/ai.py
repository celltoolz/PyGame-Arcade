from .game import TETROMINOES, TETRIS_COLS, TETRIS_ROWS

# ══════════════════════════════════════════════════════════════════
#  TETRIS AI
# ══════════════════════════════════════════════════════════════════

class TetrisAI:
    """
    Heuristic Tetris AI — direct port of gpergrossi/tetris-ai scoring.
    Primary signal: shared edges with stack/walls/floor.
    Secondary: holes, height, line clears, buried holes, left-column reservation.
    """

    # Difficulty presets — control speed only; scoring is fixed per gpergrossi
    DIFFICULTY_PRESETS = {
        'easy': {
            'think_delay':   0.70,
            'move_interval': 0.22,
            'lookahead':     False,
        },
        'medium': {
            'think_delay':   0.35,
            'move_interval': 0.13,
            'lookahead':     False,
        },
        'hard': {
            'think_delay':   0.15,
            'move_interval': 0.07,
            'lookahead':     True,
        },
    }

    # gpergrossi scoring weights
    # gpergrossi scoring weights (matched exactly to reference implementation)
    W_EDGES      =  3.0
    W_HOLES      = -8.0
    W_AVG_HEIGHT = -1.5
    W_MAX_HEIGHT = -0.5
    CLEAR_BONUS  = [0, 20, 80, 240, 800]
    CLEAR_MULT   = 1.0

    def __init__(self, difficulty='medium'):
        preset = self.DIFFICULTY_PRESETS.get(
            difficulty, self.DIFFICULTY_PRESETS['medium'])
        self.THINK_DELAY   = preset['think_delay']
        self.MOVE_INTERVAL = preset['move_interval']
        self.lookahead     = preset['lookahead']
        self._plan        = []
        self._move_timer  = 0.0
        self._think_timer = 0.0
        self._thinking    = True

    # ── board helpers ─────────────────────────────────────────────

    def _col_heights(self, board):
        heights = []
        for c in range(TETRIS_COLS):
            for r in range(TETRIS_ROWS):
                if board[r][c] is not None:
                    heights.append(TETRIS_ROWS - r)
                    break
            else:
                heights.append(0)
        return heights

    def _count_holes(self, board):
        holes = 0
        for c in range(TETRIS_COLS):
            found = False
            for r in range(TETRIS_ROWS):
                if board[r][c] is not None:
                    found = True
                elif found:
                    holes += 1
        return holes

    def _shared_edges(self, board, piece_shape, rotation, col, row):
        """Edges the placed piece shares with existing blocks, walls, or floor."""
        placed = set()
        for dr, dc in TETROMINOES[piece_shape][rotation % len(TETROMINOES[piece_shape])]:
            placed.add((row + dr, col + dc))
        score = 0
        for (r, c) in placed:
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if nc < 0 or nc >= TETRIS_COLS:      # wall
                    score += 1
                elif nr >= TETRIS_ROWS:               # floor
                    score += 1
                elif 0 <= nr < TETRIS_ROWS and board[nr][nc] is not None:
                    if (nr, nc) not in placed:        # stack contact
                        score += 1
        return score

    def _simulate_drop(self, board, piece, rotation, col):
        """Drop piece at col/rotation. Returns (new_board, lines_cleared, drop_row) or None."""
        rot = rotation % len(TETROMINOES[piece.shape])
        row = 0

        def valid(r):
            for dr, dc in TETROMINOES[piece.shape][rot]:
                nr, nc = r+dr, col+dc
                if nr < 0 or nr >= TETRIS_ROWS or nc < 0 or nc >= TETRIS_COLS:
                    return False
                if nr >= 0 and board[nr][nc] is not None:
                    return False
            return True

        if not valid(row):
            return None
        while valid(row + 1):
            row += 1

        new_board = [list(r) for r in board]
        for dr, dc in TETROMINOES[piece.shape][rot]:
            nr, nc = row+dr, col+dc
            if 0 <= nr < TETRIS_ROWS:
                new_board[nr][nc] = piece.color

        full = [r for r in range(TETRIS_ROWS) if all(new_board[r])]
        for r in full:
            del new_board[r]
            new_board.insert(0, [None]*TETRIS_COLS)

        return new_board, len(full), row

    def _score_placement(self, board, piece_shape, rotation, col):
        """
        gpergrossi scoring: shared edges primary, then holes/height/clears.
        Returns score or None if placement is invalid.
        """
        result = self._simulate_drop(
            board, type('P', (), {'shape': piece_shape,
                                  'color': (128,128,128)})(),
            rotation, col)
        if result is None:
            return None
        new_board, cleared, drop_row = result

        heights    = self._col_heights(new_board)
        max_height = max(heights)
        avg_height = sum(heights) / TETRIS_COLS
        holes      = self._count_holes(new_board)
        edges      = self._shared_edges(board, piece_shape, rotation, col, drop_row)

        score  = self.W_EDGES      * edges
        score += self.W_HOLES      * holes
        score += self.W_AVG_HEIGHT * avg_height
        score += self.W_MAX_HEIGHT * max_height
        score += self.CLEAR_BONUS[cleared] * self.CLEAR_MULT

        return score

    def _best_score_for_shape(self, board, piece_shape):
        """Best score achievable for any placement of piece_shape on board."""
        best = float('-inf')
        for rot in range(len(TETROMINOES[piece_shape])):
            for col in range(-2, TETRIS_COLS + 1):
                s = self._score_placement(board, piece_shape, rot, col)
                if s is not None and s > best:
                    best = s
        return best if best > float('-inf') else 0.0

    def best_placement(self, game):
        """Return (rotation, col) for the best placement of the current piece."""
        best_score = float('-inf')
        best_rot   = 0
        best_col   = game.piece.col
        shape      = game.piece.shape

        for rot in range(len(TETROMINOES[shape])):
            for col in range(-2, TETRIS_COLS + 1):
                s = self._score_placement(game.board, shape, rot, col)
                if s is None:
                    continue
                if self.lookahead:
                    # simulate the drop to get the resulting board for lookahead
                    result = self._simulate_drop(
                        game.board,
                        type('P', (), {'shape': shape, 'color': (128,128,128)})(),
                        rot, col)
                    if result is not None:
                        nb, _, _ = result
                        s += 0.5 * self._best_score_for_shape(nb, game.next_piece.shape)
                if s > best_score:
                    best_score = s
                    best_rot   = rot
                    best_col   = col

        return best_rot, best_col

    def plan(self, game):
        """
        Calculate best move and build an action plan (list of game method calls)
        to get the piece there step by step.
        """
        target_rot, target_col = self.best_placement(game)
        actions = []

        # Rotations first
        rot_diff = (target_rot - game.piece.rotation) % len(TETROMINOES[game.piece.shape])
        for _ in range(rot_diff):
            actions.append('rotate')

        # Horizontal moves
        col_diff = target_col - game.piece.col
        direction = 1 if col_diff > 0 else -1
        for _ in range(abs(col_diff)):
            actions.append('right' if direction > 0 else 'left')

        # Hard drop to finish
        actions.append('drop')
        self._plan        = actions
        self._move_timer  = 0.0
        self._think_timer = 0.0
        self._thinking    = True   # wait out think delay before first move

    def update(self, dt, game):
        """Execute the plan one step at a time. Re-plans if plan is empty."""
        if game.game_over or game.paused: return
        if game._flash_t > 0: return

        if not self._plan:
            self.plan(game)
            return

        # Think delay — pause before starting to move the piece
        if self._thinking:
            self._think_timer += dt
            if self._think_timer >= self.THINK_DELAY:
                self._thinking = False
            return

        self._move_timer += dt
        if self._move_timer >= self.MOVE_INTERVAL:
            self._move_timer = 0.0
            action = self._plan.pop(0)
            if action == 'rotate':
                game.rotate(1)
            elif action == 'left':
                game.move(0, -1)
            elif action == 'right':
                game.move(0, 1)
            elif action == 'drop':
                game.hard_drop()
                self._plan     = []
                self._thinking = True   # think before next piece too
