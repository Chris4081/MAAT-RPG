"""Offline German/English calendar expressions for dated memory recall.

Intervals are half-open in local civil time, including across DST. Months and
years use calendar arithmetic, not fixed 30/365-day offsets. No fuzzy day fallback
unless the question explicitly says approximately/about/around.
"""
import calendar
from datetime import datetime, timedelta
import re


def fold(text):
    return ' '.join(str(text).casefold().translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','ß':'ss'})).split())


MONTHS = {}
for i,names in enumerate((
    'januar january jan', 'februar february feb', 'maerz march mar', 'april apr',
    'mai may', 'juni june jun', 'juli july jul', 'august aug', 'september sep sept',
    'oktober october okt oct', 'november nov', 'dezember december dez dec'),1):
    MONTHS.update({name:i for name in names.split()})
MONTH_PATTERN='(?:'+'|'.join(sorted(MONTHS,key=len,reverse=True))+')'
NUMBERS={'null':0,'zero':0,'ein':1,'eine':1,'einen':1,'einem':1,'einer':1,'eins':1,'one':1,'a':1,'an':1}
for i,names in enumerate(('zwei two','drei three','vier four','fuenf five','sechs six','sieben seven','acht eight',
                          'neun nine','zehn ten','elf eleven','zwoelf twelve','dreizehn thirteen','vierzehn fourteen',
                          'fuenfzehn fifteen','sechzehn sixteen','siebzehn seventeen','achtzehn eighteen','neunzehn nineteen'),2):
    NUMBERS.update({n:i for n in names.split()})
for tens,de,en in ((20,'zwanzig','twenty'),(30,'dreissig','thirty'),(40,'vierzig','forty'),(50,'fuenfzig','fifty'),
                   (60,'sechzig','sixty'),(70,'siebzig','seventy'),(80,'achtzig','eighty'),(90,'neunzig','ninety')):
    NUMBERS[de]=NUMBERS[en]=tens
    for n,unit_de,unit_en in ((1,'ein','one'),(2,'zwei','two'),(3,'drei','three'),(4,'vier','four'),(5,'fuenf','five'),
                              (6,'sechs','six'),(7,'sieben','seven'),(8,'acht','eight'),(9,'neun','nine')):
        NUMBERS[unit_de+'und'+de]=tens+n
        NUMBERS[en+'-'+unit_en]=NUMBERS[en+' '+unit_en]=tens+n
NUMBER=r'(?:\d{1,4}|'+'|'.join(re.escape(n) for n in sorted(NUMBERS,key=len,reverse=True))+')'
UNIT=r'(?:tagen|tage|tag|wochen|woche|monaten|monate|monat|jahren|jahre|jahr|days?|weeks?|months?|years?)'


def language(text):
    return 'en' if re.search(r"\b(what|when|remember|yesterday|today|ago|earlier|last|previous|past|since|during|on|did|wrote|said|we|our|"
                            r"january|february|march|may|june|july|october|december)\b",fold(text)) else 'de'


def shift_months(day, delta):
    month_number=day.year*12+day.month-1+delta
    year,month=divmod(month_number,12); month+=1
    return day.replace(year=year,month=month,day=min(day.day,calendar.monthrange(year,month)[1]))


def unit_name(text):
    if text.startswith(('tag','day')):return 'day'
    if text.startswith(('woch','week')):return 'week'
    if text.startswith(('monat','month')):return 'month'
    return 'year'


def parse_time_query(query, *, now=None, previous_unit=''):
    text=fold(query)
    text=re.sub(r'\bvorgester[bmn]\b','vorgestern',text)
    today=(now or datetime.now()).replace(hour=0,minute=0,second=0,microsecond=0)
    tomorrow=today+timedelta(days=1)
    lang=language(text)

    def error(code):return {'language':lang,'error':code,'kind':'invalid'}
    def window(start,end,kind='day',unit='day',approximate=False):
        if end<=start:return error('invalid_range')
        fmt='%Y-%m-%d' if lang=='en' else '%d.%m.%Y'
        first=start.strftime(fmt); last=(end-timedelta(days=1)).strftime(fmt)
        return dict(start=start.timestamp(),end=end.timestamp(),label=first if first==last else first+' – '+last,
                    kind=kind,unit=unit,language=lang,approximate=approximate)
    def exact(year,month,day,match):
        try:start=today.replace(year=int(year),month=int(month),day=int(day))
        except (ValueError,OverflowError):return error('invalid_date')
        # "since" / "seit" includes the named start date up to today.
        since=re.search(r'\b(?:since|seit)\s*$',text[:match.start()])
        return window(start,tomorrow if since else start+timedelta(days=1),'since' if since else 'day')

    # Full ISO must precede D/M/Y so its trailing month/day is not reinterpreted.
    m=re.search(r'(?<![\d./-])(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?![\d./-])',text)
    if m:return exact(*m.groups(),m)
    m=re.search(r'(?<![\d./-])(\d{1,2})([./-])(\d{1,2})\2(\d{2}|\d{4})(?![\d./-])',text)
    if m:
        day,sep,month,year=m.groups(); day,month,year=int(day),int(month),int(year)
        if year<100:year+=2000 if year<70 else 1900
        if sep=='/' and lang=='en':
            if day<=12 and month<=12 and day!=month:return error('ambiguous_date')
            if month>12:day,month=month,day
        return exact(year,month,day,m)
    m=re.search(rf'\b(\d{{1,2}})(?:st|nd|rd|th|\.)?\s+(?:of\s+)?({MONTH_PATTERN})\.?(?:,?\s+(\d{{4}}))?\b',text)
    if m:return exact(m.group(3) or today.year,MONTHS[m.group(2)],m.group(1),m)
    m=re.search(rf'\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b',text)
    if m:return exact(m.group(3) or today.year,MONTHS[m.group(1)],m.group(2),m)
    m=re.search(r'\b(?:am|on|vom)\s+(\d{1,2})\.(\d{1,2})\.?(?!\d)',text)
    if m:return exact(today.year,m.group(2),m.group(1),m)

    for pattern,offset in ((r'\bvorgestern\b|\b(?:the )?day before yesterday\b',2),
                           (r'\bgestern\b|\byesterday\b',1),(r'\bheute\b|\btoday\b',0)):
        if re.search(pattern,text):
            start=today-timedelta(days=offset)
            return window(start,start+timedelta(days=1))

    # Compound units before simple units: "two weeks and three days ago".
    patterns=(rf'\bvor\s+({NUMBER})\s+({UNIT})(?:\s+und\s+({NUMBER})\s+(?:tagen|tage|tag))?\b',
              rf'\b({NUMBER})\s+({UNIT})(?:\s+and\s+({NUMBER})\s+days?)?\s+(?:ago|earlier)\b')
    for pattern in patterns:
        m=re.search(pattern,text)
        if m:
            count=NUMBERS.get(m.group(1),int(m.group(1)) if m.group(1).isdigit() else 1)
            unit=unit_name(m.group(2)); rest=m.group(3) or '0'
            rest=NUMBERS.get(rest,int(rest) if rest.isdigit() else 0)
            try:
                if unit=='day':start=today-timedelta(days=count)
                elif unit=='week':start=today-timedelta(weeks=count,days=rest)
                else:start=shift_months(today,-count*(12 if unit=='year' else 1))-timedelta(days=rest)
                approx=bool(re.search(r'\b(ungefaehr|etwa|circa|ca\.?|about|around|approximately|roughly)\b',text))
                radius={'day':1,'week':2,'month':3,'year':14}[unit] if approx else 0
                return window(start-timedelta(days=radius),start+timedelta(days=radius+1),unit=unit,approximate=approx)
            except (ValueError,OverflowError):return error('invalid_range')

    # Last calendar period differs from a relative date one period ago.
    m=re.search(r'\b(letzt(?:e|en|er|es)|vergangen(?:e|en|er|es)|last|previous|dies(?:e|en|er|es)|this)\s+('+UNIT+r')\b',text)
    if m:
        unit=unit_name(m.group(2)); current=m.group(1).startswith(('dies','this'))
        if unit=='day':start=today if current else today-timedelta(days=1); end=start+timedelta(days=1)
        elif unit=='week':
            this=today-timedelta(days=today.weekday()); start=this if current else this-timedelta(days=7); end=tomorrow if current else this
        elif unit=='month':
            this=today.replace(day=1); start=this if current else shift_months(this,-1); end=tomorrow if current else this
        else:
            this=today.replace(month=1,day=1); start=this if current else this.replace(year=this.year-1); end=tomorrow if current else this
        return window(start,end,unit,unit)

    m=re.search(rf'\b(?:letzte[nr]?|vergangene[nr]?|last|past)\s+({NUMBER})\s+({UNIT})\b',text)
    if m:
        n=NUMBERS.get(m.group(1),int(m.group(1)) if m.group(1).isdigit() else 1); unit=unit_name(m.group(2))
        try:
            start=shift_months(today,-n*(12 if unit=='year' else 1)) if unit in ('month','year') else today-timedelta(days=n*(7 if unit=='week' else 1))
            return window(start,tomorrow,'range',unit)
        except (ValueError,OverflowError):return error('invalid_range')

    m=re.search(rf'\b({MONTH_PATTERN})(?:\s+(\d{{4}}))?\b',text)
    if m:
        year=int(m.group(2) or today.year); month=MONTHS[m.group(1)]
        # Avoid treating English "may" in ordinary sentences as a month.
        if not m.group(2) and not re.search(r'\b(?:im|in|seit|since|during|from)\s*$',text[:m.start()]):return None
        try:start=today.replace(year=year,month=month,day=1)
        except ValueError:return error('invalid_date')
        since=bool(re.search(r'\b(?:since|seit)\s*$',text[:m.start()]))
        return window(start,tomorrow if since else shift_months(start,1),'since' if since else 'month','month')
    m=re.search(r'\b(?:im|in|seit|since|during)\s+(?:(?:jahr|year)\s+)?(\d{4})\b',text)
    if m:
        try:start=today.replace(year=int(m.group(1)),month=1,day=1); end=start.replace(year=start.year+1)
        except ValueError:return error('invalid_date')
        since=m.group(0).startswith(('seit','since'))
        return window(start,tomorrow if since else end,'since' if since else 'year','year')

    # The established unit is session-local, expires in the adapter and is never
    # interpreted as a name or a user profile.
    m=re.fullmatch(rf'(?:und\s+)?vor\s+({NUMBER})\s*\??|(?:and\s+)?({NUMBER})\s+(?:ago|earlier)\s*\??',text)
    if m and previous_unit in ('day','week','month','year'):
        n=m.group(1) or m.group(2)
        translated=f'{n} {previous_unit}s ago' if lang=='en' else f'vor {n} '+{'day':'Tagen','week':'Wochen','month':'Monaten','year':'Jahren'}[previous_unit]
        return parse_time_query(translated,now=now)
    return None
