# ══════════════════════════════════════════════════════════════════
#  CHECKERS CONSTANTS
# ══════════════════════════════════════════════════════════════════

CK_EMPTY   = 0
CK_BLACK   = 1   # player 1 — moves up (decreasing row)
CK_RED     = 2   # player 2 / AI — moves down (increasing row)
CK_BLACK_K = 3   # black king
CK_RED_K   = 4   # red king
CK_SIZE    = 8

# Colour palette — warm wood theme
CK_LIGHT       = (210, 165,  95)
CK_DARK        = (145,  82,  30)
CK_BOARD_BG    = (100,  55,  15)
CK_BORDER      = ( 60,  35,   8)
CK_BLACK_COL   = ( 28,  28,  28)
CK_BLACK_RIM   = ( 75,  75,  75)
CK_RED_COL     = (200,  35,  35)
CK_RED_RIM     = (240, 100, 100)
CK_CROWN       = (255, 215,   0)
CK_SEL_COL     = (255, 255, 255)
CK_MOVE_COL    = (255, 255, 255)
CK_CAPTURE_COL = (255, 200,  50)


def _ck_is_black(p): return p in (CK_BLACK,  CK_BLACK_K)
def _ck_is_red(p):   return p in (CK_RED,    CK_RED_K)
def _ck_is_king(p):  return p in (CK_BLACK_K, CK_RED_K)
def _ck_owner(p):    return CK_BLACK if _ck_is_black(p) else (CK_RED if _ck_is_red(p) else CK_EMPTY)


# ══════════════════════════════════════════════════════════════════
#  CHECKERS GAME
# ══════════════════════════════════════════════════════════════════

