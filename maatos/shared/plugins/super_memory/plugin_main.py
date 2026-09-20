"""One memory provider for terminal and desktop; no identity/person store."""
from uuid import uuid4
from shared.core.maat_paths import get_app_support_dir
from shared.core.super_memory import SuperMemory
from shared.core.memory_i18n import tr


class Plugin:
    type = 'chat'
    commands = {
        '/mem': {'de':'Super Memory: Übersicht.', 'en':'Super Memory overview.'},
        '/mem save': {'de':'Erinnerung speichern: /mem save <Text>.', 'en':'Save a memory.'},
        '/mem search': {'de':'Erinnerungen suchen.', 'en':'Search memories.'},
        '/mem recent': {'de':'Letzte Erinnerungen.', 'en':'Recent memories.'},
        '/mem timeline': {'de':'Zeitverlauf, optional Monat/Jahr.', 'en':'Memory timeline.'},
        '/mem milestones': {'de':'Meilensteine anzeigen.', 'en':'Show milestones.'},
        '/mem dream': {'de':'Erinnerungen zusammenfassen.', 'en':'Consolidate memories.'},
        '/mem archive': {'de':'Monatsarchive aktualisieren.', 'en':'Update monthly summaries.'},
        '/mem on': {'de':'Super Memory aktivieren.', 'en':'Enable Super Memory.'},
        '/mem off': {'de':'Super Memory deaktivieren.', 'en':'Disable Super Memory.'},
    }

    def __init__(self):
        self.store = None
        self.last_notice_turn = None

    def attach(self, context):
        if self.store is None:
            self.store = SuperMemory(get_app_support_dir(),maintenance=True,migrate=True)
        if isinstance(context,dict):context['super_memory']=self.store
        return self.store

    def on_startup(self, context=None):
        self.attach(context)

    def before_chat(self, user_input, context=None):
        if not isinstance(context,dict):return False,user_input
        try:
            store=self.attach(context)
            query=context.get('last_user_input',user_input) or ''
            context['super_memory_query']=query
            context['super_memory_turn']=uuid4().hex
            store.begin_turn(query,context)
            context.pop('super_memory_error',None)
        except Exception:
            context['super_memory_error']='Erinnerungsspeicher nicht verfügbar; der Chat kann weiterlaufen.'
            context.pop('super_memory',None)
            print(tr('🧠 Erinnerungsspeicher nicht verfügbar. Bitte im Erinnerungen-Tab erneut prüfen.'))
        return False,user_input

    def after_response(self, reply, context=None):
        if not isinstance(context,dict) or not context.get('super_memory'):return reply
        try:
            store=context['super_memory']
            turn=context.get('super_memory_turn','')
            clean=store.finish_turn(context.get('super_memory_query',''),reply or '',turn,runtime_context=context)
            if context.get('super_memory_error'):
                print('🧠 '+tr(context.pop('super_memory_error')))
            elif store.last_saved and store.settings['supermem_show_save_box'] and self.last_notice_turn!=turn:
                print(tr('\n🧠 {count} neue Erinnerung(en) gespeichert · Erinnerungen → Saves',count=store.last_saved))
                self.last_notice_turn=turn
            return clean
        except Exception:
            print(tr('🧠 Die neue Erinnerung konnte nicht gespeichert werden. Bitte im Erinnerungen-Tab erneut prüfen.'))
            return reply

    def command(self, cmd, context=None):
        parts=cmd.strip().split(maxsplit=2)
        if not parts or parts[0]!='/mem':return None
        try:
            store=self.attach(context)
            kind=parts[1] if len(parts)>1 else 'stats'
            text=parts[2] if len(parts)>2 else ''
            if kind=='save':
                store.save(text,runtime_context=context)
                return tr('🧠 Erinnerung gespeichert.')
            if kind in ('on','off'):
                store.configure(supermem_enabled=kind=='on')
                return tr('🧠 Super Memory aktiviert.' if kind=='on' else '🧠 Super Memory deaktiviert.')
            if kind in ('stats','info','recent','last','timeline','milestones','search','dream','archive'):
                return store.report({'last':'recent','info':'stats'}.get(kind,kind),text)
            return tr('/mem · save <Text> · search <Text> · recent · timeline · milestones · dream · archive · on/off\nLöschen: Erinnerungen → Saves.')
        except Exception:
            return tr('🧠 Speicheraktion fehlgeschlagen. Bitte erneut versuchen; Änderungen wurden nicht bestätigt.')
