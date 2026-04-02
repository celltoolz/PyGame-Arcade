from core.constants import WIN_COMBOS, AI_DEPTHS

# ──────────────────────────────────────────────
#  3D AI  —  heuristic minimax (depth-limited)
# ──────────────────────────────────────────────
def _face_score(board, player):
    """Score a single face board for `player`. Higher = better for player."""
    opp = 'O' if player=='X' else 'X'
    score = 0
    for a,b,c in WIN_COMBOS:
        cells = [board[a], board[b], board[c]]
        p_cnt = cells.count(player)
        o_cnt = cells.count(opp)
        if o_cnt == 0:
            score += (1, 10, 100)[p_cnt-1] if p_cnt else 0
        if p_cnt == 0:
            score -= (1, 10, 100)[o_cnt-1] if o_cnt else 0
    return score

def _eval_state(boards, face_winner, player):
    """Heuristic evaluation of the full cube state."""
    opp = 'O' if player=='X' else 'X'
    FACES_NEEDED = 3
    wx = sum(1 for w in face_winner if w==player)
    wo = sum(1 for w in face_winner if w==opp)
    if wx >= FACES_NEEDED: return  10000
    if wo >= FACES_NEEDED: return -10000

    score = wx * 500 - wo * 500

    # Face-level tactical score
    for f in range(6):
        if face_winner[f] is None:
            score += _face_score(boards[f], player)

    # Reward spreading — count distinct faces player has any presence on
    player_faces = sum(1 for f in range(6)
                       if face_winner[f] is None
                       and any(v == player for v in boards[f]))
    opp_faces    = sum(1 for f in range(6)
                       if face_winner[f] is None
                       and any(v == opp for v in boards[f]))
    score += (player_faces - opp_faces) * 30

    return score

def _check_face_winner(board):
    for a,b,c in WIN_COMBOS:
        if board[a] and board[a]==board[b]==board[c]: return board[a]
    if all(board): return 'draw'
    return None

def _score_move(boards, face_winner, f, c, player):
    """Quick heuristic score for a single move — used to order moves before searching."""
    opp = 'O' if player=='X' else 'X'
    nb  = list(boards[f]); nb[c] = player
    fw  = _check_face_winner(nb)
    if fw == player: return 1000      # wins the face immediately
    nb2 = list(boards[f]); nb2[c] = opp
    if _check_face_winner(nb2) == opp: return 500   # blocks opponent face win

    # How many cells does this player already have on this face?
    face_count = sum(1 for v in boards[f] if v == player)

    # How many OTHER faces has this player touched at all?
    faces_with_presence = sum(1 for fi in range(6)
                               if fi != f
                               and face_winner[fi] is None
                               and any(v == player for v in boards[fi]))

    # Strong diversity bonus for playing on a new face
    is_new_face = not any(v == player for v in boards[f])
    new_face_bonus = 60 if is_new_face else 0

    # Reward faces where we already have a foothold (but not too many)
    foothold_bonus = min(face_count, 2) * 8

    # Heavy penalty for piling onto an already-developed face
    concentration_penalty = max(0, face_count - 2) * 25

    # Cell position preference
    cell_pref = {4: 10, 0: 5, 2: 5, 6: 5, 8: 5, 1: 1, 3: 1, 5: 1, 7: 1}

    return (cell_pref.get(c, 0)
            + new_face_bonus
            + foothold_bonus
            - concentration_penalty
            + faces_with_presence * 5)

