"""Deterministic fixed-step arcade engines, shared by UI and reward validation."""
import random

class Breakout:
    endless=False
    target=40
    actions={'L','R','.'}
    def __init__(self,seed):
        self.rng=random.Random(seed);self.paddle=240.;self.lives=3
        self.bricks={(x,y) for y in range(5) for x in range(8)}
        self.score=0;self.wave=1;self.over=False;self.moves=[];self.reset_ball()
    def reset_ball(self):
        self.x=self.paddle;self.y=390.;self.vx=self.rng.choice([-2.5,2.5]);self.vy=-3.5
    def step(self,action):
        if self.over:return
        self.moves.append(action)
        self.paddle=max(40,min(440,self.paddle+({'L':-7,'R':7,'.':0}[action])))
        # Two substeps prevent tunnelling through thin bricks/paddle.
        for _ in range(2):
            old_y=self.y;self.x+=self.vx/2;self.y+=self.vy/2
            if self.x<6 or self.x>474:self.x=max(6,min(474,self.x));self.vx=-self.vx
            if self.y<6:self.y=6;self.vy=abs(self.vy)
            if self.vy>0 and old_y<=434<=self.y and abs(self.x-self.paddle)<=46:
                self.y=433;self.vy=-min(6,abs(self.vy)+.08);self.vx=(self.x-self.paddle)/12
            hit=next(((x,y) for x,y in sorted(self.bricks) if 12+x*58-6<=self.x<=64+x*58+6 and 45+y*24-6<=self.y<=63+y*24+6),None)
            if hit:
                self.bricks.remove(hit);self.score+=1;self.vy=-self.vy
                if not self.bricks:
                    if self.endless:
                        self.wave+=1;self.bricks={(x,y) for y in range(5) for x in range(8)};self.reset_ball()
                    else:self.over=True
                    break
            if self.y>480:
                self.lives-=1
                if not self.lives:self.over=True
                else:self.reset_ball()
                break
        if not self.endless and len(self.moves)>=40000:self.over=True
