"""An embedded, keyboard-accessible talent tree driven by worker snapshots."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QPushButton, QLabel
from gui.desktop import label, button
from gui.hero_portrait import HeroPortrait
from gui.ui_i18n import LocalizedUI


class TalentNode(LocalizedUI, QPushButton):
    def __init__(self, node, selected, language='de'):
        super().__init__()
        self.language = language
        self.identifier = node['id']
        self.setMinimumWidth(150)
        self.setMinimumHeight(157)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: selected(self.identifier))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        self.name = QLabel(); self.rank = QLabel(); self.effect = QLabel(); self.requirement = QLabel()
        for child in (self.name, self.rank, self.effect, self.requirement):
            child.setWordWrap(True)
            child.setAttribute(Qt.WA_TransparentForMouseEvents)
            child.setStyleSheet('background:transparent;border:none;')
            layout.addWidget(child)
        self.name.setStyleSheet('background:transparent;border:none;color:#f1dfb6;font-size:17px;font-weight:600;')
        self.requirement.setStyleSheet('background:transparent;border:none;color:#9eb4ce;font-size:12px;')
        self.update_node(node)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # QPushButton's own size hint does not account for our wrapped labels.
        width = max(80, self.width()-30)
        height = 24 + 3*self.layout().spacing()
        for child in (self.name, self.rank, self.effect, self.requirement):
            needed = max(child.fontMetrics().height(), child.heightForWidth(width))
            child.setMinimumHeight(needed)
            height += needed
        self.setMinimumHeight(max(157, height))

    def update_node(self, node, selected=False):
        self.name.setText(node['name'])
        self.rank.setText('●'*node['rank']+'○'*(node['max_rank']-node['rank'])+f"   {node['rank']}/{node['max_rank']}")
        self.effect.setText(node['description'])
        self.requirement.setText(self.ui('Level {level} · {quests} Kampfquests · {cost} TP/Rang',level=node['level'],quests=node['quests'],cost=node['cost']))
        border = '#f2cf78' if selected else '#68c5b0' if node['rank'] else '#aa8950' if node['can_buy'] else '#2d4665'
        bg = '#183b48' if node['rank'] else '#132b46' if node['can_buy'] else '#0d1c32'
        self.setStyleSheet(f'QPushButton{{background:{bg};border:{2 if selected else 1}px solid {border};border-radius:12px;}}'
                          'QPushButton:hover{border:2px solid #ead49b;} QPushButton:focus{border:2px solid #fff2c7;}')
        self.setToolTip(node['description']+'\n'+(node['reason'] or self.ui('Zum Freischalten auswählen')))
        self.setAccessibleName(self.ui('{name}, Rang {rank} von {max_rank}. {description}. {reason}',**{k:node[k] for k in ('name','rank','max_rank','description','reason')}))


class TalentTree(LocalizedUI, QWidget):
    purchase_requested = Signal(dict)
    quests_requested = Signal()

    def __init__(self):
        super().__init__()
        self.data = {}; self.cards = {}; self.branches = {}; self.class_id = None
        self.selected = None; self.ready = False; self.submitted = False
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.portrait = HeroPortrait(86); top.addWidget(self.portrait)
        heading = QVBoxLayout()
        heading.addWidget(label('DEIN WEG WÄCHST MIT DIR', 'eyebrow'))
        self.title = label('Talentbaum', 'heading'); heading.addWidget(self.title)
        self.balance = label('Wähle nach deinem ersten Kampf eine Klasse.', 'muted')
        self.balance.setWordWrap(True); heading.addWidget(self.balance); top.addLayout(heading, 1)
        layout.addLayout(top)
        rules = label('1 Punkt pro Level + 1 pro einmaliger Kampf-/Dungeonquest, auch rückwirkend. '
                      'Drei Ränge je Talent. Ab der zweiten Reihe: Vorgänger auf Rang 2. '
                      'Die Punkte werden fest vergeben; Talente wirken automatisch im Kampf.', 'muted')
        rules.setWordWrap(True); layout.addWidget(rules)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.tree = QWidget(); self.grid = QGridLayout(self.tree); self.grid.setSpacing(12)
        self.scroll.setWidget(self.tree); layout.addWidget(self.scroll, 1)
        self.bonuses = label('Noch keine Talente gelernt.', 'muted'); self.bonuses.setWordWrap(True)
        layout.addWidget(self.bonuses)
        self.detail = label('Wähle ein Talent, um Wirkung und Voraussetzungen zu sehen.')
        self.detail.setWordWrap(True); layout.addWidget(self.detail)
        row = QHBoxLayout()
        self.learn = button('Talent auswählen', self.submit, True)
        self.learn.setMinimumHeight(42); row.addWidget(self.learn, 1)
        row.addWidget(button('⚔ Kampfquests', self.quests_requested.emit))
        layout.addLayout(row)
        self.receipt = label('', 'muted'); self.receipt.setWordWrap(True); layout.addWidget(self.receipt)
        self.refresh_selection()

    def retranslate(self):
        super().retranslate()
        for card in self.cards.values(): card.language = self.language
        self.update_data(self.data)

    def update_data(self, data):
        self.data = data
        changed = self.class_id != data.get('class_id')
        if changed:
            self.class_id = data.get('class_id'); self.selected = None; self.submitted = False
            self.receipt.clear()
            while self.grid.count():
                item = self.grid.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            self.cards = {}; self.branches = {}
            for node in data.get('nodes', []):
                col, tier = node['branch'], node['tier']
                if tier == 0:
                    title = label(node['icon']+'  '+node['branch_name'], 'heading')
                    self.branches[col] = title
                    title.setWordWrap(True); self.grid.addWidget(title, 0, col)
                    self.grid.setColumnStretch(col, 1)
                if tier:
                    arrow = QLabel('│\n▼'); arrow.setAlignment(Qt.AlignCenter)
                    arrow.setStyleSheet('color:#8bafbc;background:transparent;font-size:15px;')
                    self.grid.addWidget(arrow, tier*2, col)
                card = TalentNode(node, self.select, self.language)
                self.cards[node['id']] = card; self.grid.addWidget(card, tier*2+1, col)
        self.portrait.set_class(self.class_id)
        for node in data.get('nodes',[]):
            if node['tier'] == 0: self.branches[node['branch']].setText(node['icon']+'  '+node['branch_name'])
        self.title.setText(self.ui('{name} · Talentbaum',name=data.get('class_name','Maatis')))
        self.balance.setText(self.ui('✦ {available} freie Talentpunkte   ·   {spent} eingesetzt\nLevel: {level} Punkte   ·   Kampfquests: {quests} Punkte',available=data.get('available',0),spent=data.get('spent',0),level=data.get('level_points',0),quests=data.get('quest_points',0))
                             if data.get('unlocked') else self.ui('Freischaltung nach deiner Klassenwahl.'))
        self.bonuses.setText(self.ui('Aktiv: {bonuses}',bonuses=data['bonus_text']) if data.get('bonus_text') else self.ui('Noch keine Talente gelernt.'))
        self.refresh_selection()

    def select(self, identifier):
        self.selected = identifier; self.receipt.clear(); self.refresh_selection()

    def set_ready(self, ready):
        self.ready = ready; self.refresh_selection()

    def refresh_selection(self):
        current = None
        for node in self.data.get('nodes', []):
            self.cards[node['id']].update_node(node, node['id'] == self.selected)
            if node['id'] == self.selected: current = node
        self.learn.setEnabled(bool(current and current['can_buy'] and self.ready and not self.submitted))
        if current:
            self.detail.setText(current['name']+' — '+current['description']+'\n'+
                                (current['reason'] or self.ui('Bereit zum Lernen · Voraussetzung erfüllt')))
            self.learn.setText(self.ui('Wird gespeichert …') if self.submitted else self.ui('Vollständig gelernt') if current['rank']==3
                               else self.ui('Rang {rank} lernen · {cost} TP',rank=current['rank']+1,cost=current['cost']))
        else:
            self.detail.setText(self.ui('Wähle ein Talent, um Wirkung und Voraussetzungen zu sehen.'))
            self.learn.setText(self.ui('Talent auswählen'))

    def submit(self):
        node = next((n for n in self.data.get('nodes', []) if n['id']==self.selected), None)
        if not node or not self.learn.isEnabled(): return
        self.submitted = True; self.refresh_selection()
        self.purchase_requested.emit(dict(talent=node['id'], rank=node['rank'], class_id=self.class_id))

    def result(self, text, ok):
        self.submitted = False; self.receipt.setText(('✓ ' if ok else '⚠ ')+text)
        self.refresh_selection()
