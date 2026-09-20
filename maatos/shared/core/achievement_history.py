"""Remember newly observed unlocks; never invent dates for old saves."""
from datetime import datetime,timezone

def enrich(state,data,language='de'):
    rows={r['id']:dict(r,category=category) for category,group in data.get('groups',{}).items() for r in group if r['unlocked']}
    history=state.get('achievement_history')
    if history is None:
        # Existing achievements predate this tracker; their actual order is unknown.
        history={'seen':list(rows),'events':[]}
        state['achievement_history']=history
    seen=set(history['seen'])
    new=[key for key in rows if key not in seen]
    if new:
        now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        history['events'].extend({'id':key,'at':now} for key in new)
        history['seen'].extend(new)
    recent=[dict(rows[e['id']],at=e['at']) for e in reversed(history['events']) if e['id'] in rows][:5]
    from .achievement_i18n import tr
    return dict(data,recent=recent,history_note=tr('Neue Freischaltungen werden ab diesem Update erfasst. Für ältere Erfolge ist die Reihenfolge unbekannt.',language))
