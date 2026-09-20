"""Five-room expeditions, using the terminal dungeon themes and battle core."""
from pathlib import Path
from .gameplay_i18n import tr

PLUGINS=Path(__file__).resolve().parents[2]/'apps/maat_rpg/plugins'
THEMES=[
 ('Tor der 60 Stimmen','dungeon_60','dungeon_theme.mp3','boss_theme.mp3','Wächter der Resonanz',[
  'Du betrittst den Tunnel der Stimmen.',
  'Schatten greifen nach deinem Geist, aber du bleibst standhaft.',
  'Ein Kreis aus goldenen Glyphen bildet den Boden.']),
 ('Kristallgewölbe','dungeon_500','crystal_theme.mp3','crystal_boss.mp3','Herr der 500 Schatten',[
  'Die Kristalle an den Wänden beginnen leise zu singen. Ein kühles, blaues Licht erfüllt den Gang.',
  'Brechende Lichtstrahlen tanzen über den Boden wie wandernde Runen. Du spürst, wie der Raum auf deine Schritte reagiert.',
  'Vor dir erhebt sich ein Tor aus poliertem Glas, in dem sich unzählige Welten spiegeln. Zwischen den Reflexionen flackert eine Silhouette.']),
 ('Tiefe der tausend Echos','dungeon_1000','dungeon1000_theme.mp3','boss1000_theme.mp3','Archon der tausend Echos',[
  'Die Luft flirrt vor alter Magie.', 'Flüsternde Schatten testen deinen Willen.', 'Der Boden pulsiert im Takt der Echos.']),
]
NAMES=['Tor der 60 Stimmen','Kristallgewölbe','Tiefe der tausend Echos','Gärten der Harmonie','Waage der versunkenen Stadt','Schmiede der Schöpfung','Brücken der Verbundenheit','Halle des Respekts','Herz der fünf Prinzipien']
NEW_ROOMS={
 3:[
  'Unter der Wüste wächst ein Garten aus klingendem Glas. Maatis entdeckt eine Blüte, deren Ton alle anderen überlagert.',
  'Wurzeln versperren den Weg. Zwischen ihnen bewegt sich ein Schatten, der jede Berührung in einen schrillen Akkord verwandelt.',
  'An einem trockenen Brunnen hört Maatis zwei Melodien. Er sucht den gemeinsamen Takt, als sich ein Wächter aus dem Wasserlicht erhebt.',
  'Vier Beete leuchten auf. Im fünften sammelt sich die Dissonanz zu einer Gestalt, die keinen anderen Klang duldet.',
  'Unter dem Baum der Stimmen wartet der Hüter. Maatis muss Raum für die leisen Töne schaffen, bevor der Garten wieder atmen kann.'],
 4:[
  'Treppen führen in eine versunkene Stadt. Ihre Häuser hängen an den Schalen einer gewaltigen Waage.',
  'Maatis betritt eine Brücke, die bei jedem Schritt ihre Neigung ändert. Ein steinerner Wächter hält die schwerere Seite besetzt.',
  'In einer Halle liegt Gold auf der einen Schale, ein einzelnes Samenkorn auf der anderen. Beide wiegen gleich schwer.',
  'Der Gegenspieler zieht an unsichtbaren Gewichten. Maatis erkennt, dass jede gewonnene Kraft auch eine Grenze braucht.',
  'Im Mittelpunkt der Stadt steht der Richter der Gewichte. Hinter ihm wartet eine Waage, die seit Jahrhunderten nicht stillgestanden hat.'],
 5:[
  'Die Schmiede glüht, obwohl niemand ihre Feuer nährt. Über dem Amboss schwebt eine Form, die noch keinen Namen hat.',
  'Aus verstreuten Splittern wachsen Werkzeuge. Ein Konstrukt versucht, jede neue Form sofort wieder zu zerbrechen.',
  'Maatis findet einen Plan mit einer freien Stelle. Hier muss etwas entstehen, das die alten Baumeister noch nicht kannten.',
  'Funken verbinden sich zu einem Ring. Ein ruheloser Geist hält ihn offen und verschlingt jedes unfertige Werk.',
  'Der Meister des ersten Funkens hebt seinen Hammer. Maatis tritt vor den Amboss, um dem entstehenden Licht eine Form zu geben.'],
 6:[
  'Fünf schmale Brücken schweben über einem Abgrund. Am anderen Ufer bewegt sich ein Licht im selben Rhythmus wie Maatis.',
  'Eine Brücke bricht hinter ihm auseinander. Ein Phantom versucht, den letzten Faden zum Ausgang zu durchtrennen.',
  'An einem Knotenpunkt hört Maatis die Stimmen früherer Reisender. Ihre Spuren bilden gemeinsam einen neuen Weg.',
  'Ein Schatten tarnt sich als rettende Hand. Maatis prüft, welche Verbindung trägt und welche ihn nur festhält.',
  'Der Wächter der getrennten Ufer steht zwischen den letzten Pfeilern. Hinter ihm reichen die Fäden erstmals bis zur anderen Seite.'],
 7:[
  'Vor der Halle liegt eine unberührte Schwelle. Maatis bleibt stehen, bis das Licht über der Tür ihm Einlass gewährt.',
  'Ein Wächter rückt immer näher. Maatis hält seine Grenze, ohne selbst den schützenden Kreis des Raumes zu zerstören.',
  'An den Wänden stehen Namen, die niemand mehr aussprechen wollte. Maatis liest sie, und eine vergessene Gestalt erwacht.',
  'Der Raum bietet ihm eine Abkürzung über zerbrochene Siegel. Er wählt den freien Weg und begegnet dem Hüter dieser Entscheidung.',
  'Vor dem letzten Tor wartet der Grenzwächter. Hier zählt nicht nur, welche Kraft Maatis besitzt, sondern wie er sie einsetzt.'],
 8:[
  'Unter der Pyramide laufen fünf Lichtlinien zusammen. Eine davon flackert; Maatis folgt ihr bis zu einer dunklen Kammer.',
  'Harmonie und Balance antworten einander. Zwischen ihren Strahlen erhebt sich ein Widerstand, der beide auseinanderdrängt.',
  'Ein neuer Funke springt auf die dritte Linie über. Ein Konstrukt versucht, ihn in eine starre Form zu zwingen.',
  'Die vierte Linie sucht die fünfte. Maatis schützt ihre Verbindung vor einem Schatten, der jede Grenze verwischt.',
  'Im Herzen des Tempels wartet der Hüter der fünf Siegel. Hinter ihm ist kein Ende zu sehen, sondern eine Treppe in größere Tiefe.'],
}
NEW_GUARDIANS=['Hüter des klingenden Gartens','Richter der Gewichte','Meister des ersten Funkens','Wächter der getrennten Ufer','Grenzwächter des Respekts','Hüter der fünf Siegel']
# Regular rooms draw from their setting; explicitly named creatures in the
# authored narration retain a matching form. Room five keeps its original boss.
THEMED_KINDS = [
 ('Wanderer','Wächter','Skarabäus','Skorpion','Schlange','Sandwurm','Schakal','Falke'),
 ('Wächter','Konstrukt','Golem','Spinne','Qualle','Funke','Motte','Drache'),
 ('Phantom','Beobachter','Qualle','Spinne','Motte','Schlange','Drache','Idol'),
 ('Motte','Fangschrecke','Spinne','Falke','Schlange','Skarabäus','Funke','Wächter'),
 ('Golem','Wächter','Idol','Konstrukt','Skarabäus','Skorpion','Schakal'),
 ('Konstrukt','Golem','Funke','Drache','Skarabäus','Phantom'),
 ('Phantom','Qualle','Spinne','Falke','Beobachter','Motte','Schlange'),
 ('Wächter','Idol','Golem','Schakal','Falke','Wanderer','Skarabäus'),
 ('Drache','Golem','Wächter','Konstrukt','Funke','Skorpion','Fangschrecke','Qualle'),
]
NARRATIVE_KINDS = {(3,2):('Wächter',), (4,1):('Wächter',),
                   (5,1):('Konstrukt',), (5,3):('Phantom',),
                   (6,1):('Phantom',), (7,1):('Wächter',), (7,3):('Wächter',),
                   (8,2):('Konstrukt',)}


