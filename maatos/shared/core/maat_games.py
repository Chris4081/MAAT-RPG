"""Seeded MAAT puzzles with authoritative action replay."""
import random

INFO={
 'maat_echo':('🔔 Echo der Prinzipien','Merke fünf Folgen mit 3 bis 7 Runen',75,25),
 'maat_balance':('⚖ Waage der Wahrheit','Gleiche drei Waagen mit passenden Gewichten aus',65,25),
 'maat_creation':('🎨 Schöpfungsmosaik','Erzeuge das Zielmuster in höchstens 45 Klicks',60,20),
 'maat_connection':('✦ Pfad der Verbundenheit','Verbinde H → B → S → V → R ohne Rückweg',65,25),
 'maat_respect':('🛡 Hüter des Respekts','Wähle zwölfmal die erlaubte Rune · maximal 2 Fehler',55,20),
 'maat_numbers':('📐 Resonanzrechnen','Löse zwölf Resonanzrechnungen · maximal 2 Fehler',70,25),
 'maat_towers':('🏛 Türme von Terra','Versetze vier Scheiben nach rechts · höchstens 30 Züge',80,30),
 'maat_rings':('☀ Fünf Sonnenringe','Stimme alle fünf Ringe auf 0 · höchstens 35 Klicks',70,25),
}
HINTS={
 'maat_echo':'Die Folge erscheint kurz oben. Danach die Runen in derselben Reihenfolge anklicken.',
 'maat_balance':'Gewichte anklicken zum Wählen/Abwählen, dann ✓. Jedes Gewicht darf einmal auf die Waage.',
 'maat_creation':'Jeder Klick wechselt · → H → B → ·. Die obere Rune jeder Kachel ist das Ziel, die untere dein Muster.',
 'maat_connection':'Beginne bei H. Klicke danach nur benachbarte Felder. Besuche B, S, V, R in dieser Reihenfolge; kein Feld zweimal.',
 'maat_respect':'Lies die Regel oben und wähle genau die passende Rune. Drei Fehler beenden den Versuch.',
 'maat_numbers':'Wähle das Ergebnis. Drei falsche Antworten beenden den Versuch.',
 'maat_towers':'Quellturm, dann Zielturm anklicken. Nur kleinere Scheiben dürfen auf größere. Ziel: alle Scheiben rechts.',
 'maat_rings':'Ein Klick erhöht diesen Ring und seinen rechten Nachbarn um 1 (nach 2 kommt 0). Alle Ringe müssen 0 zeigen.',
}

