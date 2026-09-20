"""Ten deterministic, replayable temple games. No GUI dependencies."""
import random

INFO = {
 'memory': ('🃏 Runenpaare', 'Finde 8 Paare in höchstens 16 Paarversuchen', 55, 20),
 'mines': ('💎 Schatzsucher', 'Decke alle sicheren Felder auf · 5 Fallen', 70, 25),
 'lights': ('💡 Sternenlichter', 'Lösche alle Lichter in höchstens 30 Zügen', 60, 20),
 'slide': ('🔢 Tempelpuzzle', 'Ordne die Zahlen 1–8 in höchstens 100 Zügen', 65, 25),
 'maze': ('🧭 Wüstenlabyrinth', 'Erreiche das goldene Tor', 45, 15),
 'sokoban': ('📦 Siegeltransport', 'Schiebe die zwei Kisten auf die goldenen Ziele', 70, 25),
 'four': ('🔴 Vier gewinnt', 'Vier eigene Steine verbinden · gegen den Wächter', 75, 25),
 'three': ('⭕ Runenduell', 'Drei eigene Runen verbinden · gegen den Wächter', 40, 15),
 'reflex': ('⚡ Sternenfang', 'Triff 15 Sterne vor Ablauf ihrer Zeit', 60, 20),
 'wheel': ('🎡 Glücksrad', 'Drehe das Rad · Goldstern gewinnt', 35, 15),
}

