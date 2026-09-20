"""Collapsible character status, outside the scrolling dialogue."""
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QScrollArea
from gui.hero_portrait import HeroPortrait, class_name
from gui.desktop import label, button
from gui.ui_i18n import LocalizedUI


class CharacterSidebar(LocalizedUI, QWidget):
    quest_requested = Signal(str)
    navigation_requested = Signal(str,str)
    def __init__(self):
        super().__init__()
        self._language_data = {}
        self.expanded = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 18, 12, 18)
        self.toggle = button('−', self.toggle_expanded)
        layout.addWidget(self.toggle)
        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(4, 8, 4, 0)
        self.portrait = HeroPortrait()
        body.addWidget(self.portrait, 0, Qt.AlignHCenter)
        self.name_heading=label('MAATIS', 'eyebrow');body.addWidget(self.name_heading)
        self.class_heading=label(class_name('normal'), 'muted');body.addWidget(self.class_heading)
        self.hp = label('')
        self.hp_bar = QProgressBar()
        self.hp_bar.setTextVisible(False)
        self.level = label('')
        self.wins = label('')
        self.items = label('')
        self.path = label('')
        for widget in (self.hp, self.hp_bar, self.level, self.wins, self.items, self.path):
            body.addWidget(widget)
        from gui.terra_map import TerraMapCard
        self.terra_map=TerraMapCard()
        body.addWidget(self.terra_map)
        body.addSpacing(14)
        self.quest_heading=label('AKTUELLE QUESTS ↗', 'eyebrow')
        self.link_quest_widget(self.quest_heading)
        body.addWidget(self.quest_heading)
        self.quest_rows=[]
        for _ in range(5):
            row=QWidget();row_layout=QVBoxLayout(row);row_layout.setContentsMargins(0,3,0,5);row_layout.setSpacing(4)
            name=label('');name.setWordWrap(True);name.setTextFormat(Qt.PlainText)
            progress=QProgressBar();progress.setMinimumHeight(20)
            progress.setStyleSheet('QProgressBar{background:#142b46;border:1px solid #345371;border-radius:4px;text-align:center;color:#ecdfbd;font-size:13px;} QProgressBar::chunk{background:#38776f;}')
            row_layout.addWidget(name);row_layout.addWidget(progress);body.addWidget(row);row.hide()
            self.quest_rows.append((row,name,progress))
            for widget in (row,name,progress):self.link_quest_widget(widget)
        self.quest_hint=label('Noch keine aktiven Quests.');self.quest_hint.setWordWrap(True);body.addWidget(self.quest_hint)
        self.link_quest_widget(self.quest_hint)
        body.addSpacing(14)
        self.achievement_heading=label('ERFOLGE ↗', 'eyebrow');body.addWidget(self.achievement_heading)
        self.achievement_summary=label('Erfolge werden geladen …')
        self.achievement_progress=QProgressBar()
        self.achievement_progress.setFormat('%p %')
        self.achievement_categories=label('')
        body.addWidget(self.achievement_summary);body.addWidget(self.achievement_progress);body.addWidget(self.achievement_categories)
        body.addSpacing(12);self.recent_heading=label('LETZTE ERFOLGE ↗', 'eyebrow');body.addWidget(self.recent_heading)
        self.recent_achievements=label('Neue Freischaltungen erscheinen hier.')
        body.addWidget(self.recent_achievements)
        body.addSpacing(12);self.dungeon_heading=label('DUNGEONS ↗', 'eyebrow');body.addWidget(self.dungeon_heading)
        self.dungeon_summary=label('Noch keine Durchläufe.')
        body.addWidget(self.dungeon_summary)
        for item in (self.achievement_summary,self.achievement_categories,self.recent_achievements,self.dungeon_summary):
            item.setWordWrap(True);item.setTextFormat(Qt.PlainText)
        for widget in (self.name_heading,self.portrait,self.class_heading,self.hp,self.hp_bar,self.level,self.wins,self.path):
            self.link_navigation(widget,'character','Charakter öffnen')
        self.link_navigation(self.items,'shop','Shop öffnen')
        for widget in (self.achievement_heading,self.achievement_summary,self.achievement_progress,self.recent_heading):
            self.link_navigation(widget,'achievements','Erfolge öffnen')
        for widget in (self.dungeon_heading,self.dungeon_summary):self.link_navigation(widget,'dungeons','Dungeon-Auswahl öffnen')
        for widget in (self.achievement_categories,self.recent_achievements):
            widget.setTextFormat(Qt.RichText);widget.setOpenExternalLinks(False)
            widget.setTextInteractionFlags(Qt.LinksAccessibleByMouse|Qt.LinksAccessibleByKeyboard)
            widget.linkActivated.connect(self.activate_detail_link)
        body.addStretch()
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet('QScrollArea{background:transparent;border:none;}')
        self.scroll.setWidget(self.body);layout.addWidget(self.scroll,1)
        self.apply_expanded()

    def retranslate(self):
        super().retranslate()
        self.apply_expanded()
        self.set_hero_class(self.portrait.class_id)
        self.terra_map.set_language(self.language)
        for method,args in list(self._language_data.items()):
            getattr(self,method)(*args)

    def toggle_expanded(self):
        self.expanded = not self.expanded
        self.apply_expanded()

    def apply_expanded(self):
        self.scroll.setVisible(self.expanded)
        self.setFixedWidth(240 if self.expanded else 60)
        self.toggle.setText('−' if self.expanded else '+')
        self.toggle.setAccessibleName(self.ui('Charakterleiste einklappen' if self.expanded else 'Charakterleiste aufklappen'))
        self.toggle.setToolTip(self.toggle.accessibleName())

    def set_hero_class(self, value):
        self.portrait.set_class(value)
        self.terra_map.board.set_class(value)
        self.class_heading.setText(class_name(value,self.language))

    def update_player(self, player):
        self._language_data['update_player']=(player,)
        self.hp.setText(f'❤️ HP {player.hp}/{player.max_hp}')
        self.hp_bar.setRange(0, max(1, player.max_hp))
        self.hp_bar.setValue(player.hp)
        self.items.setText(self.ui('💰 Gold: {gold}\n🧪 Heiltränke: {potions}',gold=player.gold,potions=player.potions))
        self.path.setText(self.ui('🜂 Pfad: {path}\n{rank}',path=player.path_profile,rank=player.rank))

    def update_profile(self, data):
        self._language_data['update_profile']=(data,)
        self.level.setText(f'📘 Level {data.get("level", 1)}\n{data.get("level_title", "")}')
        self.wins.setText(self.ui('⚔️ Siege: {wins}\nBoss-Siege: {bosses}',wins=data.get('fights_won',0),bosses=data.get('boss_wins',0)))
        if data.get('journey'): self.terra_map.update_data(data['journey'])

    def update_achievements(self,data):
        self._language_data['update_achievements']=(data,)
        from shared.core.achievement_catalog import localize
        data=localize(data,self.language)
        total=max(0,int(data.get('total',0)));done=max(0,int(data.get('unlocked',0)))
        self.achievement_summary.setText(self.ui('🏆 {done} / {total} freigeschaltet',done=done,total=total))
        self.achievement_progress.setRange(0,max(1,total));self.achievement_progress.setValue(done)
        from html import escape
        from urllib.parse import quote
        self.achievement_categories.setText('<br>'.join(f'<a style="color:#bad5ef;" href="category:{quote(name)}">{escape(self.ui(name))}: {sum(bool(r["unlocked"]) for r in rows)}/{len(rows)}</a>' for name,rows in data.get('groups',{}).items()))
        from datetime import datetime
        lines=[]
        for row in data.get('recent',[])[:5]:
            stamp=datetime.fromisoformat(row['at']).astimezone().strftime('%Y-%m-%d · %H:%M' if self.language=='en' else '%d.%m. · %H:%M')
            lines.append('<a style="color:#e8ca87;" href="achievement:'+quote(str(row.get('id','')),safe='')+'">'+escape(self.ui(row['name']))+'</a><br>'+self.ui('Erfasst: ')+stamp)
        self.recent_achievements.setText('<br><br>'.join(lines) if lines else self.ui('Noch keine neuen Erfolge erfasst. ')+'<a style="color:#e8ca87;" href="achievement:">'+self.ui('Erfolge-Tab öffnen')+'</a>.')
        self.recent_achievements.setToolTip(data.get('history_note',''))

    def update_dungeons(self,records,plus=None):
        self._language_data['update_dungeons']=(records,plus)
        rows=list(records.values())
        attempts=sum(max(0,int(r.get('attempts',0))) for r in rows)
        completed=sum(max(0,int(r.get('completed',0))) for r in rows)
        mastered=sum(int(r.get('completed',0))>0 for r in rows)
        best=max([max(0,min(5,int(r.get('best_room',0)))) for r in rows] or [0])
        rate=f'{completed/attempts*100:.0f} %' if attempts else '–'
        self.dungeon_summary.setText(self.ui('🏰 Durchläufe: {attempts}\nAbschlüsse: {completed}\nOrte gemeistert: {mastered}\nAbschlussquote: {rate}\nWeitester Raum: {best}/5',attempts=attempts,completed=completed,mastered=mastered,rate=rate,best=best))

        if plus:
            self.dungeon_summary.setText(self.dungeon_summary.text()+self.ui('\n\n∞ Dungeon+\nDurchläufe: {attempts}\nRekord: {best} Wellen\nSiege: {wins}',attempts=plus.get('attempts',0),best=plus.get('best_wave',0),wins=plus.get('total_wins',0)))

    def activate_detail_link(self,link):
        from urllib.parse import unquote
        kind,_,value=link.partition(':')
        if kind in ('category','achievement'):self.navigation_requested.emit(kind,unquote(value))

    def link_navigation(self,widget,destination,hint):
        widget.setProperty('sidebar_link',destination);widget.setCursor(Qt.PointingHandCursor)
        widget.setFocusPolicy(Qt.StrongFocus);widget.setToolTip(hint);widget.installEventFilter(self)

    def link_quest_widget(self,widget):
        widget.setProperty('quest_link','')
        widget.setCursor(Qt.PointingHandCursor)
        widget.setFocusPolicy(Qt.StrongFocus)
        widget.setToolTip('Questlog öffnen')
        widget.installEventFilter(self)

    def eventFilter(self,obj,event):
        if obj.property('quest_link') is not None or obj.property('sidebar_link') is not None:
            activated=(event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton and obj.rect().contains(event.position().toPoint())) or (event.type()==QEvent.KeyPress and event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space) and not event.isAutoRepeat())
            if activated:
                if obj.property('sidebar_link') is not None:self.navigation_requested.emit(str(obj.property('sidebar_link')),'')
                else:self.quest_requested.emit(str(obj.property('quest_link')))
                return True
        return super().eventFilter(obj,event)

    def update_quests(self,data):
        self._language_data['update_quests']=(data,)
        active=[q for q in data.get('groups',{}).get('active',[]) if not q.get('completed')]
        for i,(row,name,bar) in enumerate(self.quest_rows):
            if i>=len(active):
                row.hide();name.clear();bar.setValue(0);continue
            q=active[i];name.setText(str(q.get('name','Quest')));row.setToolTip(self.ui('Quest im Questlog öffnen\n')+str(q.get('desc','')))
            for widget in (row,name,bar):widget.setProperty('quest_link',str(q.get('id','')))
            target=q.get('target')
            if target and int(target)>0:
                target=int(target);value=min(target,max(0,int(q.get('progress',0) or 0)))
                bar.setRange(0,target);bar.setValue(value);bar.setFormat(f'{value}/{target}'+(self.ui(' Tage') if q.get('is_daily') else ''));bar.show()
                bar.setAccessibleName(self.ui('{name}: {value} von {target}',name=q.get('name','Quest'),value=value,target=target))
            else:
                bar.hide();name.setText(name.text()+'\n'+str(q.get('progress_text') or q.get('status_label') or self.ui('Aktiv')))
            row.show()
        extra=max(0,len(active)-5)
        self.quest_hint.setText(self.ui('+ {extra} weitere im Questlog',extra=extra) if extra else self.ui('Noch keine aktiven Quests.') if not active else '')
        self.quest_hint.setVisible(bool(self.quest_hint.text()))

    def reset_statistics(self):
        self.update_quests({})
        self.update_achievements({});self.update_dungeons({})
        self.scroll.verticalScrollBar().setValue(0)
