"""Read-only view of terminal achievements and persistent arcade milestones."""
from apps.maat_rpg.plugins.achievements.plugin_main import TRIGGERS, COMBAT_ACHIEVEMENTS, COMBAT_ACHIEVEMENTS_EN
from apps.maat_rpg.plugins.emotional_achievements.plugin_main import ACHIEVEMENTS as EMOTIONAL
from shared.core.minigames import CATALOG
from shared.core.minigame_i18n import game_info
from shared.core.achievement_i18n import WORDS, EMOTIONS, tr

COMBAT_GOALS={
 'special_survived':'Einen Kampf gewinnen, nachdem du eine Spezialattacke überlebt hast.',
 'phase2_reached':'Einen Boss besiegen, der seine zweite Phase erreicht hat.',
 'boss_no_potion':'Einen Boss ohne Heiltrank besiegen.',
 'ult_finisher':'Einen Kampf mit dem Resonanz-Finisher beenden.',
}

def entry(key,name,description,current=0,target=1,xp=0):
    return dict(id=key,name=name,description=description,current=min(current,target),target=target,unlocked=current>=target,xp=xp)

def snapshot(battle,words=None,emotions=None,language='de'):
    words=set((words or {}).get('unlocked',[]));emotions=(emotions or {}).get('achievements',{})
    combat=set(battle.get('achievements',{}).get('combat',[]))
    groups={
      'Worte & Entdeckungen':[entry('word:'+word,title,f'Im Gespräch das Wort „{word}“ verwenden.',int(word in words),xp=xp) for word,(title,xp) in TRIGGERS.items()],
      'Emotionale Erfolge':[entry('emotion:'+key,data['name'],'Im Gespräch: '+ ' / '.join(data['check']),int(bool(emotions.get(key))),xp=data['xp']) for key,data in EMOTIONAL.items()],
      'Kampf':[entry('combat:'+key,title,COMBAT_GOALS[key],int(key in combat)) for key,title in COMBAT_ACHIEVEMENTS.items()],
    }
    mini=battle.get('minigames',{});wins=mini.get('wins',{});discovered=len(set(mini.get('discovered',[]))&set(CATALOG))
    total=sum(max(0,int(wins.get(k,0))) for k in CATALOG);mastered=sum(wins.get(k,0)>0 for k in CATALOG)
    rows=[]
    for n,title in [(1,'🎟 Eintritt in die Spielhalle'),(5,'🗺 Spielesammler'),(len(CATALOG),'🗝 Die ganze Spielhalle')]:
        rows.append(entry('arcade:discover:'+str(n),title,f'{n} verschiedene Spiele im Chat entdecken.',discovered,n))
    for n,title in [(1,'🏅 Der erste Spielesieg'),(10,'🏆 Tempelspieler'),(50,'👑 Legende der Spielhalle')]:
        rows.append(entry('arcade:wins:'+str(n),title,f'{n} Minispiele gewinnen · Chat oder Spielhalle.',total,n))
    rows.append(entry('arcade:first_try','⚡ Auf Anhieb','5 Chat-Herausforderungen im ersten Versuch gewinnen.',mini.get('first_try_wins',0),5))
    rows.append(entry('arcade:chat','📜 Herausforderung angenommen','10 Chat-Herausforderungen gewinnen.',mini.get('chat_wins',0),10))
    rows.append(entry('arcade:master','✦ Meister aller Spiele',f'Jedes der {len(CATALOG)} Spiele mindestens einmal gewinnen.',mastered,len(CATALOG)))
    for kind,(title,goal,xp,gold) in CATALOG.items():
        rows.append(entry('arcade:game:'+kind,title+' · Sieger',goal+' · Einmal gewinnen, im Chat oder in der Spielhalle.',wins.get(kind,0)))
    groups['Minispiele']=rows
    all_rows=[r for group in groups.values() for r in group]
    return localize(dict(groups=groups,total=len(all_rows),unlocked=sum(r['unlocked'] for r in all_rows)),language)


def display_text(row, language):
    """Rebuild authored captions by ID, also when switching back from English."""
    key=row.get('id','')
    if key.startswith('word:') and key[5:] in TRIGGERS:
        word=key[5:]
        name=WORDS[word][0] if language=='en' else TRIGGERS[word][0]
        example=WORDS[word][1][0] if language=='en' else word
        return name,tr('Im Gespräch das Wort „{word}“ verwenden.',language,word=example)
    if key.startswith('emotion:') and key[8:] in EMOTIONAL:
        data=EMOTIONAL[key[8:]]
        name,examples=(EMOTIONS[key[8:]][0],EMOTIONS[key[8:]][2]) if language=='en' else (data['name'],data['check'])
        return name,tr('Im Gespräch: {examples}',language,examples=' / '.join(examples))
    if key.startswith('combat:') and key[7:] in COMBAT_ACHIEVEMENTS:
        name=(COMBAT_ACHIEVEMENTS_EN if language=='en' else COMBAT_ACHIEVEMENTS)[key[7:]]
        return name,tr(COMBAT_GOALS[key[7:]],language)
    if key.startswith('arcade:game:') and key[12:] in CATALOG:
        name,goal,*_=game_info(key[12:],language)
        return tr('{name} · Sieger',language,name=name),tr('{goal} · Einmal gewinnen, im Chat oder in der Spielhalle.',language,goal=goal)
    milestones={
        'arcade:discover:1':('🎟 Eintritt in die Spielhalle','{count} verschiedene Spiele im Chat entdecken.',1),
        'arcade:discover:5':('🗺 Spielesammler','{count} verschiedene Spiele im Chat entdecken.',5),
        'arcade:discover:'+str(len(CATALOG)):('🗝 Die ganze Spielhalle','{count} verschiedene Spiele im Chat entdecken.',len(CATALOG)),
        'arcade:wins:1':('🏅 Der erste Spielesieg','{count} Minispiele gewinnen · Chat oder Spielhalle.',1),
        'arcade:wins:10':('🏆 Tempelspieler','{count} Minispiele gewinnen · Chat oder Spielhalle.',10),
        'arcade:wins:50':('👑 Legende der Spielhalle','{count} Minispiele gewinnen · Chat oder Spielhalle.',50),
        'arcade:first_try':('⚡ Auf Anhieb','5 Chat-Herausforderungen im ersten Versuch gewinnen.',5),
        'arcade:chat':('📜 Herausforderung angenommen','10 Chat-Herausforderungen gewinnen.',10),
        'arcade:master':('✦ Meister aller Spiele','Jedes der {count} Spiele mindestens einmal gewinnen.',len(CATALOG)),
    }
    if key in milestones:
        name,goal,count=milestones[key]
        return tr(name,language),tr(goal,language,count=count)
    return row.get('name',''),row.get('description','')


def localize(data, language='de'):
    def translated(row):
        name,description=display_text(row,language)
        return dict(row,name=name,description=description)
    result=dict(data,groups={category:[translated(row) for row in rows]
                            for category,rows in data.get('groups',{}).items()})
    if 'recent' in data:result['recent']=[translated(row) for row in data['recent']]
    if 'history_note' in data:
        result['history_note']=tr('Neue Freischaltungen werden ab diesem Update erfasst. Für ältere Erfolge ist die Reihenfolge unbekannt.',language)
    return result