class MaatGame:
    endless=False
    target=1
    def __init__(self,kind,seed):
        self.kind=kind;self.rng=random.Random(seed);self.score=0;self.over=False;self.moves=[];self.steps=0
        self.note='';self.round=0;self.errors=0;self.selected=set();self.w=5;self.cells=list('HBSVR');self.ticks=0
        if kind=='maat_echo':self.next_echo()
        elif kind=='maat_balance':self.next_balance()
        elif kind=='maat_creation':
            self.w=3;self.cells=[0]*9;self.goal=[self.rng.randrange(3) for _ in range(9)];self.goal[0]=1;self.describe_mosaic()
        elif kind=='maat_connection':
            self.w=5;self.cells=['·']*25;self.path=[]
            # Mirrored routes vary by seed and always admit a non-crossing solution.
            self.checkpoints=[0,4,14,10,20]
            if self.rng.randrange(2):self.checkpoints=[i//5*5+4-i%5 for i in self.checkpoints]
            for i,c in zip(self.checkpoints,'HBSVR'):self.cells[i]=c
            self.note='Beginne bei H · Danach B → S → V → R';self.progress=0
        elif kind=='maat_respect':self.next_respect()
        elif kind=='maat_numbers':self.next_numbers()
        elif kind=='maat_towers':self.w=3;self.cells=['']*3;self.towers=[[4,3,2,1],[],[]];self.source=None;self.note='Alle vier Scheiben auf Turm 3 bewegen.'
        elif kind=='maat_rings':
            self.cells=[0]*5
            for _ in range(9):self.turn_ring(self.rng.randrange(5))
            if not any(self.cells):self.turn_ring(0)
            self.note='Alle Ringe auf 0 stimmen · 35 Klicks'
        self.actions={str(i) for i in range(len(self.cells))}|({'.'} if kind=='maat_echo' else set())
    def finish(self,won):
        self.over=True;self.score=int(won);self.note='Gewonnen! Die Prinzipien schwingen im Einklang.' if won else 'Versuch beendet · Die Resonanz ist abgerissen.'
    def next_echo(self):
        self.sequence=[self.rng.randrange(5) for _ in range(3+self.round)];self.position=0;self.ticks=35+10*len(self.sequence)
        self.note='Merke: '+' → '.join('HBSVR'[i] for i in self.sequence)
    def next_balance(self):
        self.weights=self.rng.sample(range(2,16),5);self.goal=sum(self.weights[i] for i in self.rng.sample(range(5),3));self.cells=self.weights+['✓'];self.selected=set();self.balance_note()
    def balance_note(self):self.note=f'Waage {self.round+1}/3 · Ziel {self.goal} · Gewählt {sum(self.weights[i] for i in self.selected)}'
    def describe_mosaic(self):self.note=f'Ziel / dein Muster · {self.steps}/45 Klicks'
    def next_respect(self):
        self.answer=self.rng.randrange(5);self.cells=list('HBSVR')
        self.note=f'Runde {self.round+1}/12 · Wähle '+['Harmonie','Balance','Schöpfungskraft','Verbundenheit','Respekt'][self.answer]+f' · Fehler {self.errors}/3'
        self.rng.shuffle(self.cells)
    def next_numbers(self):
        a=self.rng.randrange(2,16);b=self.rng.randrange(2,10);op=self.rng.choice(['+','−','×']);self.answer=a+b if op=='+' else a-b if op=='−' else a*b
        self.cells=[self.answer]+self.rng.sample([i for i in range(self.answer-9,self.answer+10) if i!=self.answer],4);self.rng.shuffle(self.cells)
        self.note=f'Resonanz {self.round+1}/12 · {a} {op} {b} = ? · Fehler {self.errors}/3'
    def turn_ring(self,i):
        for j in (i,(i+1)%5):self.cells[j]=(self.cells[j]+1)%3
    def tile(self,i):
        k=self.kind
        if k=='maat_balance':return '✓ Prüfen' if i==5 else ('● ' if i in self.selected else '')+str(self.weights[i])
        if k=='maat_creation':return '·HB'[self.goal[i]]+' / '+'·HB'[self.cells[i]]
        if k=='maat_connection':return ('●' if self.path and i==self.path[-1] else '○') if i in self.path else self.cells[i]
        if k=='maat_towers':return f'Turm {i+1}'+(' ◀' if self.source==i else '')+'\n'+'\n'.join('━'*n for n in reversed(self.towers[i]))
        if k=='maat_rings':return 'HBSVR'[i]+'\n'+str(self.cells[i])
        return str(self.cells[i])
    def step(self,action):
        if self.over or action not in self.actions:return
        self.moves.append(action)
        if len(self.moves)>10000:self.finish(False);return
        k=self.kind
        if k=='maat_echo' and self.ticks:
            if action=='.':
                self.ticks-=1
                if not self.ticks:self.note='Jetzt nachspielen · '+'○'*len(self.sequence)
            return
        if action=='.':return
        i=int(action);self.steps+=1
        if k=='maat_echo':
            if i!=self.sequence[self.position]:self.finish(False);return
            self.position+=1;self.note='Nachspielen · '+'●'*self.position+'○'*(len(self.sequence)-self.position)
            if self.position==len(self.sequence):
                self.round+=1
                if self.round==5:self.finish(True)
                else:self.next_echo()
        elif k=='maat_balance':
            if i==5:
                if sum(self.weights[n] for n in self.selected)!=self.goal:self.errors+=1
                else:self.round+=1
                if self.round==3:self.finish(True)
                elif self.errors>=3:self.finish(False)
                else:self.next_balance();self.note+=f' · Fehler {self.errors}/3'
            else:
                if i in self.selected:self.selected.remove(i)
                else:self.selected.add(i)
                self.balance_note()
        elif k=='maat_creation':
            self.cells[i]=(self.cells[i]+1)%3;self.describe_mosaic()
            if self.cells==self.goal:self.finish(True)
            elif self.steps>=45:self.finish(False)
        elif k=='maat_connection':
            if not self.path:
                if i!=self.checkpoints[0]:return
            elif i in self.path or abs(i%5-self.path[-1]%5)+abs(i//5-self.path[-1]//5)!=1:return
            if i in self.checkpoints:
                if self.checkpoints.index(i)!=self.progress:self.finish(False);return
                self.progress+=1
            self.path.append(i)
            if self.progress==5:self.finish(True)
            elif not any(n not in self.path and abs(n%5-i%5)+abs(n//5-i//5)==1 for n in range(25)):self.finish(False)
            else:self.note='Nächste Rune: '+'HBSVR'[self.progress]
        elif k in ('maat_respect','maat_numbers'):
            correct=self.cells[i]==('HBSVR'[self.answer] if k=='maat_respect' else self.answer)
            if correct:self.round+=1
            else:self.errors+=1
            if self.errors>=3:self.finish(False)
            elif self.round==12:self.finish(True)
            elif k=='maat_respect':self.next_respect()
            else:self.next_numbers()
        elif k=='maat_towers':
            if self.source is None:
                if self.towers[i]:self.source=i
                self.steps-=1
            else:
                src=self.source;self.source=None
                if src==i or (self.towers[i] and self.towers[i][-1]<self.towers[src][-1]):self.steps-=1;return
                self.towers[i].append(self.towers[src].pop());self.note=f'{self.steps}/30 Züge'
                if len(self.towers[2])==4:self.finish(True)
                elif self.steps>=30:self.finish(False)
        elif k=='maat_rings':
            self.turn_ring(i);self.note=f'{self.steps}/35 Klicks · Alle Ringe auf 0'
            if not any(self.cells):self.finish(True)
            elif self.steps>=35:self.finish(False)
