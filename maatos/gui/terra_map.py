"""A small, live Terra board plus an embedded large view; no extra window."""
import math
import random
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QTimer, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
from gui.hero_portrait import PortraitRenderer
from gui.ui_i18n import LocalizedUI
from shared.core.terra_journey import snapshot, localized_snapshot
from shared.core.gameplay_i18n import tr
from shared.core.monster_catalog import enemy_display_name

PALETTES = (
    ('#283b50','#5f645d','#e2c780'),
    ('#123d46','#346957','#9bd1a7'),
    ('#173b5c','#386481','#a9dcf2'),
    ('#282a51','#595173','#c5b7eb'),
    ('#334255','#68715c','#f6dda0'),
)


class BossMarker(QPushButton):
    def __init__(self, target, parent):
        super().__init__(parent)
        from gui.battle_arena import ART, artwork_for
        self.target=target
        self.setObjectName('terraBoss');self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(target['label']+' · '+target['name'])
        self.setToolTip(target['name'])
        self.setStyleSheet('QPushButton#terraBoss {background:#102239;border:1px solid #aa9864;border-radius:10px;} '
            'QPushButton#terraBoss:hover, QPushButton#terraBoss:focus {background:#243d55;border:2px solid #f2d78e;} '
            'QPushButton#terraBoss:checked {background:#344642;border:2px solid #f2d78e;} '
            'QPushButton#terraBoss:disabled {border-color:#52616e;}')
        layout=QVBoxLayout(self);layout.setContentsMargins(5,5,5,5);layout.setSpacing(2)
        art=QSvgWidget(str(ART/(artwork_for(target['name'])+'.svg')))
        art.setFixedSize(56,56);art.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(art,0,Qt.AlignCenter)
        self.name_label=name=QLabel(target['label']+' · '+target['name'].split(' #')[0].split(' (Final')[0])
        name.setWordWrap(True);name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet('background:transparent;color:#ecdba8;font-size:12px;')
        name.setAttribute(Qt.WA_TransparentForMouseEvents);layout.addWidget(name,1)

    def set_language(self, language):
        name=enemy_display_name(self.target['name'],language)
        label=self.target['label'].replace('Finale ', 'Final ') if language=='en' else self.target['label']
        self.name_label.setText(label+' · '+name.split(' #')[0].split(' (Final')[0])
        self.setToolTip(name)
        self.setAccessibleName(label+' · '+name)


