"""Local clock snapshots, DE/EN, profile boundaries and existing chat pipeline."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
import test_ai_plugins as helpers
from shared.core.ai_plugin_settings import DEFAULTS, SNAPSHOT
from shared.core import maat_reality_layer as reality
from shared.core.thinking_mode import prepare_generation_messages
from shared.core.chat_history import ChatHistory
from shared.core.chat_turn import ChatTurn
from shared.plugins.maat_reality_layer.plugin_main import Plugin as Reality


NOW = datetime(2026, 9, 16, 14, 37, tzinfo=timezone(timedelta(hours=2), 'CEST'))


class RealityTests(unittest.TestCase):
    def test_local_clock_language_offset_and_unknown_activity(self):
        for lang, expected in [('de', ('Mittwoch', '16.09.2026', 'unbekannt')),
                               ('en', ('Wednesday', '2026-09-16', 'unknown'))]:
            block = reality.build_reality_block(language=lang, now=NOW)
            for value in (*expected, '14:37', 'UTC+02:00'):
                self.assertIn(value, block)
            self.assertLess(len(block), 1050)
        other = NOW.astimezone(timezone(timedelta(hours=-3, minutes=-30)))
        self.assertIn('UTC-03:30', reality.build_reality_block(now=other))
        self.assertIn('09:07', reality.build_reality_block(now=other))

    def test_relative_time_unknown_future_and_dst(self):
        self.assertEqual(reality.relative_time_text(NOW-timedelta(days=1), NOW, 'en'), 'about 1 day ago')
        self.assertEqual(reality.relative_time_text(NOW-timedelta(minutes=7), NOW), 'vor etwa 7 Minuten')
        for value in (None, 'not a date', NOW+timedelta(days=1)):
            block = reality.build_reality_block(value, language='en', now=NOW)
            self.assertIn('activity: unknown', block)
        from zoneinfo import ZoneInfo
        berlin = ZoneInfo('Europe/Berlin')
        before = datetime(2026, 3, 29, 1, 30, tzinfo=berlin)
        after = datetime(2026, 3, 29, 3, 30, tzinfo=berlin)
        self.assertEqual(reality.relative_time_text(before, after, 'en'), 'about 1 hour ago')

    def test_live_question_detection_does_not_hijack_historical_queries(self):
        for query in ('Wie viel Uhr ist es?', 'Wieviel Uhr ist es?', 'Wie spät ist es?', 'What time is it?',
                      'Welches Datum haben wir?', 'What day is it?', "What is today's date?"):
            self.assertTrue(reality.is_reality_question(query), query)
        for query in ('What time did Rome fall?', 'What did I say yesterday?', 'Wie geht es dir?'):
            self.assertFalse(reality.is_reality_question(query), query)

    def test_fresh_snapshot_replaces_old_time_without_changing_chat(self):
        pm = helpers.manager()
        context = {'pm': pm, SNAPSHOT: dict(DEFAULTS), 'memory_perspective': 'companion'}
        messages = [{'role': 'system', 'content': 'You play Maatis.'}, {'role':'user','content':'What time is it?'}]
        with patch.object(reality, 'now_local', return_value=NOW), \
             patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
            first = prepare_generation_messages(messages, language='en', runtime_context=context)
        self.assertEqual(len(messages), 2)
        self.assertNotIn('_ai_generation_state', context)
        with patch.object(reality, 'now_local', return_value=NOW+timedelta(days=1, minutes=1)), \
             patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
            second = prepare_generation_messages(first, language='en', runtime_context=context)
        self.assertEqual(str(second).count('[MAAT_REALITY]'), 1)
        self.assertIn('Thursday, 2026-09-17, 14:38', str(second))
        self.assertNotIn('14:37', str(second))
        context[SNAPSHOT]['reality_enabled'] = False
        disabled = prepare_generation_messages(second, language='en', runtime_context=context)
        self.assertNotIn('[MAAT_REALITY]', str(disabled))

    def test_disabled_plugin_never_reads_clock_or_archive_and_locked_archive_is_optional(self):
        archive = Mock(side_effect=sqlite3.OperationalError('locked'))
        context = {SNAPSHOT: dict(DEFAULTS, reality_enabled=False), 'reality_last_activity':archive}
        plugin = Reality()
        with patch.object(reality, 'now_local') as clock:
            self.assertEqual(plugin.generation_prompt('en',context),'')
            clock.assert_not_called();archive.assert_not_called()
        context[SNAPSHOT]['reality_enabled'] = True
        with patch.object(reality, 'now_local', return_value=NOW):
            self.assertIn('activity: unknown',plugin.generation_prompt('en',context))

    def test_explicit_reply_language_applies_to_reality_prompt(self):
        context = {'pm': helpers.manager(), SNAPSHOT:dict(DEFAULTS)}
        with patch.object(reality,'now_local',return_value=NOW):
            messages = prepare_generation_messages([{'role':'user','content':'Bitte auf Deutsch: Wie spät ist es?'}],
                                                   language='en',runtime_context=context)
        clock = next(m['content'] for m in messages if m['content'].startswith('[MAAT_REALITY]'))
        self.assertIn('Mittwoch',clock)
        self.assertNotIn('Wednesday',clock)

    def test_previous_activity_is_profile_local_and_respects_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = ChatHistory(Path(folder)/'one')
            other = ChatHistory(Path(folder)/'two')
            self.assertIsNone(archive.last_activity())
            old = archive.append('user','Private words',timestamp=(NOW-timedelta(days=1)).isoformat())
            latest = archive.append('assistant','Private reply',timestamp=(NOW-timedelta(minutes=5)).isoformat())
            context = {SNAPSHOT:dict(DEFAULTS), 'reality_last_activity':archive.last_activity}
            with patch.object(reality, 'now_local',return_value=NOW):
                block = Reality().generation_prompt('en',context)
                self.assertIn('about 5 minutes ago',block)
                self.assertNotIn('Private',block)
                archive.delete_message(latest)
                self.assertIn('about 1 day ago',Reality().generation_prompt('en',context))
                archive.delete_message(old)
                self.assertIn('activity: unknown',Reality().generation_prompt('en',context))
            self.assertIsNone(other.last_activity())

    def test_current_or_cancelled_turn_is_not_previous_activity(self):
        from gui import game_worker as worker
        with tempfile.TemporaryDirectory() as folder, patch.object(worker,'emit'):
            runtime = worker.Runtime.__new__(worker.Runtime)
            runtime.chat_history = ChatHistory(folder)
            runtime.chat_history.append('assistant','Earlier',timestamp=(NOW-timedelta(hours=1)).isoformat())
            prior = runtime.last_chat_activity()
            runtime.context = {'gui_chat_turn':ChatTurn('one')}
            runtime.archive_chat('user','New message')
            self.assertEqual(runtime.last_chat_activity(),prior)
            runtime.context['gui_chat_turn'].cancel()
            self.assertEqual(runtime.last_chat_activity(),prior)
            runtime.context['gui_chat_turn'] = ChatTurn('two')
            runtime.archive_chat('user','Completed message')
            runtime.context['gui_chat_turn'].commit()
            self.assertNotEqual(runtime.last_chat_activity(),prior)


class RealityStreamingTests(unittest.TestCase):
    setUp = helpers.PluginTests.setUp
    stream = helpers.PluginTests.stream

    def test_live_clock_is_grounding_for_antihallu(self):
        self.settings['hallu_mode'] = True
        for language, query, reply in [('de','Wie viel Uhr ist es?','Es ist 14:37 Uhr.'),
                                        ('en','What time is it?','It is 14:37.'),
                                        ('de','Welches Datum ist heute?','Heute ist Mittwoch, der 16.09.2026.'),
                                        ('en','What is the current date?','Today is Wednesday, 2026-09-16.')]:
            with patch.object(reality,'now_local',return_value=NOW), \
                 patch('shared.core.offline_wiki.generation_context',return_value='[MAAT-OFFLINE-WIKI] '+
                       ' '.join(f'unrelated{i}' for i in range(250))):
                result = self.stream(query,reply,language=language)
            self.assertTrue(result.endswith(reply),result)
            self.assertIn('14:37',self.context['_ai_generation_state']['grounding']['text'])


if __name__ == '__main__':
    unittest.main()