class TempleGame:
    endless=False
    target=1
    def __init__(self, kind, seed):
        self.kind=kind; self.rng=random.Random(seed); self.score=0; self.over=False; self.moves=[]
        self.note=''; self.selected=[]; self.matched=set(); self.attempts=0; self.steps=0
        self.w=self.h=4; self.cells=['']*16; self.player=0; self.goals=set(); self.boxes=set(); self.walls=set()
        if kind=='memory':
            self.cells=list('ABCDEFGH')*2; self.rng.shuffle(self.cells)
        elif kind=='mines':
            self.w=self.h=5; self.cells=['']*25; self.mines=set(); self.opened=set()
        elif kind=='lights':
            self.cells=[0]*16
            for _ in range(12):self.flip(self.rng.randrange(16))
            if not any(self.cells):self.flip(0)
        elif kind=='slide':
            self.w=self.h=3; self.cells=list(range(1,9))+[0]
            for _ in range(80):
                z=self.cells.index(0); n=self.rng.choice(self.neighbors(z));self.cells[z],self.cells[n]=self.cells[n],self.cells[z]
            if self.cells==list(range(1,9))+[0]:self.cells[8],self.cells[7]=self.cells[7],self.cells[8]
        elif kind=='maze':
            self.w=self.h=9; self.cells=['']*81; self.walls=set(range(81));self.walls.remove(10)
            stack=[10]
            while stack:
                a=stack[-1];x,y=a%9,a//9
                options=[(y+dy)*9+x+dx for dx,dy in ((2,0),(-2,0),(0,2),(0,-2)) if 0<x+dx<8 and 0<y+dy<8 and (y+dy)*9+x+dx in self.walls]
                if options:
                    b=self.rng.choice(options);self.walls.remove(b);self.walls.remove((a+b)//2);stack.append(b)
                else:stack.pop()
            self.player=10;self.goals={70}
        elif kind=='sokoban':
            self.w=self.h=6;self.cells=['']*36;self.walls={i for i in range(36) if i%6 in (0,5) or i//6 in (0,5)}
            self.player=25;self.boxes={14,15};self.goals={8,9}
            if self.rng.randrange(2):
                self.player=28;self.boxes={20,21};self.goals={8,9}
        elif kind in ('four','three'):
            self.w,self.h=(7,6) if kind=='four' else (3,3);self.cells=['']*(self.w*self.h)
        elif kind=='reflex':self.star=self.rng.randrange(16);self.hits=0;self.ticks=0;self.misses=0
        elif kind=='wheel':self.w=self.h=3;self.cells=['★','·','★','·','★','·','★','·','·'];self.cursor=0;self.spinning=False;self.remaining=0
        self.actions={str(i) for i in range(len(self.cells))}|{'U','D','L','R','.'}

    def neighbors(self,i):
        x,y=i%self.w,i//self.w
        return [(y+dy)*self.w+x+dx for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)) if 0<=x+dx<self.w and 0<=y+dy<self.h]
    def flip(self,i):
        for n in [i]+self.neighbors(i):self.cells[n]=1-self.cells[n]
    def finish(self,won):self.over=True;self.score=int(won);self.note='Gewonnen!' if won else 'Dieser Versuch ist beendet.'
    def line(self,who):
        n=4 if self.kind=='four' else 3
        for i,c in enumerate(self.cells):
            if c!=who:continue
            x,y=i%self.w,i//self.w
            for dx,dy in ((1,0),(0,1),(1,1),(-1,1)):
                if all(0<=x+dx*k<self.w and 0<=y+dy*k<self.h and self.cells[(y+dy*k)*self.w+x+dx*k]==who for k in range(n)):return True
        return False
    def legal(self):return [x for x in range(self.w) if not self.cells[x]] if self.kind=='four' else [i for i,c in enumerate(self.cells) if not c]
    def put(self,a,who):
        i=next(y*self.w+a for y in reversed(range(self.h)) if not self.cells[y*self.w+a]) if self.kind=='four' else a
        self.cells[i]=who;return i
    def step(self,action):
        if self.over:return
        self.moves.append(action);self.steps+=1
        if not self.endless and self.steps>=10000:self.finish(False);return
        k=self.kind
        if k=='wheel':
            if not self.spinning and action!='.':self.spinning=True;self.remaining=self.rng.randint(30,65)
            elif self.spinning and action=='.':
                self.cursor=(self.cursor+1)%9;self.remaining-=1
                if not self.remaining:self.finish(self.cells[self.cursor]=='★')
            return
        if k=='reflex':
            if action=='.':
                self.ticks+=1
                if self.ticks>=10:self.misses+=1;self.ticks=0;self.star=self.rng.randrange(16)
            elif action.isdigit():
                if int(action)==self.star:self.hits+=1;self.star=(self.star+self.rng.randrange(1,16))%16;self.ticks=0
                else:self.misses+=1
            self.note=f'Sterne {self.hits}'+(' · Endlos' if self.endless else '/15')+f' · Fehler {self.misses}/4'
            if self.hits>=15 and not self.endless:self.finish(True)
            elif self.misses>=4:self.finish(False)
            return
        if k in ('maze','sokoban'):
            delta={'L':-1,'R':1,'U':-self.w,'D':self.w}.get(action,0);n=self.player+delta
            if delta and n in self.neighbors(self.player) and n not in self.walls:
                if n in self.boxes:
                    b=n+delta
                    if b not in self.neighbors(n) or b in self.walls or b in self.boxes:return
                    self.boxes.remove(n);self.boxes.add(b)
                self.player=n
            if (k=='maze' and self.player in self.goals) or (k=='sokoban' and self.boxes==self.goals):self.finish(True)
            return
        if not action.isdigit():return
        i=int(action)
        if not 0<=i<len(self.cells):return
        if k=='memory':
            if len(self.selected)==2:self.selected=[]
            if i in self.matched or i in self.selected:return
            self.selected.append(i)
            if len(self.selected)==2:
                self.attempts+=1;a,b=self.selected
                if self.cells[a]==self.cells[b]:self.matched.update((a,b))
                self.note=f'Paare {len(self.matched)//2}/8 · Versuche {self.attempts}/16'
                if len(self.matched)==16:self.finish(True)
                elif self.attempts>=16:self.finish(False)
        elif k=='mines':
            if not self.mines:self.mines=set(self.rng.sample([n for n in range(25) if n!=i],5))
            self.opened.add(i)
            if i in self.mines:self.finish(False)
            elif len(self.opened)==20:self.finish(True)
        elif k=='lights':
            self.flip(i);self.attempts+=1;self.note=f'Züge {self.attempts}/30'
            if not any(self.cells):self.finish(True)
            elif self.attempts>=30:self.finish(False)
        elif k=='slide':
            z=self.cells.index(0)
            if i in self.neighbors(z):self.cells[z],self.cells[i]=self.cells[i],self.cells[z];self.attempts+=1
            self.note=f'Züge {self.attempts}/100'
            if self.cells==list(range(1,9))+[0]:self.finish(True)
            elif self.attempts>=100:self.finish(False)
        elif k in ('four','three'):
            a=i%self.w if k=='four' else i
            if a not in self.legal():return
            self.put(a,'●')
            if self.line('●'):self.finish(True);return
            legal=self.legal()
            if not legal:self.finish(False);return
            pick=None
            for who in ('◆','●'):
                for candidate in legal:
                    pos=self.put(candidate,who);wins=self.line(who);self.cells[pos]=''
                    if wins:pick=candidate;break
                if pick is not None:break
            self.put(self.rng.choice(legal) if pick is None else pick,'◆')
            if self.line('◆') or not self.legal():self.finish(False)
    def tile(self,i):
        k=self.kind
        if k=='memory':return self.cells[i] if i in self.selected or i in self.matched or self.over else '?'
        if k=='mines':
            if self.over and i in self.mines:return '✹'
            if i not in self.opened:return '?'
            x,y=i%5,i//5
            return str(sum(abs(n%5-x)<=1 and abs(n//5-y)<=1 for n in self.mines))
        if k=='lights':return '☀' if self.cells[i] else '·'
        if k=='slide':return str(self.cells[i]) if self.cells[i] else ''
        if k in ('maze','sokoban'):
            return '●' if i==self.player else '▣' if i in self.boxes else '■' if i in self.walls else '★' if i in self.goals else ''
        if k=='reflex':return '★' if i==self.star else '·'
        return self.cells[i]