def ai_best_move(boards, face_winner, ai_player, depth=3):
    """Return (face, cell) for the best AI move."""
    opp = 'O' if ai_player=='X' else 'X'
    FACES_NEEDED = 3

    # ── Transposition table ──────────────────────────────────────────
    # Maps board_key → (depth_searched, flag, value)
    # flag: 'exact' | 'lower' (alpha) | 'upper' (beta)
    ttable = {}
    tt_hits = [0]   # mutable so inner func can increment

    def board_key(boards, face_winner, is_max):
        """Hashable key for the current game state."""
        return (
            tuple(tuple(b) for b in boards),
            tuple(face_winner),
            is_max
        )

    def order_moves(boards, face_winner, moves, current_player):
        """Sort moves best-first for the given player."""
        scored = [(_score_move(boards, face_winner, f, c, current_player), f, c)
                  for f, c in moves]
        scored.sort(reverse=True)
        return [(f, c) for _, f, c in scored]

    def minimax(boards, face_winner, is_max, depth, alpha, beta):
        wx = sum(1 for w in face_winner if w==ai_player)
        wo = sum(1 for w in face_winner if w==opp)
        if wx >= FACES_NEEDED: return  10000
        if wo >= FACES_NEEDED: return -10000
        if depth == 0:
            return _eval_state(boards, face_winner, ai_player)

        moves = [(f,c) for f in range(6) for c in range(9)
                 if boards[f][c] is None and face_winner[f] is None]
        if not moves:
            return _eval_state(boards, face_winner, ai_player)

        # ── Transposition table lookup ──
        key = board_key(boards, face_winner, is_max)
        if key in ttable:
            cached_depth, flag, cached_val = ttable[key]
            if cached_depth >= depth:
                tt_hits[0] += 1
                if flag == 'exact':
                    return cached_val
                elif flag == 'lower':
                    alpha = max(alpha, cached_val)
                elif flag == 'upper':
                    beta  = min(beta,  cached_val)
                if alpha >= beta:
                    return cached_val

        orig_alpha = alpha
        current = ai_player if is_max else opp
        moves   = order_moves(boards, face_winner, moves, current)

        if is_max:
            best = -99999
            for f,c in moves:
                new_boards = [list(b) for b in boards]
                new_fw     = list(face_winner)
                new_boards[f][c] = current
                fw = _check_face_winner(new_boards[f])
                if fw: new_fw[f] = fw
                val = minimax(new_boards, new_fw, False, depth-1, alpha, beta)
                best = max(best, val)
                alpha = max(alpha, best)
                if beta <= alpha: break
        else:
            best = 99999
            for f,c in moves:
                new_boards = [list(b) for b in boards]
                new_fw     = list(face_winner)
                new_boards[f][c] = current
                fw = _check_face_winner(new_boards[f])
                if fw: new_fw[f] = fw
                val = minimax(new_boards, new_fw, True, depth-1, alpha, beta)
                best = min(best, val)
                beta  = min(beta, best)
                if beta <= alpha: break

        # ── Store result in transposition table ──
        if best <= orig_alpha:
            flag = 'upper'
        elif best >= beta:
            flag = 'lower'
        else:
            flag = 'exact'
        ttable[key] = (depth, flag, best)

        return best

    moves = [(f,c) for f in range(6) for c in range(9)
             if boards[f][c] is None and face_winner[f] is None]
    if not moves: return None

    # Only short-circuit for truly decisive moves
    wx = sum(1 for w in face_winner if w==ai_player)
    wo = sum(1 for w in face_winner if w==opp)

    if wx == 2:
        for f,c in moves:
            nb = list(boards[f]); nb[c] = ai_player
            if _check_face_winner(nb) == ai_player:
                return (f,c)

    if wo == 2:
        for f,c in moves:
            nb = list(boards[f]); nb[c] = opp
            if _check_face_winner(nb) == opp:
                return (f,c)

    # Order root moves and search with minimax + transposition table
    moves_ordered = order_moves(boards, face_winner, moves, ai_player)
    best_val  = -99999
    best_move = moves_ordered[0]
    for f,c in moves_ordered:
        new_boards = [list(b) for b in boards]
        new_fw     = list(face_winner)
        new_boards[f][c] = ai_player
        fw = _check_face_winner(new_boards[f])
        if fw: new_fw[f] = fw
        val = minimax(new_boards, new_fw, False, depth-1, -99999, 99999)
        if val > best_val:
            best_val  = val
            best_move = (f,c)

    return best_move, tt_hits[0], len(ttable)
