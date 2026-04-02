import random
from .game import CheckersGame, CK_SIZE, CK_EMPTY, CK_BLACK, CK_RED, _ck_is_black, _ck_is_red, _ck_is_king

# ══════════════════════════════════════════════════════════════════
#  CHECKERS AI
# ══════════════════════════════════════════════════════════════════

class CheckersAI:
    """Minimax with alpha-beta pruning."""

    DEPTHS   = {'easy': 1,    'medium': 4,  'hard': 7}
    EPSILONS = {'easy': 0.40, 'medium': 0.0, 'hard': 0.0}

    def __init__(self, difficulty='medium'):
        self.depth   = self.DEPTHS.get(difficulty, 4)
        self.epsilon = self.EPSILONS.get(difficulty, 0.0)
        self.player  = CK_RED

    def best_move(self, game):
        moves = game.get_all_moves_flat()
        if not moves: return None
        if self.epsilon > 0 and random.random() < self.epsilon:
            return random.choice(moves)
        best_val, best_mv = float('-inf'), moves[0]
        alpha, beta = float('-inf'), float('inf')
        for mv in moves:
            child = self._apply(game, mv)
            val   = self._minimax(child, self.depth-1, False, alpha, beta)
            if val > best_val:
                best_val, best_mv = val, mv
            alpha = max(alpha, best_val)
        return best_mv

    def _apply(self, game, mv):
        fr, fc, tr, tc = mv
        child = game.copy()
        child._refresh_moves()
        child.select(fr, fc)
        # Find the path to (tr, tc) from valid_moves (or build simple path)
        path = child.valid_moves.get((tr, tc), [(fr, fc), (tr, tc)])
        child.move_full_path(path)
        return child

    def _minimax(self, game, depth, is_max, alpha, beta):
        if game.game_over:
            if game.winner == self.player: return  50000 + depth
            if game.winner == 'draw':      return  0
            return -50000 - depth
        if depth == 0: return self._evaluate(game)
        moves = game.get_all_moves_flat()
        if not moves: return self._evaluate(game)
        if is_max:
            val = float('-inf')
            for mv in moves:
                val   = max(val, self._minimax(self._apply(game,mv), depth-1, False, alpha, beta))
                alpha = max(alpha, val)
                if alpha >= beta: break
        else:
            val = float('inf')
            for mv in moves:
                val  = min(val, self._minimax(self._apply(game,mv), depth-1, True, alpha, beta))
                beta = min(beta, val)
                if alpha >= beta: break
        return val

    def _evaluate(self, game):
        score = 0
        for r in range(CK_SIZE):
            for c in range(CK_SIZE):
                p = game.board[r][c]
                if p == CK_EMPTY: continue
                val = 3 if _ck_is_king(p) else 1
                centre = (3 - abs(c - 3.5)) * 0.1
                if _ck_is_red(p):
                    score += val + centre + r * 0.05
                else:
                    score -= val + centre + (CK_SIZE-1-r) * 0.05
        return score