def room_enemy(state, index, room, language='de'):
    from .monster_catalog import choose_enemy_name, enemy_display_name
    place = index % len(NAMES)
    name = choose_enemy_name(state, kinds=NARRATIVE_KINDS.get((place, room), THEMED_KINDS[place]))
    return enemy_display_name(name, language)


EXTENSIONS=[
 'Maatis findet fünf leere Zeichen im Stein. Hinter jedem wartet ein Widerstand; erst gemeinsam öffnen sie den Rückweg.',
 'Eine silberne Spur teilt den Raum. Maatis folgt ihrem Klang, während ein weiterer Hüter aus dem Dunkel tritt.',
 'Drei Zeichen antworten aufeinander. Doch die Stille zwischen ihnen verbirgt einen neuen Gegner.',
 'Vor dem letzten Tor liegt ein zerbrochenes Siegel. Maatis hebt die Teile auf; ihr Licht lockt den vorletzten Hüter herbei.',
 'Die fünf Wege laufen in einer Kammer zusammen. Ihr Wächter tritt vor. Hinter ihm wartet das letzte Zeichen dieses Ortes.',
]

def dungeon(index, language='de'):
    index=int(index)
    if index<0 or index>10000:raise ValueError(tr('Unbekannter Dungeon.',language))
    theme=THEMES[index%3];depth=index//len(NAMES)+1
    name=tr(NAMES[index%len(NAMES)],language)+(tr(' · Tiefe {depth}',language,depth=depth) if depth>1 else '')
    theme_path=PLUGINS/theme[1]/'music'/theme[2]
    if not theme_path.is_file():theme_path=PLUGINS/theme[1]/'music'/theme[3]
    place=index%len(NAMES)
    return dict(id=index,level=10+5*index,name=name,theme=str(theme_path),
                boss_music=str(PLUGINS/theme[1]/'music'/theme[3]),guardian=tr(NEW_GUARDIANS[place-3] if place>=3 else theme[4],language),original=[tr(line,language) for line in NEW_ROOMS.get(place,theme[5])])