class TerraBoard(QWidget):
    activated = Signal()
    boss_selected = Signal(str)
    credits_requested = Signal()

    def __init__(self, compact=False):
        super().__init__()
        self.compact=compact
        self.setMinimumHeight(208 if compact else 330)
        self.setCursor(Qt.PointingHandCursor if compact else Qt.ArrowCursor)
        self.setFocusPolicy(Qt.StrongFocus if compact else Qt.NoFocus)
        self.data=snapshot({})
        self.hero=PortraitRenderer()
        self.position=self.target=0.
        self.origin=0.
        self.duration=0
        self.walk_clock=QElapsedTimer()
        self.markers=[]
        self._marker_ids=()
        self.replay_ready=False
        self.end_button=QPushButton('✦ Ende der Welt\nAbspann ansehen',self)
        self.end_button.setCursor(Qt.PointingHandCursor)
        self.end_button.setStyleSheet('QPushButton {background:#383d38;color:#ffe3a2;border:1px solid #e6c677;'
            'border-radius:12px;font-size:13px;padding:5px;} QPushButton:hover, QPushButton:focus '
            '{background:#525044;border:2px solid #ffe8a5;} QPushButton:disabled {color:#899195;border-color:#52616e;}')
        self.end_button.setAccessibleName('Ende der Welt · Abspann ansehen')
        self.end_button.clicked.connect(self.credits_requested.emit)
        self.end_button.hide()
        self.idle_clock=QElapsedTimer();self.idle_clock.start()
        self.timer=QTimer(self);self.timer.setInterval(33);self.timer.timeout.connect(self.advance)

    def set_class(self, value):
        self.hero.set_class(value);self.update()

    def update_data(self, data):
        data=data or snapshot({})
        target=float(data.get('position',0))
        changed=data.get('id')!=self.data.get('id')
        self.data=data
        targets=data.get('map_targets',[]) if not self.compact else []
        ids=tuple(row['id'] for row in targets)
        if ids!=self._marker_ids:
            for marker in self.markers:marker.hide();marker.deleteLater()
            self.markers=[];self._marker_ids=ids
            for row in targets:
                marker=BossMarker(row,self)
                marker.clicked.connect(lambda checked=False,key=row['id']:self.boss_selected.emit(key))
                marker.show();self.markers.append(marker)
        for marker in self.markers:
            marker.set_language(getattr(self,'language','de'))
            marker.setChecked(marker.target['id']==data.get('selected_target'))
        self.end_button.setVisible(bool(targets) and data.get('kind')=='complete' and data.get('region')==4)
        self.setMinimumHeight(208 if self.compact else 420 if targets else 330)
        self.set_replay_ready(self.replay_ready)
        self.place_markers()
        if changed or not self.isVisible():
            self.position=self.target=target
            self.walk_clock.invalidate()
        elif target!=self.target:
            self.origin=self.position;self.target=target
            self.duration=min(1900,max(420,int(abs(target-self.origin)*240)))
            self.walk_clock.start()
        language=getattr(self,'language','de')
        shown=localized_snapshot(data,language)
        self.end_button.setText(tr('✦ Ende der Welt\nAbspann ansehen',language))
        self.end_button.setAccessibleName(tr('Ende der Welt · Abspann ansehen',language))
        self.setAccessibleName(f"Terra · {shown['title']} · "+tr('{progress} · Ziel: {goal}',language,progress=shown['progress'],goal=shown['goal']))
        self.setToolTip(self.accessibleName()+(tr(' · Karte vergrößern',language) if self.compact else ''))
        self.update()

    def advance(self):
        if self.walk_clock.isValid():
            t=min(1.,self.walk_clock.elapsed()/max(1,self.duration))
            # Ease at the endpoints, traversing every intermediate field.
            self.position=self.origin+(self.target-self.origin)*(t*t*(3-2*t))
            if t>=1:self.walk_clock.invalidate()
        self.update()

    def showEvent(self,event):
        self.timer.start();super().showEvent(event)

    def hideEvent(self,event):
        self.timer.stop();self.walk_clock.invalidate();self.position=self.target
        super().hideEvent(event)

    def mouseReleaseEvent(self,event):
        if self.compact and event.button()==Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        if self.compact and event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space) and not event.isAutoRepeat():
            self.activated.emit();event.accept();return
        super().keyPressEvent(event)

    def points(self):
        if self.markers:
            return [QPointF(self.width()*x,self.height()*y) for x,y in
                    ((.18,.73),(.5,.73),(.82,.73),(.82,.27),(.5,.27),(.18,.27))]
        count=int(self.data['steps'])+1
        route=int(self.data.get('route',0))
        cols=6 if count>15 else (4,3,4,3,4)[route%5]
        rows=math.ceil(count/cols)
        # Keep the trail on land and reserve headroom for the moving portrait.
        left,right=self.width()*.16,self.width()*.84
        top,bottom=(52. if self.compact else 90.),self.height()-35.
        points=[]
        # Balance the last row too, instead of leaving a single field at an edge.
        for row in range(rows):
            row_count=count//rows+(row<count%rows)
            inset=(.04*math.sin(route+row*1.7))*self.width()
            for col in range(row_count):
                x=left+(right-left)*col/max(1,row_count-1)+inset
                if (row+route)%2:x=self.width()-x
                y=bottom-(bottom-top)*row/max(1,rows-1)
                points.append(QPointF(x,y))
        return points

    def set_replay_ready(self, ready):
        self.replay_ready=ready
        for marker in self.markers:marker.setEnabled(ready)
        self.end_button.setEnabled(ready)

    def place_markers(self):
        width=min(158,max(120,int(self.width()*.27)))
        for marker,point in zip(self.markers,self.points()):
            marker.setGeometry(round(point.x()-width/2),round(point.y()-61),width,122)
        end_width=min(208,max(160,int(self.width()*.36)))
        self.end_button.setGeometry(round((self.width()-end_width)/2),round(self.height()*.5-26),end_width,52)

    def resizeEvent(self,event):
        self.place_markers();super().resizeEvent(event)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height()
        region=min(4,max(0,int(self.data.get('region',0))))
        land,edge,accent=PALETTES[region]
        background=QLinearGradient(0,0,w,h)
        background.setColorAt(0,QColor('#102943'));background.setColorAt(1,QColor('#060f24'))
        p.setBrush(background);p.setPen(QPen(QColor('#334d6d'),1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),12,12)
        p.save()
        clip=QPainterPath();clip.addRoundedRect(QRectF(self.rect()).adjusted(3,3,-3,-3),10,10)
        p.setClipPath(clip)
        seed=int(self.data.get('route',0))*127+region*23
        rng=random.Random(seed)
        # Each route has its own coastline; the five regions keep their terrain.
        bend=(rng.random()-.5)*.07
        coast=QPainterPath();coast.moveTo(w*.06,h*.9)
        coast.cubicTo(-w*.07,h*.45,w*(.12+bend),h*.58,w*.08,h*.17)
        coast.cubicTo(w*.33,-h*.06,w*.52,h*(.16+bend),w*.65,h*.06)
        coast.cubicTo(w*1.04,h*.07,w*(1.04-bend),h*.48,w*.94,h*.72)
        coast.cubicTo(w*.99,h*1.01,w*.64,h*(.96+bend),w*.5,h*.98)
        coast.cubicTo(w*.29,h*.83,w*.18,h*1.03,w*.06,h*.9)
        p.setPen(QPen(QColor(edge),1.2));p.setBrush(QColor(land));p.drawPath(coast)
        p.setPen(QPen(QColor(100,152,185,35),1))
        for line in range(5):
            y=h*(.12+line*.2)
            p.drawArc(QRectF(w*.6,y,w*.5,h*.08),15*16,140*16)
        for i in range(16):
            x,y=w*(.08+rng.random()*.84),h*(.12+rng.random()*.75)
            scale=(5 if self.compact else 10)*(0.7+rng.random()*.6)
            if region==1:
                p.setPen(Qt.NoPen);p.setBrush(QColor('#35785f'))
                p.drawEllipse(QPointF(x,y-scale),scale,scale*1.3)
                p.setPen(QPen(QColor('#7c9270'),1));p.drawLine(QPointF(x,y),QPointF(x,y+scale))
            elif region==2:
                shape=QPainterPath();shape.moveTo(x,y-scale*1.5);shape.lineTo(x+scale*.6,y)
                shape.lineTo(x,y+scale*.5);shape.lineTo(x-scale*.6,y);shape.closeSubpath()
                p.setPen(QPen(QColor('#6aafd0'),1));p.setBrush(QColor('#366987'));p.drawPath(shape)
            else:
                shape=QPainterPath();shape.moveTo(x-scale,y+scale*.4);shape.lineTo(x,y-scale)
                shape.lineTo(x+scale,y+scale*.4);shape.closeSubpath()
                p.setPen(QPen(QColor(edge),1));p.setBrush(QColor('#435169' if region==3 else '#6b6b59'))
                p.drawPath(shape)
        # A ruin/temple keeps the route anchored in Terra, not an abstract chart.
        x,y=w*.77,h*.22
        p.setBrush(QColor(accent));p.setPen(Qt.NoPen)
        p.setOpacity(.3)
        for i in range(3):p.drawRect(QRectF(x+i*7,y,3,16))
        p.drawRect(QRectF(x-2,y-3,22,3));p.setOpacity(1)
        points=self.points()
        path=QPainterPath(points[0])
        for point in points[1:]:path.lineTo(point)
        p.setPen(QPen(QColor('#0a1427'),7 if self.compact else 10,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        p.setBrush(Qt.NoBrush);p.drawPath(path)
        p.setPen(QPen(QColor('#7896aa'),1.5,Qt.DashLine));p.drawPath(path)
        pos=max(0.,min(float(len(points)-1),self.position))
        lower=int(pos);fraction=pos-lower
        actor=points[lower]
        if lower+1<len(points):actor=actor+(points[lower+1]-actor)*fraction
        travelled=QPainterPath(points[0])
        for point in points[1:lower+1]:travelled.lineTo(point)
        travelled.lineTo(actor)
        p.setPen(QPen(QColor('#76cbbd'),3 if self.compact else 4,Qt.SolidLine,Qt.RoundCap));p.drawPath(travelled)
        if not self.end_button.isHidden():
            ending=QPainterPath(points[-1])
            ending.lineTo(points[-1].x(),h*.5);ending.lineTo(w*.5,h*.5)
            p.setPen(QPen(QColor('#e6c677'),3,Qt.SolidLine,Qt.RoundCap));p.drawPath(ending)
        checkpoints=set(self.data['checkpoints'])
        font=p.font();font.setPixelSize(8 if self.compact and len(points)>15 else 10 if self.compact else 13);p.setFont(font)
        radius=5 if self.compact and len(points)>15 else 8 if self.compact else 12
        for i,point in enumerate(points):
            checkpoint=i in checkpoints
            p.setPen(QPen(QColor('#f2cd70' if checkpoint else '#83b5af' if i<=pos else '#6b879d'),1.5))
            p.setBrush(QColor('#d2ac59' if checkpoint and i<=pos else '#162942'))
            p.drawEllipse(point,radius+2 if checkpoint else radius,radius+2 if checkpoint else radius)
            if not self.compact or len(points)<=15:
                p.setPen(QColor('#102239' if checkpoint and i<=pos else '#d7e5e6'))
                p.drawText(QRectF(point.x()-14,point.y()-10,28,20),Qt.AlignCenter,str(i))
        # Existing class art remains consistent with the sidebar and arena.
        seconds=self.idle_clock.elapsed()/1000
        side=34 if self.compact else 64
        if len(points)>15:
            side=min(side,max(22,(h-(52 if self.compact else 90)-35)/5*.86))
        bob=math.sin(seconds*(9 if self.walk_clock.isValid() else 2.4))*(2 if self.walk_clock.isValid() else .7)
        p.setPen(Qt.NoPen);p.setBrush(QColor(5,13,30,150))
        p.drawEllipse(actor,side*.3,side*.1)
        if not self.markers:
            self.hero.render(p,QRectF(actor.x()-side/2,actor.y()-side*.83+bob,side,side))
        else:
            chosen=next((i for i,m in enumerate(self.markers) if m.isChecked()),len(points)-1)
            point=points[chosen]
            self.hero.render(p,QRectF(point.x()-18,point.y()+63+bob,36,36))
        p.setPen(QColor(accent));font.setPixelSize(10 if self.compact else 14);p.setFont(font)
        p.drawText(QRectF(12,8,w-24,22),Qt.AlignLeft,'T E R R A')
        p.restore();p.end()


class TerraMapCard(LocalizedUI, QWidget):
    activated=Signal()
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,5,0,8);layout.setSpacing(5)
        self.heading=QLabel('TERRA · DEIN WEG ↗')
        self.heading.setStyleSheet('color:#d7bc78;font-size:11px;font-weight:600;background:transparent;')
        self.board=TerraBoard(compact=True);self.board.activated.connect(self.activated.emit)
        self.progress=QLabel();self.progress.setWordWrap(True)
        self.progress.setStyleSheet('font-size:12px;color:#c7d7e5;background:transparent;')
        self.open=QPushButton('Karte vergrößern ↗');self.open.setCursor(Qt.PointingHandCursor)
        self.open.setStyleSheet('font-size:12px;padding:6px;');self.open.clicked.connect(self.activated.emit)
        for widget in (self.heading,self.board,self.progress,self.open):layout.addWidget(widget)
        self.update_data(snapshot({}))

    def retranslate(self):
        super().retranslate()
        self.update_data(self.board.data)

    def update_data(self,data):
        self.board.language=self.language
        self.board.update_data(data)
        shown=localized_snapshot(data,self.language)
        self.progress.setText(shown['progress']+'\n'+shown['subtitle'])


class TerraJourneyView(LocalizedUI, QWidget):
    back_requested=Signal()
    boss_selected=Signal(str)
    random_requested=Signal()
    credits_requested=Signal()
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(10)
        row=QHBoxLayout()
        self.back=QPushButton('← Zurück');self.back.clicked.connect(self.back_requested.emit)
        row.addWidget(self.back);row.addStretch();self.leg=QLabel();row.addWidget(self.leg);layout.addLayout(row)
        self.title=QLabel();self.title.setWordWrap(True);self.title.setStyleSheet('font-family:Georgia;font-size:28px;color:#ead49c;')
        self.subtitle=QLabel();self.subtitle.setWordWrap(True)
        self.region_choice=QComboBox();self.region_choice.addItems(snapshot({})['regions'])
        self.region_choice.currentIndexChanged.connect(self.show_replay_region)
        self.random_encounters=QPushButton('Zufallskämpfe')
        self.random_encounters.setObjectName('terraRandom')
        self.random_encounters.setCheckable(True)
        self.random_encounters.setCursor(Qt.PointingHandCursor)
        self.random_encounters.setMinimumHeight(42)
        self.random_encounters.setStyleSheet(
            'QPushButton#terraRandom {background:#102239;color:#dce9f3;border:1px solid #617f9f;border-radius:8px;padding:8px 16px;}'
            'QPushButton#terraRandom:hover {background:#243d55;border-color:#f2d78e;}'
            'QPushButton#terraRandom:checked {background:#23434a;color:#f2d78e;border:2px solid #d6bd79;}'
            'QPushButton#terraRandom:disabled {color:#71869c;border-color:#344b63;}')
        self.random_encounters.clicked.connect(self.request_random_encounters)
        self._replay_ready=False
        self.board=TerraBoard()
        self.board.boss_selected.connect(self.boss_selected.emit)
        self.board.credits_requested.connect(self.credits_requested.emit)
        self.replay_note=QLabel();self.replay_note.setWordWrap(True)
        self.replay_note.setStyleSheet('color:#efd289;font-size:14px;')
        self.progress=QLabel();self.progress.setWordWrap(True);self.progress.setStyleSheet('color:#efd289;font-size:18px;')
        self.hint=QLabel();self.hint.setWordWrap(True);self.hint.setStyleSheet('color:#b5c9df;')
        legend=QLabel('● Gelb: Speicherpunkt / Ziel   ·   Türkis: bereister Weg   ·   Maatis: dein Standort')
        legend.setWordWrap(True);legend.setStyleSheet('font-size:12px;color:#afc1d8;')
        self.regions=QLabel();self.regions.setWordWrap(True);self.regions.setStyleSheet('font-size:12px;color:#b5c9df;')
        for widget in (self.title,self.subtitle,self.region_choice,self.random_encounters,self.board,self.replay_note,self.progress,self.hint,legend,self.regions):
            layout.addWidget(widget,1 if widget is self.board else 0)
        self.update_data(snapshot({}))

    def update_data(self,data):
        self.board.language=self.language
        was_complete=getattr(self,'data',{}).get('kind')=='complete'
        self.data=data
        shown=localized_snapshot(data,self.language)
        if not data.get('replay_targets'):self.board.update_data(data)
        if data.get('kind')!='complete':self._replay_error=''
        self.title.setText(shown['title'])
        self.subtitle.setText(shown['subtitle'])
        self.progress.setText(self.ui('{progress} · Ziel: {goal}',progress=shown['progress'],goal=shown['goal']))
        self.hint.setText(shown['hint'])
        self.leg.setText(self.ui('{bosses}/25 Bosse · {finals}/5 Finale',bosses=data['bosses'],finals=data['finals']))
        self.regions.setText('  ·  '.join(('◆' if i<data['finals'] else '◇')+' '+name for i,name in enumerate(shown['regions'])))
        self.region_choice.blockSignals(True)
        for index,name in enumerate(shown['regions']):self.region_choice.setItemText(index,name)
        self.region_choice.blockSignals(False)
        complete=data.get('kind')=='complete' and bool(data.get('replay_targets'))
        self.region_choice.setVisible(complete);self.replay_note.setVisible(complete)
        self.random_encounters.setVisible(complete)
        self.random_encounters.setText(self.ui('Zufallskämpfe'))
        self.random_encounters.setToolTip(self.ui('Bossauswahl aufheben und im Chat wieder normalen Zufallsgegnern begegnen.'))
        self.random_encounters.setChecked(complete and not data.get('replay_pending'))
        self.random_encounters.setEnabled(complete and self._replay_ready)
        if complete:
            if not was_complete:
                self.region_choice.blockSignals(True);self.region_choice.setCurrentIndex(0);self.region_choice.blockSignals(False)
            self.show_replay_region()

    def show_replay_region(self):
        if getattr(self,'data',{}).get('kind')!='complete':return
        region=self.region_choice.currentIndex()
        targets=[row for row in self.data['replay_targets'] if row['region']==region]
        pending=self.data.get('replay_pending')
        self.board.update_data(dict(self.data,id=f'replay-region-{region}',region=region,route=region*6,
            steps=5,position=5,checkpoints=list(range(6)),map_targets=targets,
            selected_target=pending['id'] if pending else None))
        self.subtitle.setText(self.ui(self.data['regions'][region])+self.ui(' · Bossbild anklicken'))
        self.hint.setText(self.ui('Wähle einen Boss für die nächste Zufallsbegegnung im Chat oder kehre mit „Zufallskämpfe“ zu normalen Gegnern zurück. EP und Gold bleiben erhalten.'))
        if region==4:self.hint.setText(self.hint.text()+self.ui(' „Ende der Welt“ öffnet den Abspann.'))
        note=(self.ui('Vorgemerkt: {name} · Beim nächsten Zufallskampf im Chat.',name=enemy_display_name(pending['name'],self.language))
              if pending else self.ui('Zufallskämpfe aktiv · Normale Gegner erscheinen weiterhin beim Chatten.'))
        self.replay_note.setText(getattr(self,'_replay_error','') or note)

    def request_random_encounters(self):
        # The saved worker snapshot decides the selection, also after a failed save.
        self.random_encounters.setChecked(not self.data.get('replay_pending'))
        if self._replay_ready and self.data.get('kind')=='complete':
            self.random_requested.emit()

    def retranslate(self):
        super().retranslate()
        self.update_data(self.data)

    def set_replay_ready(self,ready):
        self._replay_ready=bool(ready)
        self.board.set_replay_ready(ready)
        self.random_encounters.setEnabled(bool(ready) and self.data.get('kind')=='complete')

    def replay_result(self,text,ok=True):
        self._replay_error='' if ok else text
        self.replay_note.setText(text)
