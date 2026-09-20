"""Verify only the average of an unambiguous five-rating MAAT assessment."""
from decimal import Decimal
import re
from .maat_reference import assessment_requested
from .wiki_maat_query import VALUE

_NAMES = {
    'harmonie':'h','harmony':'h','balance':'b',
    'schöpfungskraft':'s','schoepfungskraft':'s','creative power':'s','creativity':'s',
    'verbundenheit':'v','connection':'v','connectedness':'v','respekt':'r','respect':'r',
}
_LABEL = re.compile(r'\b('+ '|'.join(re.escape(name) for name in _NAMES)+r')\b\s*\*{0,2}\s*[:|]\s*\*{0,2}',re.I)
_SCORE = re.compile(r'(?<![\d.,+−-])(\d{1,2}(?:[.,]\d{1,4})?)\s*(von|out\s+of|/)\s*10(?!\d)',re.I)
_TOTAL = re.compile(VALUE+r'\s*\*{0,2}\s*:\s*\*{0,2}[ \t]*',re.I)


def context_messages(context):
    context = context or {}
    messages = list(context.get('conversation') or [])
    query = context.get('last_user_input') or context.get('super_memory_query')
    last = next((m.get('content') for m in reversed(messages) if m.get('role')=='user'),None)
    if query and query != last:
        messages.append({'role':'user','content':query})
    return messages


def correct_average(reply, messages):
    if not isinstance(reply,str) or not assessment_requested(messages) or '```' in reply:
        return reply
    labels, totals = list(_LABEL.finditer(reply)), list(_TOTAL.finditer(reply))
    # Missing/duplicate ratings, comparisons and advanced formulas are left
    # alone. Never generate a subjective rating that the model did not supply.
    if len(labels)!=5 or len(totals)!=1 or totals[0].start() <= labels[-1].end():
        return reply
    values = {}
    total = totals[0]
    for index,label in enumerate(labels):
        end = labels[index+1].start() if index<4 else total.start()
        scores = list(_SCORE.finditer(reply[label.end():end]))
        key = _NAMES.get(label[1].casefold())
        if key is None or len(scores)!=1 or key in values:
            return reply
        number = Decimal(scores[0][1].replace(',','.'))
        if not 0<=number<=10:
            return reply
        values[key] = number
    end = reply.find('\n',total.end())
    end = len(reply) if end<0 else end
    final_scores = list(_SCORE.finditer(reply,total.end(),end))
    if len(final_scores)!=1:
        return reply
    score = final_scores[0]
    german = score[2].casefold()=='von' or bool(re.search(r'wert|bewertung',total[0],re.I))
    def number(value):
        text = format(value.normalize(),'f')
        return text.replace('.',',') if german else text
    ordered = [values[key] for key in 'hbsvr']
    average = sum(ordered)/5
    calculation = '('+'+'.join(number(v) for v in ordered)+')/5 = '+number(average)
    calculation += ' von 10' if german else ' out of 10'
    stop = score.end()
    rounding = re.match(r'\s*\((?:rounded|rounding|gerundet|aufgerundet)[^\n)]*\)',reply[stop:],re.I)
    if rounding:
        stop += rounding.end()
    return reply[:total.end()]+calculation+reply[stop:]
