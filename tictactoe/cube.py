import math
import time
import random
import threading
import pygame

from core.constants import WIN_COMBOS, AI_MOVE_DELAY, AI_MOVE_DELAY_MIN, AI_MOVE_DELAY_MAX, AI_RANDOM_CHANCE, AI_DEPTHS
from core.colors import FACE_COLORS, X_COLOR, O_COLOR
from core.drawing import rot_x, rot_y, project, face_normal_z, lerp2, lerp_color, point_in_poly, draw_X, draw_O
from .ai import ai_best_move, _check_face_winner

# ──────────────────────────────────────────────
#  CUBE GAME LOGIC
# ──────────────────────────────────────────────
class CubeGame:
    FACES_NEEDED = 3

    _CRN = [
        (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
        (-1,-1, 1),(1,-1, 1),(1,1, 1),(-1,1, 1),
    ]
    _FACE_DEF = [
        (7, 6, 5, 4, "front"),
        (0, 1, 2, 3, "back"),
        (7, 3, 2, 6, "top"),
        (4, 5, 1, 0, "bottom"),
        (3, 7, 4, 0, "left"),
        (6, 2, 1, 5, "right"),
    ]

    def __init__(self):
        self.boards      = [[None]*9 for _ in range(6)]
        self.face_winner = [None]*6
        self.current     = 'X'
        self.winner      = None
        self.game_over   = False
        self.scores      = {'X':0,'O':0,'draw':0}
        self.cell_anim   = [[0.0]*9 for _ in range(6)]
        self.result_anim = 0.0
        self.yaw         = math.radians(30)
        self.pitch       = math.radians(-25)
        self.hover_face  = -1
        self.hover_cell  = -1
        self._quads      = []
        # AI
        self.ai_mode      = False
        self.ai_vs_ai     = False
        self.ai_pending   = False
        self.ai_move_at   = 0.0
        self.ai_difficulty= 'Hard'
        self.on_face_win  = None
        # Pending move for rotation-first mechanic
        self.pending_face = None
        self.pending_cell = None
        # Background thread for AI calculation
        self._ai_thread     = None
        self._ai_result     = None
        self._ai_random     = False
        self._ai_tt_stats   = (0, 0)
        self._ai_calc_start = 0.0
        self._game_start    = None   # set when first move is scheduled

    def reset_scores(self):
        self.scores = {'X':0,'O':0,'draw':0}

    def new_game(self):
        self.boards      = [[None]*9 for _ in range(6)]
        self.face_winner = [None]*6
        self.current     = 'X'
        self.winner      = None
        self.game_over   = False
        self.cell_anim   = [[0.0]*9 for _ in range(6)]
        self.result_anim = 0.0
        self.hover_face  = -1
        self.hover_cell  = -1
        self.ai_pending  = False
        self.pending_face= None
        self.pending_cell= None
        self._ai_thread  = None
        self._ai_result  = None
        self._ai_random  = False
        self._ai_tt_stats= (0, 0)
        self._game_start = None
        self._maybe_schedule_ai()

    def _maybe_schedule_ai(self):
        """Schedule an AI move if it's an AI player's turn."""
        if self.game_over: return
        if self.ai_vs_ai or (self.ai_mode and self.current=='O'):
            self.ai_pending = True
            self.ai_move_at = time.time() + self._natural_delay()

    def _natural_delay(self):
        """Return a varied delay to make AI feel more natural."""
        opp = 'O' if self.current=='X' else 'X'
        # Check if any face is close to being won or blocked — feel more deliberate
        important = False
        for f in range(6):
            if self.face_winner[f] is not None: continue
            board = self.boards[f]
            for a,b,c in WIN_COMBOS:
                cells = [board[a], board[b], board[c]]
                if cells.count(self.current)==2 and cells.count(None)==1:
                    important = True; break
                if cells.count(opp)==2 and cells.count(None)==1:
                    important = True; break
            if important: break
        # Base delay + jitter for naturalness
        base = AI_MOVE_DELAY_MAX if important else AI_MOVE_DELAY
        jitter = random.uniform(-0.12, 0.12)
        return max(AI_MOVE_DELAY_MIN, base + jitter)

    def check_face(self, f):
        b = self.boards[f]
        for a,b2,c in WIN_COMBOS:
            if b[a] and b[a]==b[b2]==b[c]: return b[a]
        if all(b): return 'draw'
        return None

    def play(self, face, cell):
        if self.game_over: return
        if self.boards[face][cell] is not None: return
        if self.face_winner[face] is not None: return
        # Block human clicks when AI is playing
        if self.ai_vs_ai: return
        if self.ai_mode and self.current=='O': return
        self._do_play(face, cell)

    def _do_play(self, face, cell):
        self.boards[face][cell] = self.current
        fw = self.check_face(face)
        if fw:
            self.face_winner[face] = fw
            if self.on_face_win:
                self.on_face_win(face, fw)
            wx = sum(1 for w in self.face_winner if w=='X')
            wo = sum(1 for w in self.face_winner if w=='O')
            if wx>=self.FACES_NEEDED:
                self.winner='X'; self.game_over=True; self.scores['X']+=1
            elif wo>=self.FACES_NEEDED:
                self.winner='O'; self.game_over=True; self.scores['O']+=1
            elif all(w is not None for w in self.face_winner):
                self.winner='draw'; self.game_over=True; self.scores['draw']+=1
            if self.game_over and self._game_start is not None:
                elapsed  = time.time() - self._game_start
                mode_str = "AI vs AI" if self.ai_vs_ai else "vs AI"
                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[GAME END]  {mode_str} | Winner: {self.winner} | "
                      f"Duration: {elapsed:.1f}s | {ts}")
                print("-" * 60)
        if not self.game_over:
            self.current = 'O' if self.current=='X' else 'X'
            self._maybe_schedule_ai()

    def update(self, dt):
        """Call every frame — launches AI calc in background, polls for result."""
        self.update_animations(dt)
        if self.game_over: return

        # ── Phase 1: delay expired → launch background thread ──
        if (self.ai_pending
                and self._ai_thread is None
                and time.time() >= self.ai_move_at):
            self.ai_pending = False
            player = self.current if self.ai_vs_ai else 'O'
            depth  = AI_DEPTHS['Hard'] if self.ai_vs_ai else AI_DEPTHS[self.ai_difficulty]
            # Snapshot board state for the thread (thread must not touch self)
            boards_snap     = [list(b) for b in self.boards]
            fw_snap         = list(self.face_winner)
            self._ai_result = None
            self._ai_calc_start = time.time()
            # Log game start on the very first move
            if self._game_start is None:
                self._game_start = time.time()
                mode_str = "AI vs AI" if self.ai_vs_ai else "vs AI"
                diff_str = "Hard" if self.ai_vs_ai else self.ai_difficulty
                depth    = AI_DEPTHS['Hard'] if self.ai_vs_ai else AI_DEPTHS[self.ai_difficulty]
                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print("=" * 60)
                print(f"[GAME START] {mode_str} | Depth {depth} ({diff_str}) | {ts}")
                print("=" * 60)

            def _calc():
                choices = [(f,c) for f in range(6) for c in range(9)
                           if boards_snap[f][c] is None and fw_snap[f] is None]
                if not choices:
                    self._ai_result   = None
                    self._ai_random   = False
                    self._ai_tt_stats = (0, 0)
                    return

                opp = 'O' if player=='X' else 'X'
                opp_face_wins  = sum(1 for w in fw_snap if w==opp)
                must_play_best = opp_face_wins >= 2

                if (self.ai_vs_ai
                        and not must_play_best
                        and depth > 0
                        and random.random() < AI_RANDOM_CHANCE):
                    self._ai_result   = random.choice(choices)
                    self._ai_random   = True
                    self._ai_tt_stats = (0, 0)
                elif depth == 0:
                    self._ai_result   = random.choice(choices)
                    self._ai_random   = False
                    self._ai_tt_stats = (0, 0)
                else:
                    result = ai_best_move(boards_snap, fw_snap, player, depth=depth)
                    if isinstance(result, tuple) and len(result) == 3:
                        move, tt_hits, tt_size = result
                    else:
                        move, tt_hits, tt_size = result, 0, 0
                    self._ai_result   = move
                    self._ai_random   = False
                    self._ai_tt_stats = (tt_hits, tt_size)

            self._ai_thread = threading.Thread(target=_calc, daemon=True)
            self._ai_thread.start()

        # ── Phase 2: thread finished → log and hand move to pending ──
        if (self._ai_thread is not None
                and not self._ai_thread.is_alive()):
            self._ai_thread = None
            move      = self._ai_result
            is_random = self._ai_random
            tt_hits, tt_size = getattr(self, '_ai_tt_stats', (0, 0))
            self._ai_result   = None
            self._ai_random   = False
            self._ai_tt_stats = (0, 0)
            elapsed  = (time.time() - self._ai_calc_start) * 1000
            player   = self.current if self.ai_vs_ai else 'O'
            depth    = AI_DEPTHS['Hard'] if self.ai_vs_ai else AI_DEPTHS[self.ai_difficulty]
            mode_str = "AI vs AI" if self.ai_vs_ai else "vs AI"
            diff_str = "Hard" if self.ai_vs_ai else self.ai_difficulty
            tag      = " [RANDOM]" if is_random else ""
            tt_info  = f" | TT hits: {tt_hits} / {tt_size} entries" if tt_size > 0 else ""
            print(f"[AI] {mode_str} | Player {player} | Depth {depth} ({diff_str}) | "
                  f"Move: {move} | Calc time: {elapsed:.1f}ms{tt_info}{tag}")
            if move:
                self.pending_face, self.pending_cell = move

    def random_move(self):
        if self.game_over: return
        if self.ai_vs_ai: return
        if self.ai_mode and self.current=='O': return
        choices = [(f,c) for f in range(6) for c in range(9)
                   if self.boards[f][c] is None and self.face_winner[f] is None]
        if choices: self._do_play(*random.choice(choices))

    def update_animations(self, dt):
        for f in range(6):
            for c in range(9):
                if self.boards[f][c] and self.cell_anim[f][c]<1.0:
                    self.cell_anim[f][c]=min(1.0,self.cell_anim[f][c]+dt*6)
        if self.game_over:
            self.result_anim=min(1.0,self.result_anim+dt*2.5)

    # ── geometry ───────────────────────────────
    def _build_quads(self, cx, cy, size):
        rotated = rot_y(rot_x(self._CRN, self.pitch), self.yaw)
        fov = size * 3.8
        quads = []
        for fi,(tl_i,tr_i,br_i,bl_i,_) in enumerate(self._FACE_DEF):
            corners3 = [rotated[i] for i in (tl_i,tr_i,br_i,bl_i)]
            pts2 = [project(p[0]*size, p[1]*size, p[2]*size, cx, cy, fov)
                    for p in corners3]
            nz   = face_normal_z(pts2)
            avgz = sum(p[2] for p in pts2)/4
            quads.append({'fi':fi,'pts2':pts2,'avg_z':avgz,'visible':nz>0,'nz':nz})
        quads.sort(key=lambda q:q['avg_z'])
        return quads

    def _cell_corners(self, face_pts2, row, col):
        tl,tr,br,bl = face_pts2
        c0,c1 = col/3, (col+1)/3
        r0,r1 = row/3, (row+1)/3
        def corner(cu,rv):
            return lerp2(lerp2(tl,tr,cu), lerp2(bl,br,cu), rv)
        return [corner(c0,r0),corner(c1,r0),corner(c1,r1),corner(c0,r1)]

    def hit_test(self, mx, my):
        for q in reversed(self._quads):
            if not q['visible']: continue
            pts2 = [(int(p[0]),int(p[1])) for p in q['pts2']]
            if not point_in_poly(mx,my,pts2): continue
            for cell in range(9):
                row,col=divmod(cell,3)
                cq = self._cell_corners(q['pts2'],row,col)
                cqi= [(int(p[0]),int(p[1])) for p in cq]
                if point_in_poly(mx,my,cqi):
                    return q['fi'],cell
        return -1,-1

    def draw_cube(self, surf, cx, cy, size, mouse_pos):
        self._quads = self._build_quads(cx, cy, size)
        mx,my = mouse_pos
        # Only show hover when it's the human's turn
        if not self.game_over and not (self.ai_mode and self.current=='O'):
            self.hover_face,self.hover_cell = self.hit_test(mx,my)
        else:
            self.hover_face = self.hover_cell = -1

        for q in self._quads:
            if not q['visible']: continue
            fi   = q['fi']
            pts2 = q['pts2']
            ipts = [(int(p[0]),int(p[1])) for p in pts2]
            base = FACE_COLORS[fi]
            max_nz = size*size*0.25
            light  = 0.5 + 0.5*min(1.0, abs(q['nz'])/(max_nz+1))
            shaded = tuple(min(255,int(c*light)) for c in base)
            pygame.draw.polygon(surf, shaded, ipts)

            fw = self.face_winner[fi]
            if fw and fw != 'draw':
                fcx = int(sum(p[0] for p in pts2)/4)
                fcy = int(sum(p[1] for p in pts2)/4)
                stamp = size*0.52
                col   = X_COLOR if fw=='X' else O_COLOR
                alp   = int(min(1.0,self.result_anim*2)*200+55)
                if fw=='X': draw_X(surf,fcx,fcy,stamp,col,alp,0.17)
                else:       draw_O(surf,fcx,fcy,stamp,col,alp,0.17)
            else:
                board = self.boards[fi]
                for cell in range(9):
                    row,col=divmod(cell,3)
                    cq  = self._cell_corners(pts2,row,col)
                    cqi = [(int(p[0]),int(p[1])) for p in cq]
                    is_hov = (fi==self.hover_face and cell==self.hover_cell
                              and board[cell] is None and not self.game_over
                              and fw is None)
                    cell_col = lerp_color(shaded,(255,255,255),
                                          0.22 if is_hov else 0.09)
                    pygame.draw.polygon(surf, cell_col, cqi)
                    if board[cell]:
                        prog = self.cell_anim[fi][cell]
                        alp  = int(prog*220)
                        ccx  = sum(p[0] for p in cqi)//4
                        ccy  = sum(p[1] for p in cqi)//4
                        msz  = size*0.13
                        mc   = X_COLOR if board[cell]=='X' else O_COLOR
                        if board[cell]=='X': draw_X(surf,ccx,ccy,msz,mc,alp,0.20)
                        else:                draw_O(surf,ccx,ccy,msz,mc,alp,0.20)
                    pygame.draw.polygon(surf,(0,0,0),cqi,1)

                tl,tr,br,bl = pts2
                for t in (1/3, 2/3):
                    top_l=lerp2(tl,tr,t); bot_l=lerp2(bl,br,t)
                    lft_l=lerp2(tl,bl,t); rgt_l=lerp2(tr,br,t)
                    pygame.draw.line(surf,(0,0,0),(int(top_l[0]),int(top_l[1])),
                                     (int(bot_l[0]),int(bot_l[1])),2)
                    pygame.draw.line(surf,(0,0,0),(int(lft_l[0]),int(lft_l[1])),
                                     (int(rgt_l[0]),int(rgt_l[1])),2)

            pygame.draw.polygon(surf,(20,20,20),ipts,2)
