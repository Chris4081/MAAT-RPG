"""Native shop, backed by the original /shop buy commands."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QSpinBox, QTabWidget
from gui.ui_i18n import LocalizedUI

class Shop(LocalizedUI, QWidget):
    purchase_requested=Signal(str)
    def __init__(self):
        super().__init__()
        self.ready=False
        self.data={}
        self.items={}
        self.columns=2
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        banner=QWidget();banner.setObjectName('shopBanner')
        banner.setStyleSheet('QWidget#shopBanner {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #234263,stop:1 #111c32);border:1px solid #907747;border-radius:12px;}')
        top=QVBoxLayout(banner)
        title=QLabel('✦  DER BASAR VON TERRA');title.setStyleSheet('font-size:27px;font-weight:700;color:#f0d59d;');top.addWidget(title)
        subtitle=QLabel('Vorräte für den nächsten Schritt. Schutz für den entscheidenden Augenblick.')
        subtitle.setWordWrap(True);subtitle.setStyleSheet('font-size:16px;color:#c0cede;');top.addWidget(subtitle)
        self.balance=QLabel('Gold wird geladen …');self.balance.setStyleSheet('font-size:23px;font-weight:700;color:#f0d59d;');top.addWidget(self.balance)
        layout.addWidget(banner)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        supplies=QWidget();supplies_layout=QVBoxLayout(supplies)
        self.tabs.addTab(supplies,"Vorräte")
        from gui.contract_board import ContractBoard
        self.contracts=ContractBoard()
        self.tabs.addTab(self.contracts,"📜 Auftragsbrett")
        self.contracts.purchase_requested.connect(self.buy_contract)
        self.grid=QGridLayout();self.grid.setSpacing(18);supplies_layout.addLayout(self.grid)
        from shared.core.shop_catalog import ITEMS
        for i,(key,item) in enumerate(ITEMS.items()):
            card=QWidget();card.setObjectName('shopItem')
            card.setStyleSheet(f'QWidget#shopItem {{background:#101f36;border:1px solid {item["color"]};border-radius:12px;}}')
            c=QVBoxLayout(card);c.setContentsMargins(22,18,22,20);c.setSpacing(14)
            art=QLabel(item['icon']);art.setAlignment(Qt.AlignCenter);art.setProperty('shopArt',True);art.setFixedHeight(132)
            art.setStyleSheet(f'font-size:66px;color:{item["color"]};background:#172d44;border-radius:12px;padding:16px;');c.addWidget(art)
            name=QLabel(item['name']);name.setMinimumHeight(38);name.setStyleSheet(f'font-size:25px;font-weight:700;color:{item["color"]};');c.addWidget(name)
            desc=QLabel(item['description']);desc.setWordWrap(True);desc.setMinimumHeight(72);desc.setStyleSheet('font-size:17px;');c.addWidget(desc)
            usage=QLabel(item['usage']);usage.setWordWrap(True);usage.setMinimumHeight(48);usage.setStyleSheet('font-size:14px;color:#a9bdd1;');c.addWidget(usage)
            c.addStretch()
            info=QLabel();info.setStyleSheet('font-size:17px;color:#efd69e;');c.addWidget(info)
            row=QHBoxLayout();row.addWidget(QLabel('Menge'))
            quantity=QSpinBox();quantity.setRange(1,99);quantity.setMinimumHeight(38);row.addWidget(quantity)
            c.addLayout(row)
            buy=QPushButton();buy.setMinimumHeight(48)
            buy.setStyleSheet('QPushButton {background:#be9b55;color:#101c2d;border:1px solid #efd69e;border-radius:8px;font-size:18px;font-weight:700;text-align:center;} QPushButton:hover {background:#e1bd72;} QPushButton:disabled {background:#24334a;color:#8192a9;border-color:#41516a;}')
            c.addWidget(buy)
            self.items[key]=dict(card=card,info=info,quantity=quantity,buy=buy,name=name,description=desc,usage=usage)
            quantity.valueChanged.connect(self.refresh)
            buy.clicked.connect(lambda checked=False,k=key:self.buy(k))
            self.grid.addWidget(card,0,i)
        note=QLabel('Preise steigen mit deinem Level. Kein Rabatt auf Mehrfachkäufe. Gekaufte Gegenstände werden im Profil gespeichert.')
        note.setWordWrap(True);note.setStyleSheet('font-size:14px;color:#b6c3d5;');supplies_layout.addWidget(note)
        self.receipt=QLabel('Wähle deine Vorräte.');self.receipt.setWordWrap(True);self.receipt.setStyleSheet('font-size:17px;color:#87debc;');layout.addWidget(self.receipt)
        layout.addStretch()
        for text_label in self.findChildren(QLabel):
            if not text_label.property('shopArt'):
                text_label.setStyleSheet(text_label.styleSheet() + 'background:transparent;')
        self.refresh()

    def retranslate(self):
        super().retranslate()
        self.contracts.set_language(self.language)
        self.tabs.setTabText(0,self.ui('Vorräte'))
        self.tabs.setTabText(1,self.ui('📜 Auftragsbrett'))
        self.refresh()

    def set_receipt(self,text):
        self.receipt.setText(self.ui(text))

    def update_data(self,data):
        self.data=data
        self.refresh()

    def set_ready(self,ready):
        if self.ready == ready:
            return
        self.ready=ready
        self.refresh()

    def refresh(self):
        self.contracts.update_data(self.data,self.ready)
        gold=self.data.get('gold',0)
        self.balance.setText(self.ui('◈  {gold} Gold     ·     Level {level}',gold=gold,level=self.data.get('level',1)))
        current={i['id']:i for i in self.data.get('items',[])}
        for key,widgets in self.items.items():
            item=current.get(key)
            cost=item['price']*widgets['quantity'].value() if item else 0
            widgets['info'].setText(self.ui('{price} Gold / Stück   ·   Im Beutel: {owned}',price=item['price'],owned=item['owned']) if item else self.ui('Sortiment wird geladen …'))
            widgets['buy'].setText(self.ui('Kaufen · {cost} Gold',cost=cost) if gold>=cost else self.ui('Es fehlen {missing} Gold',missing=cost-gold))
            widgets['buy'].setEnabled(bool(item and self.ready and gold>=cost))
            widgets['quantity'].setEnabled(self.ready)

    def buy_contract(self,command):
        self.set_ready(False)
        self.set_receipt('Auftrag wird gekauft …')
        self.purchase_requested.emit(command)

    def buy(self,key):
        if not self.items[key]['buy'].isEnabled():return
        amount=self.items[key]['quantity'].value()
        self.set_ready(False)
        self.set_receipt('Kauf wird verarbeitet …')
        self.purchase_requested.emit(f'/shop buy {key} {amount}')

    def resizeEvent(self,event):
        super().resizeEvent(event)
        columns=2 if self.width()>=700 else 1
        if columns!=self.columns:
            self.columns=columns
            for i,widgets in enumerate(self.items.values()):
                self.grid.addWidget(widgets['card'],i//columns,i%columns)