class CheckersGame:
    """Full English draughts logic."""

    def __init__(self, force_jump=True):
        self.force_jump  = force_jump
        self.mid_jump    = False
        self.board       = self._initial_board()
        self.turn        = CK_BLACK
        self.winner      = None
        self.game_over   = False
        self.selected    = None
        self.valid_moves = {}   # dest → full waypoint path (list of (r,c))
        self.all_moves   = {}   # piece → list of immediate dests (for AI / refresh)
        self._refresh_moves()

    def _initial_board(self):
        b = [[CK_EMPTY]*CK_SIZE for _ in range(CK_SIZE)]
        for r in range(CK_SIZE):
            for c in range(CK_SIZE):
                if (r + c) % 2 == 1:
                    if r < 3:   b[r][c] = CK_RED
                    elif r > 4: b[r][c] = CK_BLACK
        return b

    def _refresh_moves(self):
        captures, normals = {}, {}
        for r in range(CK_SIZE):
            for c in range(CK_SIZE):
                p = self.board[r][c]
                if _ck_owner(p) != self.turn: continue
                caps = self._get_captures(r, c)
                nors = self._get_normal_moves(r, c)
                if caps: captures[(r, c)] = caps
                if nors: normals[(r, c)]  = nors
        if self.force_jump:
            self.all_moves = captures if captures else normals
        else:
            self.all_moves = {**normals, **captures}
        self.mid_jump    = False
        self.selected    = None
        self.valid_moves = {}

    def _dirs(self, piece):
        if _ck_is_king(piece):  return [(-1,-1),(-1,1),(1,-1),(1,1)]
        if _ck_is_black(piece): return [(-1,-1),(-1,1)]
        return [(1,-1),(1,1)]

    def _get_normal_moves(self, r, c):
        moves = []
        for dr, dc in self._dirs(self.board[r][c]):
            nr, nc = r+dr, c+dc
            if 0 <= nr < CK_SIZE and 0 <= nc < CK_SIZE and self.board[nr][nc] == CK_EMPTY:
                moves.append((nr, nc))
        return moves

    def _get_captures(self, r, c, board=None):
        if board is None: board = self.board
        piece    = board[r][c]
        captures = []
        for dr, dc in self._dirs(piece):
            mr, mc = r+dr,   c+dc
            lr, lc = r+dr*2, c+dc*2
            if not (0 <= lr < CK_SIZE and 0 <= lc < CK_SIZE): continue
            mid = board[mr][mc]
            if _ck_owner(mid) not in (CK_EMPTY, _ck_owner(piece)) \
               and _ck_owner(mid) != CK_EMPTY \
               and board[lr][lc] == CK_EMPTY:
                captures.append((lr, lc))
        return captures

    def _get_all_capture_paths(self, r, c):
        """
        DFS through all possible jump chains from (r,c).
        Returns {(dest_r, dest_c): [waypoint_list including (r,c) as first item]}.
        Each unique reachable destination maps to the path that reaches it.
        """
        results = {}

        def dfs(cur_r, cur_c, board_state, path, captured_set):
            p = board_state[cur_r][cur_c]
            for dr, dc in self._dirs(p):
                mr, mc = cur_r+dr,   cur_c+dc
                lr, lc = cur_r+dr*2, cur_c+dc*2
                if not (0 <= lr < CK_SIZE and 0 <= lc < CK_SIZE): continue
                if (mr, mc) in captured_set: continue     # already jumped
                mid = board_state[mr][mc]
                if _ck_owner(mid) == CK_EMPTY:          continue
                if _ck_owner(mid) == _ck_owner(p):      continue
                if board_state[lr][lc] != CK_EMPTY:     continue
                # Simulate this capture
                nb = [row[:] for row in board_state]
                nb[cur_r][cur_c] = CK_EMPTY
                nb[mr][mc]       = CK_EMPTY
                np_ = p
                if p == CK_BLACK and lr == 0:          np_ = CK_BLACK_K
                elif p == CK_RED and lr == CK_SIZE-1:  np_ = CK_RED_K
                nb[lr][lc] = np_
                new_path    = path + [(lr, lc)]
                new_captured = captured_set | {(mr, mc)}
                results[(lr, lc)] = new_path
                dfs(lr, lc, nb, new_path, new_captured)

        dfs(r, c, self.board, [(r, c)], set())
        return results

    def select(self, r, c):
        """Select a piece. valid_moves maps ALL reachable dests → full path."""
        if (r, c) not in self.all_moves:
            return False
        self.selected = (r, c)
        # If there are captures, show all reachable capture destinations
        caps_anywhere = any(self._get_captures(pr, pc)
                            for pr in range(CK_SIZE) for pc in range(CK_SIZE)
                            if _ck_owner(self.board[pr][pc]) == self.turn)
        if caps_anywhere:
            paths = self._get_all_capture_paths(r, c)
            if paths:
                self.valid_moves = paths
                return True
        # Normal moves — path is just [origin, dest]
        self.valid_moves = {dest: [(r, c), dest]
                            for dest in self.all_moves[(r, c)]}
        return True

    def move_full_path(self, path):
        """
        Execute a complete path (list of (r,c) waypoints).
        Returns list of (mr, mc) captured squares in order.
        """
        captured = []
        piece    = self.board[path[0][0]][path[0][1]]
        for i in range(len(path) - 1):
            fr, fc = path[i]
            tr, tc = path[i+1]
            is_cap = abs(tr - fr) == 2
            self.board[fr][fc] = CK_EMPTY
            if is_cap:
                mr, mc = (fr+tr)//2, (fc+tc)//2
                captured.append((mr, mc))
                self.board[mr][mc] = CK_EMPTY
            if piece == CK_BLACK and tr == 0:          piece = CK_BLACK_K
            elif piece == CK_RED and tr == CK_SIZE-1:  piece = CK_RED_K
            self.board[tr][tc] = piece
        self.mid_jump = False
        self.turn     = CK_RED if self.turn == CK_BLACK else CK_BLACK
        self._refresh_moves()
        self._check_game_over()
        return captured

    def _check_game_over(self):
        black = sum(1 for r in range(CK_SIZE) for c in range(CK_SIZE) if _ck_is_black(self.board[r][c]))
        red   = sum(1 for r in range(CK_SIZE) for c in range(CK_SIZE) if _ck_is_red(self.board[r][c]))
        if black == 0:          self.winner = CK_RED;   self.game_over = True
        elif red == 0:          self.winner = CK_BLACK; self.game_over = True
        elif not self.all_moves:
            self.winner = CK_RED if self.turn == CK_BLACK else CK_BLACK
            self.game_over = True

    def copy(self):
        g = CheckersGame.__new__(CheckersGame)
        g.board       = [row[:] for row in self.board]
        g.force_jump  = self.force_jump
        g.mid_jump    = False
        g.turn        = self.turn
        g.winner      = self.winner
        g.game_over   = self.game_over
        g.selected    = None
        g.valid_moves = {}
        g.all_moves   = {}
        return g

    def get_all_moves_flat(self):
        return [(fr, fc, tr, tc)
                for (fr, fc), dests in self.all_moves.items()
                for (tr, tc) in dests]