def catalog(level,progress=None,language='de'):
    # Show the first nine locations, then always one locked destination ahead.
    count=max(9,(max(1,int(level))-10)//5+2)
    return [dict(dungeon(i,language),record=(progress or {}).get(str(i),{})) for i in range(min(count,10001))]

def run(core,index,narrate,notify,on_progress=None,language='de'):
    d=dungeon(index,language);state=core.state.state
    if int(state['player']['level'])<d['level']:raise ValueError(tr('Dieser Dungeon öffnet sich ab Level {level}.',language,level=d['level']))
    if state['player'].get('hp',1)<=1:raise ValueError(tr('Maatis braucht erst Erholung im Chat oder einen Heiltrank.',language))
    record=state.setdefault('dungeon_runs',{}).setdefault(str(d['id']),{'attempts':0,'completed':0,'best_room':0})
    record['attempts']+=1;record['last_result']='begonnen';core.state.save()
    try:
        notify('audio',action='play',owner='dungeon-run',path=d['theme'],loop=True)
        for room in range(5):
            notify('dungeon_progress',active=True,id=d['id'],name=d['name'],room=room+1,total=5)
            lines=[d['original'][room] if room<len(d['original']) else tr('Das Tor hinter Maatis bleibt offen, doch vor ihm wartet die nächste Prüfung.',language),tr(EXTENSIONS[room],language)]
            if room==0:lines.append(tr('Fünf Kämpfe liegen vor dir. Deine KP und Heiltränke begleiten dich durch alle Räume; eine Flucht beendet den Durchlauf.',language))
            narrate(lines,None,{'name':tr('{name} · Raum {room}/5',language,name=d['name'],room=room+1),'module':'dungeon_room'})
            before=state['stats'].get('fights_won',0)
            enemy=d['guardian'] if room==4 else room_enemy(state,index,room,language)
            ctx={'combat_source':'dungeon','continuous_dungeon_music':True,'battle_profile':{
                'boss_name':enemy,
                'enemy':{'hp_mult':.65+room*.13,'damage_mult':.5+room*.08,'xp_mult':.8+room*.1},
                'intro_lines':[tr('Dungeon: {name} · Gegner {room}/5',language,name=d['name'],room=room+1)],
                'victory_lines':[tr('Ein weiteres Zeichen leuchtet. Maatis kann tiefer vordringen.',language)]}}
            core.run_fight('normal',context=ctx)
            if state['stats'].get('fights_won',0)<=before:
                record['last_result']='abgebrochen';core.state.save()
                narrate([tr('Maatis tritt den Rückweg an. Die bereits gewonnenen Belohnungen bleiben bei ihm.',language),
                         tr('Die übrigen Zeichen verlöschen. Beim nächsten Eintritt beginnt die Prüfung wieder im ersten Raum.',language)],None,{'name':tr('Dungeon beendet',language),'module':'dungeon_end'})
                return False
            record['best_room']=max(record.get('best_room',0),room+1);core.state.save()
        record['completed']+=1;record['last_result']='geschafft';core.state.save()
        if on_progress is not None:on_progress()
        narrate([tr('Alle fünf Zeichen leuchten. Der Raum antwortet mit einem einzigen, ruhigen Klang.',language),
                 tr('Maatis trägt die Erinnerung an diesen Weg hinaus. Der Dungeon ist bezwungen; seine Tore bleiben für weitere Reisen offen.',language)],None,{'name':tr('{name} · Vollendet',language,name=d['name']),'module':'dungeon_end'})
        return True
    except BaseException:
        record['last_result']='unterbrochen'
        core.state.save()
        raise
    finally:
        notify('audio',action='stop',owner='dungeon-run')
        notify('dungeon_progress',active=False,id=d['id'],name=d['name'],room=0,total=5)


def run_endless(core,narrate,notify,on_progress=None,language='de'):
    """One expedition without a wave limit; the normal flee action ends it."""
    state=core.state.state
    if int(state['player']['level'])<50:raise ValueError(tr('Dungeon+ öffnet sich ab Level 50.',language))
    if state['player'].get('hp',1)<=1:raise ValueError(tr('Maatis braucht erst Erholung im Chat oder einen Heiltrank.',language))
    record=state.setdefault('dungeon_plus',{'attempts':0,'best_wave':0,'total_wins':0})
    record['attempts']+=1;record['last_wave']=0;record['last_result']='läuft';core.state.save()
    from shared.core.monster_catalog import choose_enemy_name,enemy_display_name
    wave=1
    try:
        notify('dungeon_progress',active=True,id='plus',name='Dungeon+',room=wave,total=None)
        notify('audio',action='play',owner='dungeon-plus',playlist=[dungeon(i)['theme'] for i in range(3)])
        narrate([tr('Unter dem letzten Siegel öffnet sich eine Treppe ohne sichtbares Ende.',language),
                 tr('Maatis tritt in Dungeon+. Hinter jedem Gegner wartet ein weiterer; mit jeder Welle wächst der Widerstand.',language),
                 tr('KP und Tränke bleiben erhalten. Fliehe aus einem Kampf, um den Durchlauf zu beenden. Siege, Belohnungen und dein Wellenrekord werden nach jedem Sieg gespeichert.',language)],None,{'name':tr('Dungeon+ · Die endlose Tiefe',language),'module':'dungeon_room'})
        while True:
            notify('dungeon_progress',active=True,id='plus',name='Dungeon+',room=wave,total=None)
            enemy=enemy_display_name(choose_enemy_name(state),language)
            before=state['stats'].get('fights_won',0)
            core.run_fight('normal',context={'combat_source':'dungeon','continuous_dungeon_music':True,'battle_profile':{
                'boss_name':enemy,
                'enemy':{'hp_mult':1+.08*(wave-1),'damage_mult':.65+.025*(wave-1),'xp_mult':min(2.,1+.02*(wave-1))},
                'intro_lines':[tr('Dungeon+ · Welle {wave} · Bisheriger Rekord: {best} Siege',language,wave=wave,best=record['best_wave'])],
                'victory_lines':[tr('Die Tiefe öffnet den nächsten Kreis.',language)]}})
            if state['stats'].get('fights_won',0)<=before:
                record['last_result']='beendet';core.state.save();break
            record['last_wave']=wave;record['best_wave']=max(record['best_wave'],wave)
            record['total_wins']+=1;core.state.save();wave+=1
            if on_progress is not None:on_progress()
        narrate([tr('Dieser Durchlauf endet nach {waves} gewonnenen Wellen.',language,waves=record['last_wave']),
                 tr('Dein Rekord in Dungeon+ liegt bei {waves} Wellen.',language,waves=record['best_wave']),
                 tr('Maatis verlässt die Tiefe. Die gewonnenen Belohnungen bleiben bei ihm.',language)],None,{'name':tr('Dungeon+ · Rückkehr aus der Tiefe',language),'module':'dungeon_end'})
        return record['last_wave']
    except BaseException:
        record['last_result']='unterbrochen';core.state.save();raise
    finally:
        notify('audio',action='stop',owner='dungeon-plus')
        notify('dungeon_progress',active=False,id='plus',name='Dungeon+',room=0,total=None)
