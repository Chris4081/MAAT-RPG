"""One price source for terminal purchases and the native shop."""
ITEMS = {
    'potion': dict(name='Heiltrank', inventory='potions', base=75, per_level=5,
                   description='Stellt 50 % deiner maximalen HP wieder her. Im Kampf mindestens 10 HP; Pfadboni können die Heilung erhöhen.',
                   usage='Im Kampf über „Trank“. Auch außerhalb von Kämpfen verwendbar.', icon='🧪', color='#78d6c7'),
    'sigil': dict(name='Schutz-Siegel', inventory='sigils', base=125, per_level=8,
                  description='Verleiht zu Beginn des nächsten echten Kampfes ein Schild: mindestens 10, sonst 8 + 2 × Level.',
                  usage='Wird beim nächsten echten Kampf automatisch verbraucht. Nicht in der Demo.', icon='✦', color='#deb875'),
}


def item_price(item, level):
    data=ITEMS[item]
    return data['base'] + data['per_level'] * (max(1, int(level))-1)


def shop_snapshot(player):
    level=max(1,int(player.get('level',1)))
    return dict(gold=int(player.get('gold',0)),level=level,items=[
        dict(id=key,**data,price=item_price(key,level),owned=int(player.get(data['inventory'],0)))
        for key,data in ITEMS.items()])
