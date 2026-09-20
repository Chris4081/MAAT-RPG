"""Real calendar windows and dated save recall, with a frozen reference date."""
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
from test_desktop import APP
from shared.core.memory_dates import parse_time_query
from shared.core.super_memory import SuperMemory,MARKER
from shared.core.thinking_mode import prepare_generation_messages

NOW=datetime(2026,9,10,12)


class CalendarQueryTests(unittest.TestCase):
    def period(self,text,now=NOW):
        w=parse_time_query(text,now=now)
        self.assertIsNotNone(w,text); self.assertNotIn('error',w,text)
        return (datetime.fromtimestamp(w['start']).strftime('%Y-%m-%d'),
                datetime.fromtimestamp(w['end']).strftime('%Y-%m-%d'))

    def test_german_and_english_days_and_explicit_dates(self):
        groups=[(('Was habe ich gestern gesagt?','What did I say yesterday?'),'2026-09-09','2026-09-10'),
                (('vorgestern','vorgesterb','Was habe ich vorgestern geschrieben?','the day before yesterday'),'2026-09-08','2026-09-09'),
                (('heute','What did we discuss today?'),'2026-09-10','2026-09-11'),
                (('am 15.06.2026','Was habe ich am 15. Juni 2026 gesagt?','on June 15, 2026','on 15 June 2026',
                  'on the 15th of June 2026','on 2026-06-15','on 06/15/2026','on 15/06/2026','am 15.06.26'),
                 '2026-06-15','2026-06-16')]
        for phrases,first,last in groups:
            for phrase in phrases:
                with self.subTest(phrase=phrase):self.assertEqual(self.period(phrase),(first,last))

    def test_relative_days_weeks_months_years(self):
        for phrases,first,last in [
            (('vor drei Tagen','three days ago'),'2026-09-07','2026-09-08'),
            (('vor zwei Wochen','two weeks ago'),'2026-08-27','2026-08-28'),
            (('vor zwei Wochen und drei Tagen','two weeks and three days ago'),'2026-08-24','2026-08-25'),
            (('vor einem Monat','a month ago','one month ago'),'2026-08-10','2026-08-11'),
            (('vor zwei Monaten','two months ago'),'2026-07-10','2026-07-11'),
            (('vor einundzwanzig Tagen','twenty-one days ago','twenty one days ago'),'2026-08-20','2026-08-21')]:
            for phrase in phrases:
                with self.subTest(phrase=phrase):self.assertEqual(self.period(phrase),(first,last))
        # Calendar years, including leap-day clamping; independent of today's year.
        for phrase in ('vor einem Jahr','a year ago','one year ago'):
            self.assertEqual(self.period(phrase,datetime(2028,2,29)),('2027-02-28','2027-03-01'))
        for phrase in ('vor einem Monat','a month ago'):
            self.assertEqual(self.period(phrase,datetime(2026,3,31)),('2026-02-28','2026-03-01'))

    def test_whole_periods_and_since(self):
        for phrases,first,last in [
            (('letzte Woche','in der letzten Woche','last week'),'2026-08-31','2026-09-07'),
            (('letzten Monat','im letzten Monat','last month','previous month'),'2026-08-01','2026-09-01'),
            (('diesen Monat','this month'),'2026-09-01','2026-09-11'),
            (('im Juni 2026','in June 2026'),'2026-06-01','2026-07-01'),
            (('seit Juni 2026','since June 2026'),'2026-06-01','2026-09-11'),
            (('seit 15.06.2026','since 2026-06-15'),'2026-06-15','2026-09-11'),
            (('die letzten drei Tage','the past three days'),'2026-09-07','2026-09-11'),
            (('in 2026','im Jahr 2026'),'2026-01-01','2027-01-01')]:
            for phrase in phrases:
                with self.subTest(phrase=phrase):self.assertEqual(self.period(phrase),(first,last))
        for phrase in ('letztes Jahr','last year'):
            self.assertEqual(self.period(phrase,datetime(2027,9,10)),('2026-01-01','2027-01-01'))

    def test_dst_boundaries_and_midnight(self):
        berlin=ZoneInfo('Europe/Berlin')
        for now,hours in [(datetime(2026,3,30,tzinfo=berlin),23),(datetime(2026,10,26,tzinfo=berlin),25)]:
            w=parse_time_query('yesterday',now=now)
            self.assertEqual(w['end']-w['start'],hours*3600)
            self.assertEqual(datetime.fromtimestamp(w['start'],berlin).hour,0)
            self.assertEqual(datetime.fromtimestamp(w['end'],berlin).hour,0)
        self.assertEqual(self.period('gestern',datetime(2026,9,10,0,0,1)),('2026-09-09','2026-09-10'))

    def test_invalid_ambiguous_dates_and_non_temporal_text(self):
        for phrase in ('am 31.02.2026','on 2026-13-01','on 02/03/2026','vor 9999 Jahren','since 2030'):
            with self.subTest(phrase=phrase):self.assertIn('error',parse_time_query(phrase,now=NOW))
        for phrase in ('May I ask a question?','Welche Projekte kennst du?','Ich nutze Python 3.11','hello'):
            self.assertIsNone(parse_time_query(phrase,now=NOW),phrase)
        w=parse_time_query('about a month ago',now=NOW)
        self.assertTrue(w['approximate'])
        self.assertEqual(w['end']-w['start'],7*86400)


class DatedRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.s=SuperMemory(self.root)
        self.clock=patch('shared.core.super_memory.time.time',return_value=NOW.timestamp()); self.clock.start(); self.addCleanup(self.clock.stop)

    def save(self,text,stamp,role='user',priority=.65):
        with patch('shared.core.super_memory.time.time',return_value=datetime.fromisoformat(stamp).timestamp()):
            self.s.save(text,role=role,priority=priority)

    def test_exact_date_keeps_other_days_and_summaries_out(self):
        self.save('JUN15: Mein Fahrradprojekt wurde begonnen.','2026-06-15T12:00:00')
        self.save('JUN14: Nicht vom angefragten Tag.','2026-06-14T12:00:00',priority=1)
        self.save('JUN16: Nicht vom angefragten Tag.','2026-06-16T12:00:00',priority=1)
        self.s.report('archive')
        self.s.engine._add_working('user','JUNNOW: Was habe ich am 15.06.2026 gesagt?')
        for query in ('Was habe ich am 15.06.2026 gesagt?','What did I say on June 15, 2026?','What did I say on 2026-06-15?'):
            block=self.s.generation_context(query,{'chat_state':{'architecture':'llama'}})
            self.assertIn('JUN15',block)
            for wrong in ('JUN14','JUN16','JUNNOW','Kernpunkte'):self.assertNotIn(wrong,block)
            self.assertEqual(len(self.s.last_recall),1)
        self.assertIn('user note',block)
        self.assertIn('2026-06-15',block)

    def test_missing_invalid_disabled_and_deleted_never_fall_back(self):
        self.save('NEIGHBOR: Ein Save am Vortag.','2026-09-08T12:00:00')
        for query,expected in [('Was sagte ich gestern?','keine gespeicherten'),('What did I say yesterday?','No saved memories'),
                               ('on 31.02.2026','invalid'),('on 06/07/2026','ambiguous')]:
            block=self.s.generation_context(query)
            self.assertIn(expected,block); self.assertNotIn('NEIGHBOR',block); self.assertEqual(self.s.last_recall,[])
        self.s.configure(supermem_autorecall=False)
        self.assertIn('disabled',self.s.generation_context('What did I say yesterday?'))
        self.s.configure(supermem_autorecall=True)
        self.s.delete([r['id'] for r in self.s.entries()])
        self.assertIn('No saved memories',self.s.generation_context('the day before yesterday'))

    def test_old_ledger_entries_remain_retrievable_after_hot_index_pruning(self):
        self.save('ANCIENT: Mein Projekt begann an diesem Datum.','2026-01-15T13:00:00')
        with self.s.operation() as db:
            db.execute('DELETE FROM episodic'); db.execute('DELETE FROM semantic'); db.execute('DELETE FROM keyword_memory')
        self.assertIn('ANCIENT',self.s.generation_context('What did I say on January 15, 2026?'))

    def test_user_notes_prioritized_caps_and_partial_source_labels(self):
        for i in range(8):self.save(f'USER{i}: Eine Aufgabe für das Projekt.','2026-09-09T12:00:00')
        self.save('AI: Modellnotiz mit höchster Priorität.','2026-09-09T13:00:00','assistant',1)
        for arch,cap in [('llama',3),('qwen3',5),('gemma4',5),('llama',3)]:
            block=self.s.generation_context('What did I say yesterday?',{'chat_state':{'architecture':arch}})
            self.assertEqual(len(self.s.last_recall),cap)
            self.assertNotIn('AI:',block); self.assertIn(f'{cap} of 9',block)
            self.assertLess(len(block),3000 if cap==5 else 1700)
        block=self.s.generation_context('What did you say yesterday?')
        self.assertIn('AI note',block)

    def test_calendar_followups_expire_and_clear_with_profile_and_deletion(self):
        self.s.generation_context('vor einem Monat')
        self.s.generation_context('und vor zwei?')
        self.assertEqual(self.s.last_time_query['label'],'10.07.2026')
        self.s.generation_context('one year ago')
        self.s.generation_context('and two ago?')
        self.assertEqual(datetime.fromtimestamp(self.s.last_time_query['start']).year,2024)
        with patch('shared.core.super_memory.time.time',return_value=NOW.timestamp()+901):
            self.assertIsNone(self.s.time_query('and three ago?'))
        self.assertIsNone(SuperMemory(self.root/'other').time_query('und vor zwei?'))
        self.s.clear_cache(); self.assertIsNone(self.s.time_query('und vor zwei?'))

    def test_generation_route_uses_english_date_context_without_changing_input(self):
        self.save('SOURCE: The new design uses dark blue.','2026-09-09T20:00:00')
        query='What did I say yesterday?'
        messages=[{'role':'system','content':'You are MAAT.'},{'role':'user','content':query}]
        ctx={'super_memory':self.s,'super_memory_query':query}
        with patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
            prepared=prepare_generation_messages(messages,runtime_context=ctx,llm={'chat_state':{'architecture':'llama'}})
        block=next(m['content'] for m in prepared if m['content'].startswith(MARKER))
        self.assertIn('Requested period: 2026-09-09',block); self.assertIn('SOURCE:',block)
        self.assertEqual(messages,[{'role':'system','content':'You are MAAT.'},{'role':'user','content':query}])
        self.assertIn('SOURCE:',self.s.report('search',query))


if __name__=='__main__':unittest.main()
