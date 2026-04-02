import math
import time
import random
import pygame

from core.constants import WIN_COMBOS, FPS, DEFAULT_W, DEFAULT_H
from core.colors import (BG_DARK, BG_PANEL, GRID_COLOR, GRID_HOVER, X_COLOR, O_COLOR,
                            WIN_LINE_COL, TEXT_MAIN, TEXT_DIM, ACCENT, BTN_RAND_BG, BTN_RAND_HOVER,
                            SCORE_X_BG, SCORE_O_BG, DRAW_BG, AI_THINKING_COL, FACE_COLORS)
from core.screen import SM
from core.drawing import draw_rounded_rect, draw_X, draw_O, draw_X_crisp, draw_O_crisp, lerp_color, lerp2
from core.widgets import Button
from core.particles import ParticleSystem
from .cube import CubeGame

# ──────────────────────────────────────────────
#  MAIN APP
# ──────────────────────────────────────────────
class TicTacToeApp:
    def __init__(self, config=None):
        config = config or {'mode': '2D', 'opponent': 'human', 'difficulty': 'Hard'}
        _mode       = config.get('mode', '2D')
        _opponent   = config.get('opponent', 'human')
        _difficulty = config.get('difficulty', 'Hard')

        SM.set_title("Tic  Tac  Toe")
        self.screen     = SM.screen
        self.clock      = SM.clock
        self.fullscreen = SM.fullscreen
        self.screen_w   = SM.win_w
        self.screen_h   = SM.win_h
        self.mode       = _mode

        # 2-D state
        self.board2       = [None]*9
        self.current2     = 'X'
        self.winner2      = None
        self.win_combo2   = None
        self.scores2      = {'X':0,'O':0,'draw':0}
        self.game_over2   = False
        self.hover_cell2  = -1
        self.cell_anim2   = [0.0]*9
        self.win_anim2    = 0.0
        self.result_anim2 = 0.0

        # 3-D state
        self.cube        = CubeGame()
        self.cube.ai_mode       = (_opponent == 'ai')
        self.cube.ai_vs_ai      = (_opponent == 'ai_vs_ai')
        self.cube.ai_difficulty = _difficulty
        self._drag       = False
        self._drag_start = None
        self._drag_yaw0  = 0.0
        self._drag_pit0  = 0.0
        # Particles
        self.particles   = ParticleSystem()
        self.cube.on_face_win = self._on_face_win
        # Smooth rotation-to-face
        self._rot_target_yaw   = None   # None = not animating
        self._rot_target_pitch = None
        # Face index → (yaw, pitch) that puts it squarely facing the camera
        # Note: back face uses -π not +π to avoid the ±π boundary ambiguity
        self._FACE_TARGET = [
            (math.radians(   0),  math.radians(  0)),   # 0 front   +z
            (math.radians(-180),  math.radians(  0)),   # 1 back    -z  (≡ +π but avoids boundary)
            (math.radians(   0),  math.radians( 90)),   # 2 top     +y
            (math.radians(   0),  math.radians(-90)),   # 3 bottom  -y
            (math.radians(  90),  math.radians(  0)),   # 4 left    -x
            (math.radians( -90),  math.radians(  0)),   # 5 right   +x
        ]
        self._panel_face_rects    = []
        self._auto_restart_at     = None
        self._rotating_to_pending = False
        self._rotation_started_at = None

        self._build_fonts()
        self._build_layout()
        # end-of-game overlay "Play Again" button (positioned in _draw_end_overlay)
        self._btn_again = Button("Play Again", 0, 0, 0, 0, self.font_btn,
                                 bg=(50,40,80), hover_bg=(80,65,130))

    # ── fonts ──────────────────────────────────
    def _build_fonts(self):
        scale = min(self.screen_w/DEFAULT_W, self.screen_h/DEFAULT_H)
        candidates = ["segoeui","helvetica","dejavusans","freesans"]
        fam = next((c for c in candidates if pygame.font.match_font(c)),None)
        def F(base,bold=False):
            sz=max(10,int(base*scale))
            return (pygame.font.SysFont(fam,sz,bold=bold) if fam
                    else pygame.font.Font(None,sz))
        self.font_title  = F(28,bold=True)
        self.font_score  = F(34,bold=True)
        self.font_label  = F(16)
        self.font_turn   = F(20,bold=True)
        self.font_result = F(30,bold=True)
        self.font_btn    = F(15)
        self.font_hint   = F(13)

    # ── layout ─────────────────────────────────
    def _build_layout(self):
        W,H  = self.screen_w,self.screen_h
        sc   = min(W/DEFAULT_W, H/DEFAULT_H)
        pad  = max(12,int(24*sc))
        hdr  = int(44*sc); scr=int(88*sc); sta=int(40*sc)
        bth  = int(46*sc); hnt=int(24*sc)
        ui_h = pad+hdr+pad+scr+pad + pad+sta+pad+bth+pad+hnt+pad

        # In 3D mode, reserve the left column for the face panel
        if self.mode=='3D':
            panel_w = max(90, int(W * 0.18))   # ~18% of width
            play_x  = pad + panel_w + pad       # left edge of playfield
            play_w  = W - play_x - pad
        else:
            panel_w = 0
            play_x  = pad
            play_w  = W - 2*pad

        bsz = max(120, min(play_w, H - ui_h))

        y=pad
        self.title_y=y; y+=hdr+pad
        self.score_top=y
        self.score_rect=pygame.Rect(pad,y,W-2*pad,scr); y+=scr+pad

        # Board / cube area
        bl = play_x + (play_w - bsz)//2
        bt = y
        self.board_rect=pygame.Rect(bl,bt,bsz,bsz)
        cs=bsz//3
        self.cell_rects=[]
        for r in range(3):
            for c in range(3):
                self.cell_rects.append(pygame.Rect(bl+c*cs,bt+r*cs,cs,cs))
        y+=bsz+pad

        self.status_top=y; y+=sta+pad

        # Cube centred in the play area
        self.cube_cx  = play_x + play_w//2
        self.cube_cy  = bt + bsz//2
        self.cube_size= bsz * 0.36

        # Face panel geometry (3D only) — 6 mini boards stacked in left column
        self.panel_x = pad
        self.panel_y = bt
        self.panel_w = panel_w
        self.panel_h = bsz

        # Buttons row — always 3 buttons: New Game | Random Move | Settings
        btn_top=y; gap=max(5,int(pad*0.35))
        btw=(W-2*pad-2*gap)//3
        btfs=max(11,int(bth*0.42))
        sc2=min(W/DEFAULT_W,H/DEFAULT_H)
        fam2=next((c for c in ["segoeui","helvetica","dejavusans","freesans"]
                   if pygame.font.match_font(c)),None)
        def F2(b,bold=False):
            sz=max(10,int(b*sc2))
            return (pygame.font.SysFont(fam2,sz,bold=bold) if fam2
                    else pygame.font.Font(None,sz))
        self.font_btn=F2(btfs)

        if not hasattr(self,'_btn_new'):
            self._btn_new  = Button("New Game",    0,0,0,0,self.font_btn)
            self._btn_rand = Button("Random Move", 0,0,0,0,self.font_btn,
                                    bg=BTN_RAND_BG,hover_bg=BTN_RAND_HOVER)
            self._btn_again= Button("Play Again",0,0,0,0,self.font_btn,
                                    bg=(50,40,80),hover_bg=(80,65,130))
        else:
            for b in (self._btn_new, self._btn_rand, self._btn_again):
                b.font = self.font_btn

        # Two-button layout: New Game | Random Move
        gap  = max(5, int(pad*0.35))
        btw  = (W - 2*pad - gap) // 2
        x0   = pad
        self._btn_new .reposition(x0,        btn_top, btw, bth)
        self._btn_rand.reposition(x0+btw+gap, btn_top, btw, bth)

        self.hint_y=btn_top+bth+int(pad*0.6)

    # ── 2-D logic ──────────────────────────────
    def _check2(self):
        for a,b,c in WIN_COMBOS:
            if self.board2[a] and self.board2[a]==self.board2[b]==self.board2[c]:
                return self.board2[a],(a,b,c)
        if all(self.board2): return 'draw',None
        return None,None

    def _new2(self):
        self.board2=[None]*9; self.current2='X'; self.winner2=None
        self.win_combo2=None; self.game_over2=False; self.hover_cell2=-1
        self.cell_anim2=[0.0]*9; self.win_anim2=0.0; self.result_anim2=0.0
        self.scores2={'X':0,'O':0,'draw':0}

    def _play_again2(self):
        """Play Again overlay — keeps scores."""
        self.board2=[None]*9; self.current2='X'; self.winner2=None
        self.win_combo2=None; self.game_over2=False; self.hover_cell2=-1
        self.cell_anim2=[0.0]*9; self.win_anim2=0.0; self.result_anim2=0.0

    def _click2(self,pos):
        if self.game_over2: return
        for i,r in enumerate(self.cell_rects):
            if r.collidepoint(pos) and self.board2[i] is None:
                self.board2[i]=self.current2
                w,combo=self._check2()
                if w:
                    self.winner2=w; self.win_combo2=combo; self.game_over2=True
                    self.scores2['draw' if w=='draw' else w]+=1
                else:
                    self.current2='O' if self.current2=='X' else 'X'
                break

    def _rand2(self):
        if self.game_over2: return
        empty=[i for i,v in enumerate(self.board2) if v is None]
        if empty: self._click2(self.cell_rects[random.choice(empty)].center)

    def _anim2(self,dt):
        for i in range(9):
            if self.board2[i] and self.cell_anim2[i]<1.0:
                self.cell_anim2[i]=min(1.0,self.cell_anim2[i]+dt*5)
        if self.game_over2:
            if self.win_combo2: self.win_anim2=min(1.0,self.win_anim2+dt*3)
            self.result_anim2=min(1.0,self.result_anim2+dt*2.5)

    # ── fullscreen ─────────────────────────────
    def toggle_fs(self):
        self.screen     = SM.toggle_fs()
        self.fullscreen = SM.fullscreen
        self.screen_w   = SM.win_w
        self.screen_h   = SM.win_h
        self._settings_open = False
        self._build_fonts(); self._build_layout()

    def _rotate_to_face(self, fi):
        """Kick off a smooth rotation to bring face fi front-and-centre."""
        # Normalize current yaw/pitch into [-π, π] so angle_lerp converges quickly
        self.cube.yaw   = (self.cube.yaw   + math.pi) % (2*math.pi) - math.pi
        self.cube.pitch = (self.cube.pitch + math.pi) % (2*math.pi) - math.pi
        self._rot_target_yaw, self._rot_target_pitch = self._FACE_TARGET[fi]
        print(f"[ROT] yaw={self.cube.yaw:.3f}→{self._rot_target_yaw:.3f}  "
              f"pitch={self.cube.pitch:.3f}→{self._rot_target_pitch:.3f}")

    def _on_face_win(self, face_index, winner):
        """Burst particles from the centre of the winning face on screen."""
        # Use the face's projected centre from the last drawn quads
        for q in self.cube._quads:
            if q['fi'] == face_index and q['visible']:
                pts = q['pts2']
                cx  = int(sum(p[0] for p in pts) / 4)
                cy  = int(sum(p[1] for p in pts) / 4)
                col = X_COLOR if winner == 'X' else O_COLOR
                self.particles.burst(cx, cy, col, count=35)
                return
        # Face not currently visible — burst from cube centre anyway
        col = X_COLOR if winner == 'X' else O_COLOR
        self.particles.burst(self.cube_cx, self.cube_cy, col, count=20)

    def _print_game_end(self, reason="Interrupted"):
        """Print [GAME END] debug line if an AI game was in progress."""
        if self.cube._game_start is None: return
        if not (self.cube.ai_mode or self.cube.ai_vs_ai): return
        import datetime
        elapsed  = time.time() - self.cube._game_start
        mode_str = "AI vs AI" if self.cube.ai_vs_ai else "vs AI"
        result   = f"Winner: {self.cube.winner}" if self.cube.winner else reason
        ts       = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[GAME END]  {mode_str} | {result} | "
              f"Duration: {elapsed:.1f}s | {ts}")
        print("-" * 60)

    def _new_game_3d(self):
        """New game button — resets scores too."""
        self._print_game_end(reason="User started new game")
        self.cube.reset_scores()
        self._rotating_to_pending = False
        self.cube.new_game()

    def _play_again_3d(self):
        """Play Again overlay — keeps scores."""
        self._rotating_to_pending = False
        self.cube.new_game()

    # ── draw helpers ───────────────────────────
    def _draw_header(self,surf):
        W=surf.get_width()
        t=self.font_title.render("TIC  TAC  TOE"+" (3D)"*(self.mode=='3D'),True,TEXT_MAIN)
        rx=W//2-t.get_width()//2; surf.blit(t,(rx,self.title_y))
        uw=t.get_width()+20; ux=W//2-uw//2; uy=self.title_y+t.get_height()+4
        pygame.draw.line(surf,ACCENT,(ux,uy),(ux+uw,uy),2)

    def _draw_scores(self,surf,scores,ai_mode=False,ai_vs_ai=False):
        r=self.score_rect; sw=r.width//3
        if ai_vs_ai:
            x_label = "AI X"
            o_label = "AI O"
        elif ai_mode:
            x_label = "You (X)"
            o_label = "AI (O)"
        else:
            x_label = "Player X"
            o_label = "Player O"
        for i,(lbl,val,bg,col) in enumerate([
            ('X',scores['X'],SCORE_X_BG,X_COLOR),
            ('·',scores['draw'],DRAW_BG,TEXT_DIM),
            ('O',scores['O'],SCORE_O_BG,O_COLOR)]):
            pr=pygame.Rect(r.x+i*sw+(2 if i else 0),r.y,sw-2,r.height)
            draw_rounded_rect(surf,bg,pr,10)
            name = x_label if lbl=='X' else (o_label if lbl=='O' else "Draws")
            ls=self.font_label.render(name,True,col)
            surf.blit(ls,(pr.centerx-ls.get_width()//2,pr.y+int(pr.height*0.15)))
            ns=self.font_score.render(str(val),True,col)
            surf.blit(ns,(pr.centerx-ns.get_width()//2,pr.centery-ns.get_height()//2+6))

    def _draw_status(self,surf,current,game_over,winner,ranim,ai_mode=False,ai_vs_ai=False):
        W=surf.get_width(); y=self.status_top
        if game_over and ranim>0.1:
            if winner=='draw':
                msg="It's a Draw!"
                col=TEXT_DIM
            elif ai_vs_ai:
                msg=f"AI {winner} Wins!"
                col=X_COLOR if winner=='X' else O_COLOR
            elif ai_mode:
                msg="You Win!" if winner=='X' else "AI Wins!"
                col=X_COLOR if winner=='X' else O_COLOR
            else:
                msg=f"Player {winner} Wins!"
                col=X_COLOR if winner=='X' else O_COLOR
            t=self.font_result.render(msg,True,col)
            surf.blit(t,(W//2-t.get_width()//2,y))
        else:
            if (ai_mode or ai_vs_ai) and self.cube.ai_pending:
                thinking = "AI is thinking..." if not ai_vs_ai else f"AI {current} is thinking..."
                t=self.font_turn.render(thinking,True,AI_THINKING_COL)
                surf.blit(t,(W//2-t.get_width()//2,y))
            else:
                mc=X_COLOR if current=='X' else O_COLOR
                if ai_vs_ai:
                    label = f"AI {current}'s Turn"
                elif ai_mode:
                    label = "Your Turn (X)" if current=='X' else "AI's Turn (O)"
                else:
                    label = f"Player {current}'s Turn"
                t=self.font_turn.render(label,True,mc)
                tx=W//2-t.get_width()//2; surf.blit(t,(tx,y))
                if int(time.time()*2)%2==0:
                    pygame.draw.circle(surf,mc,(tx-18,y+t.get_height()//2),5)

    def _draw_board2(self,surf):
        br=self.board_rect; cs=br.width//3; g=max(3,int(cs*0.04))
        for i,rect in enumerate(self.cell_rects):
            inner=rect.inflate(-g*2,-g*2)
            is_h=(i==self.hover_cell2 and not self.game_over2 and self.board2[i] is None)
            draw_rounded_rect(surf,GRID_HOVER if is_h else BG_PANEL,inner,12)
            if self.board2[i]:
                a=int(self.cell_anim2[i]*255)
                if self.board2[i]=='X': draw_X(surf,rect.centerx,rect.centery,cs*0.5,X_COLOR,a)
                else:                   draw_O(surf,rect.centerx,rect.centery,cs*0.5,O_COLOR,a)
        lw=max(2,int(cs*0.025))
        for c in range(1,3):
            x=br.x+c*cs
            pygame.draw.line(surf,GRID_COLOR,(x,br.y+g),(x,br.bottom-g),lw)
        for r in range(1,3):
            y=br.y+r*cs
            pygame.draw.line(surf,GRID_COLOR,(br.x+g,y),(br.right-g,y),lw)
        if self.win_combo2 and self.win_anim2>0:
            a,_,c=self.win_combo2
            p1=pygame.Vector2(self.cell_rects[a].center)
            p2=pygame.Vector2(self.cell_rects[c].center)
            end=p1+(p2-p1)*self.win_anim2
            lw2=max(4,int(cs*0.07))
            pygame.draw.line(surf,WIN_LINE_COL,
                (int(p1.x),int(p1.y)),(int(end.x),int(end.y)),lw2)

    def _draw_face_panel(self, surf):
        """Left-side panel: 6 coloured 2-D mini-boards showing live board state."""
        FACE_NAMES = ["Front","Back","Top","Bottom","Left","Right"]
        px, py, pw, ph = self.panel_x, self.panel_y, self.panel_w, self.panel_h
        mp = pygame.mouse.get_pos()

        gap       = max(4, int(ph * 0.012))
        lbl_h     = max(12, int(ph * 0.032))
        cell_h    = (ph - 6*lbl_h - 7*gap) // 6
        cell_w    = min(pw - 4, cell_h)
        ox        = px + (pw - cell_w) // 2

        self._panel_face_rects = []   # rebuild each frame

        for fi in range(6):
            fy = py + fi * (cell_h + lbl_h + gap) + gap
            base_col = FACE_COLORS[fi]
            fw = self.cube.face_winner[fi]

            board_rect = pygame.Rect(ox, fy + lbl_h, cell_w, cell_h)
            self._panel_face_rects.append(pygame.Rect(ox, fy, cell_w, lbl_h + cell_h))

            hovered = board_rect.collidepoint(mp)

            # ── face label ──────────────────────────
            lbl_col  = TEXT_MAIN if hovered else TEXT_DIM
            lbl_surf = self.font_hint.render(FACE_NAMES[fi], True, lbl_col)
            surf.blit(lbl_surf, (ox + (cell_w - lbl_surf.get_width())//2, fy))
            fy += lbl_h

            # ── coloured background ─────────────────
            bg = lerp_color(base_col, (10,10,20), 0.35 if fw else 0.0)
            draw_rounded_rect(surf, bg, board_rect, 4)

            # hover / selected highlight ring
            if hovered:
                pygame.draw.rect(surf, (255,255,255), board_rect, 2, border_radius=4)

            cs = cell_w // 3

            if fw and fw != 'draw':
                fcx = board_rect.centerx
                fcy = board_rect.centery
                mc  = X_COLOR if fw=='X' else O_COLOR
                stamp = cell_w * 0.36
                if fw=='X': draw_X_crisp(surf, fcx, fcy, stamp, (20,20,20))
                else:       draw_O_crisp(surf, fcx, fcy, stamp, (20,20,20))
                pygame.draw.rect(surf, mc, board_rect, 2, border_radius=4)
            elif fw == 'draw':
                pygame.draw.line(surf, TEXT_DIM,
                    (board_rect.left+4, board_rect.centery),
                    (board_rect.right-4, board_rect.centery), 2)
                pygame.draw.rect(surf, TEXT_DIM, board_rect, 1, border_radius=4)
            else:
                board = self.cube.boards[fi]
                for cell in range(9):
                    row, col = divmod(cell, 3)
                    cr = pygame.Rect(ox + col*cs, fy + row*cs, cs, cs)
                    inner = cr.inflate(-2,-2)
                    cell_bg = lerp_color(bg, (255,255,255), 0.12)
                    pygame.draw.rect(surf, cell_bg, inner)
                    if board[cell]:
                        msz  = cs * 0.36
                        ccx, ccy = cr.centerx, cr.centery
                        if board[cell]=='X': draw_X_crisp(surf, ccx, ccy, msz, (20,20,20))
                        else:               draw_O_crisp(surf, ccx, ccy, msz, (20,20,20))

                lw = max(1, cs // 14)
                for c in range(1,3):
                    x = ox + c*cs
                    pygame.draw.line(surf,(0,0,0),(x, fy),(x, fy+cell_h), lw)
                for r in range(1,3):
                    y2 = fy + r*cs
                    pygame.draw.line(surf,(0,0,0),(ox, y2),(ox+cell_w, y2), lw)

                pygame.draw.rect(surf,(0,0,0), board_rect, 1, border_radius=4)

    def _draw_end_overlay(self, surf, winner, ai_mode=False):
        """Semi-transparent modal shown when a game ends."""
        W, H = surf.get_size()

        # Dim the whole screen
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surf.blit(dim, (0, 0))

        # Box dimensions
        bw = min(340, int(W * 0.42))
        bh = min(200, int(H * 0.26))
        bx = W // 2 - bw // 2
        by = H // 2 - bh // 2

        # Box background + border
        box_col    = (28, 24, 48)
        if winner == 'draw':
            border_col = TEXT_DIM
            result_col = TEXT_DIM
        elif winner == 'X':
            border_col = X_COLOR
            result_col = X_COLOR
        else:
            border_col = O_COLOR
            result_col = O_COLOR

        draw_rounded_rect(surf, box_col, (bx, by, bw, bh), 18, 3, border_col)

        # Result text
        if winner == 'draw':
            msg = "It's a Draw!"
        elif ai_mode:
            msg = "You Win!" if winner == 'X' else "AI Wins!"
        else:
            msg = f"Player {winner} Wins!"

        t = self.font_result.render(msg, True, result_col)
        surf.blit(t, (W // 2 - t.get_width() // 2, by + int(bh * 0.18)))

        # Play Again button — centred in lower half of box
        btn_w = int(bw * 0.58)
        btn_h = int(bh * 0.30)
        btn_x = W // 2 - btn_w // 2
        btn_y = by + int(bh * 0.57)
        self._btn_again.reposition(btn_x, btn_y, btn_w, btn_h)
        self._btn_again.font = self.font_btn
        self._btn_again.draw(surf)

    def _draw_face_tally(self,surf):
        W=surf.get_width(); sq=22
        tw=6*sq+5*4; x0=W//2-tw//2; y0=self.status_top-sq-6
        for fi in range(6):
            col=FACE_COLORS[fi]
            r=pygame.Rect(x0+fi*(sq+4),y0,sq,sq)
            pygame.draw.rect(surf,col,r,border_radius=4)
            fw=self.cube.face_winner[fi]
            if fw and fw!='draw':
                mc=X_COLOR if fw=='X' else O_COLOR
                if fw=='X': draw_X(surf,r.centerx,r.centery,sq*0.38,mc,200,0.22)
                else:       draw_O(surf,r.centerx,r.centery,sq*0.38,mc,200,0.22)
            elif fw=='draw':
                pygame.draw.line(surf,TEXT_DIM,(r.left+4,r.centery),(r.right-4,r.centery),2)
            pygame.draw.rect(surf,(0,0,0),r,1,border_radius=4)
        lbl=self.font_hint.render("Face wins:",True,TEXT_DIM)
        surf.blit(lbl,(x0-lbl.get_width()-6, y0+(sq-lbl.get_height())//2))

    def _draw_hint(self,surf):
        W=surf.get_width()
        if self.mode=='3D':
            hint="Drag to rotate  |  Click cell to play  |  Space — random  |  R — new game  |  Esc — menu"
        else:
            hint="R — new game  |  Space — random move  |  F11 — fullscreen  |  Esc — menu"
        t=self.font_hint.render(hint,True,TEXT_DIM)
        surf.blit(t,(W//2-t.get_width()//2,self.hint_y))

    # ── main draw ──────────────────────────────
    def draw(self):
        surf=self.screen
        nw,nh=surf.get_size()
        if (nw,nh)!=(self.screen_w,self.screen_h):
            self.screen_w,self.screen_h=nw,nh
            self._build_fonts(); self._build_layout()
        W,H=nw,nh
        surf.fill(BG_DARK)
        for x in range(0,W,40): pygame.draw.line(surf,(22,25,38),(x,0),(x,H),1)
        for y in range(0,H,40): pygame.draw.line(surf,(22,25,38),(0,y),(W,y),1)
        self._draw_header(surf)
        go=self.game_over2 if self.mode=='2D' else self.cube.game_over
        if self.mode=='2D':
            self._draw_scores(surf,self.scores2)
            self._draw_board2(surf)
            self._draw_status(surf,self.current2,self.game_over2,
                              self.winner2,self.result_anim2)
        else:
            self._draw_scores(surf,self.cube.scores,self.cube.ai_mode,self.cube.ai_vs_ai)
            self.cube.draw_cube(surf,self.cube_cx,self.cube_cy,
                                self.cube_size,pygame.mouse.get_pos())
            self._draw_face_panel(surf)
            self._draw_face_tally(surf)
            self._draw_status(surf,self.cube.current,self.cube.game_over,
                              self.cube.winner,self.cube.result_anim,
                              self.cube.ai_mode,self.cube.ai_vs_ai)
        self._draw_buttons(surf,go)
        self._draw_hint(surf)
        if self.mode=='3D':
            self.particles.draw(surf)
        # End-of-game overlay (not shown in AI vs AI — it auto-restarts)
        if self.mode=='2D' and self.game_over2 and self.result_anim2>0.4:
            self._draw_end_overlay(surf, self.winner2)
        elif (self.mode=='3D' and self.cube.game_over and self.cube.result_anim>0.4
              and not self.cube.ai_vs_ai):
            self._draw_end_overlay(surf, self.cube.winner, self.cube.ai_mode)
        # hover update for overlay button
        self._btn_again.update(pygame.mouse.get_pos())
        pygame.display.flip()

    def _draw_buttons(self, surf, game_over):
        self._btn_new.draw(surf)
        rand_dim = (game_over or self.cube.ai_vs_ai
                    or (self.mode=='3D' and self.cube.ai_mode and self.cube.current=='O'))
        self._btn_rand.draw(surf, dimmed=rand_dim)

    # ── main loop ──────────────────────────────
    def run(self):
        lt=time.time()
        while True:
            now=time.time(); dt=now-lt; lt=now
            mp=pygame.mouse.get_pos()
            buttons = [self._btn_new, self._btn_rand]
            for b in buttons: b.update(mp)

            if self.mode=='2D':
                self.hover_cell2=-1
                if not self.game_over2:
                    for i,r in enumerate(self.cell_rects):
                        if r.collidepoint(mp): self.hover_cell2=i; break

            for event in pygame.event.get():
                if event.type==pygame.QUIT: return 'quit'

                if event.type==pygame.KEYDOWN:
                    if event.key in(pygame.K_F11,pygame.K_f): self.toggle_fs()
                    if event.key==pygame.K_r:
                        if self.mode=='2D': self._new2()
                        else:               self._new_game_3d()
                    if event.key==pygame.K_SPACE:
                        if self.mode=='2D': self._rand2()
                        else:               self.cube.random_move()
                    if event.key==pygame.K_ESCAPE:
                        return 'menu'

                if event.type==pygame.VIDEORESIZE and not SM.fullscreen:
                    self.screen = SM.on_resize(event.w, event.h)
                    self.screen_w, self.screen_h = SM.win_w, SM.win_h
                    self._build_fonts(); self._build_layout()

                if self.mode=='3D':
                    if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                        self._drag=True
                        self._drag_start=event.pos
                        self._drag_yaw0=self.cube.yaw
                        self._drag_pit0=self.cube.pitch
                        # Only cancel auto-rotate if not mid-pending-move rotation
                        if not self._rotating_to_pending:
                            self._rot_target_yaw = self._rot_target_pitch = None
                    if event.type==pygame.MOUSEMOTION and self._drag:
                        dx=event.pos[0]-self._drag_start[0]
                        dy=event.pos[1]-self._drag_start[1]
                        self.cube.yaw  =self._drag_yaw0+dx*0.008
                        self.cube.pitch=max(-1.4,min(1.4,self._drag_pit0-dy*0.008))
                    if event.type==pygame.MOUSEBUTTONUP and event.button==1:
                        if self._drag_start:
                            dx=event.pos[0]-self._drag_start[0]
                            dy=event.pos[1]-self._drag_start[1]
                            if dx*dx+dy*dy<64:
                                handled=False
                                # overlay Play Again takes priority
                                if self.cube.game_over and self._btn_again.rect.collidepoint(event.pos):
                                    self._play_again_3d(); handled=True
                                else:
                                    # check face panel clicks
                                    for fi, fr in enumerate(self._panel_face_rects):
                                        if fr.collidepoint(event.pos):
                                            self._rotate_to_face(fi)
                                            handled=True; break
                                if not handled:
                                    if self._btn_new.rect.collidepoint(event.pos):
                                        self._new_game_3d(); handled=True
                                    elif self._btn_rand.rect.collidepoint(event.pos):
                                        self.cube.random_move(); handled=True
                                if not handled:
                                    fi,ci=self.cube.hit_test(*event.pos)
                                    if fi>=0 and ci>=0: self.cube.play(fi,ci)
                        self._drag=False; self._drag_start=None

                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if self.game_over2 and self._btn_again.rect.collidepoint(event.pos):
                        self._play_again2()
                    elif self._btn_new.clicked(event):  self._new2()
                    elif self._btn_rand.clicked(event): self._rand2()
                    else: self._click2(event.pos)

            if self.mode=='2D': self._anim2(dt)
            else:
                self.cube.update(dt)
                self.particles.update(dt)

                # ── Smooth rotation toward target face (runs first) ──
                if self._rot_target_yaw is not None:
                    speed = min(1.0, dt * 8)
                    def angle_lerp(a, b, t):
                        diff = (b - a + math.pi) % (2*math.pi) - math.pi
                        return a + diff * t
                    def angle_diff(a, b):
                        """Shortest angular distance between a and b."""
                        return abs((b - a + math.pi) % (2*math.pi) - math.pi)
                    self.cube.yaw   = angle_lerp(self.cube.yaw,   self._rot_target_yaw,   speed)
                    self.cube.pitch = angle_lerp(self.cube.pitch, self._rot_target_pitch, speed)
                    if (angle_diff(self.cube.yaw,   self._rot_target_yaw)   < 0.005 and
                        angle_diff(self.cube.pitch, self._rot_target_pitch) < 0.005):
                        self.cube.yaw   = self._rot_target_yaw
                        self.cube.pitch = self._rot_target_pitch
                        self._rot_target_yaw = self._rot_target_pitch = None
                        if self._rotating_to_pending:
                            print(f"[ROT] Rotation finished → ready to fire pending move "
                                  f"face={self.cube.pending_face} cell={self.cube.pending_cell}")

                # ── Rotation-first: rotate to face, then fire move ──
                if self.cube.pending_face is not None:
                    if not self._rotating_to_pending:
                        # Phase 1 — kick off rotation
                        print(f"[ROT] Starting rotation to face {self.cube.pending_face} "
                              f"for move ({self.cube.pending_face},{self.cube.pending_cell})")
                        self._rotate_to_face(self.cube.pending_face)
                        self._rotating_to_pending = True
                        self._rotation_started_at = time.time()
                    elif self._rot_target_yaw is None:
                        # Phase 2 — rotation done, fire move
                        print(f"[MOVE] Firing move face={self.cube.pending_face} "
                              f"cell={self.cube.pending_cell} player={self.cube.current}")
                        self.cube._do_play(self.cube.pending_face, self.cube.pending_cell)
                        self.cube.pending_face    = None
                        self.cube.pending_cell    = None
                        self._rotating_to_pending = False

                # ── Timeout watchdog: if stuck > 3s, force-fire the move ──
                if self.cube.pending_face is not None and self._rotating_to_pending:
                    if time.time() - self._rotation_started_at > 3.0:
                        print(f"[WATCHDOG] Rotation timed out! Force-firing move "
                              f"face={self.cube.pending_face} cell={self.cube.pending_cell}")
                        self._rot_target_yaw = self._rot_target_pitch = None
                        self.cube._do_play(self.cube.pending_face, self.cube.pending_cell)
                        self.cube.pending_face    = None
                        self.cube.pending_cell    = None
                        self._rotating_to_pending = False
                        self._rotation_started_at = None
                else:
                    self._rotation_started_at = None

                # ── Auto-restart for AI vs AI ──
                if self.cube.ai_vs_ai and self.cube.game_over:
                    if self._auto_restart_at is None:
                        self._auto_restart_at = time.time() + 2.0
                    elif time.time() >= self._auto_restart_at:
                        self._auto_restart_at = None
                        self._rotating_to_pending = False
                        self._rot_target_yaw = self._rot_target_pitch = None
                        self.cube.new_game()
            self.draw()
            self.clock.tick(FPS)
