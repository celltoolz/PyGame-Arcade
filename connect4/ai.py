import random
from .game import C4_COLS, C4_ROWS, C4_EMPTY, C4_P1, C4_P2

# ══════════════════════════════════════════════════════════════════
#  CONNECT 4 AI
# ══════════════════════════════════════════════════════════════════

class Connect4AI:
    """Minimax with alpha-beta pruning and centre-weighted heuristic."""

    DEPTHS   = {'easy': 2,    'medium': 4,   'hard': 7}
    EPSILONS = {'easy': 0.45, 'medium': 0.1, 'hard': 0.0}

    def __init__(self, difficulty='medium'):
        self.depth   = self.DEPTHS.get(difficulty, 4)
        self.epsilon = self.EPSILONS.get(difficulty, 0.0)
        self.player  = C4_P2   # AI is always player 2

    def best_move(self, game):
        if not game.valid_cols():
            return None
        # Epsilon-greedy: play random move with probability epsilon
        if self.epsilon > 0 and random.random() < self.epsilon:
            return random.choice(game.valid_cols())
        if self.depth == 0:
            return random.choice(game.valid_cols())
        # Order cols centre-first for better pruning
        cols = sorted(game.valid_cols(),
                      key=lambda c: abs(c - C4_COLS // 2))
        best_col, best_val = cols[0], float('-inf')
        alpha, beta = float('-inf'), float('inf')
        for col in cols:
            child = game.copy()
            child.drop(col)
            val = self._minimax(child, self.depth - 1, False, alpha, beta)
            if val > best_val:
                best_val, best_col = val, col
            alpha = max(alpha, best_val)
        return best_col

    def _minimax(self, game, depth, is_max, alpha, beta):
        if game.game_over:
            if game.winner == self.player:      return  100000 + depth
            if game.winner == 'draw':           return  0
            return -100000 - depth
        if depth == 0:
            return self._score(game)

        cols = sorted(game.valid_cols(),
                      key=lambda c: abs(c - C4_COLS // 2))
        if is_max:
            val = float('-inf')
            for col in cols:
                child = game.copy()
                child.drop(col)
                val = max(val, self._minimax(child, depth-1, False, alpha, beta))
                alpha = max(alpha, val)
                if alpha >= beta: break
            return val
        else:
            val = float('inf')
            for col in cols:
                child = game.copy()
                child.drop(col)
                val = min(val, self._minimax(child, depth-1, True, alpha, beta))
                beta = min(beta, val)
                if alpha >= beta: break
            return val

    def _score(self, game):
        """Heuristic board score from AI's perspective."""
        score = 0
        opp   = C4_P1

        # Centre column preference
        centre = [game.board[r][C4_COLS//2] for r in range(C4_ROWS)]
        score += centre.count(self.player) * 6

        # Score all windows of 4
        for r in range(C4_ROWS):
            for c in range(C4_COLS - 3):
                w = [game.board[r][c+i] for i in range(4)]
                score += self._score_window(w, opp)
        for c in range(C4_COLS):
            for r in range(C4_ROWS - 3):
                w = [game.board[r+i][c] for i in range(4)]
                score += self._score_window(w, opp)
        for r in range(C4_ROWS - 3):
            for c in range(C4_COLS - 3):
                w = [game.board[r+i][c+i] for i in range(4)]
                score += self._score_window(w, opp)
            for c in range(3, C4_COLS):
                w = [game.board[r+i][c-i] for i in range(4)]
                score += self._score_window(w, opp)
        return score

    def _score_window(self, window, opp):
        ai_cnt  = window.count(self.player)
        opp_cnt = window.count(opp)
        emp_cnt = window.count(C4_EMPTY)
        if ai_cnt == 4:               return  1000
        if ai_cnt == 3 and emp_cnt==1: return  10
        if ai_cnt == 2 and emp_cnt==2: return   3
        if opp_cnt == 3 and emp_cnt==1: return -18   # block opponent threat
        return 0
