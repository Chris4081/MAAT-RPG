import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_desktop import APP
from gui.game_worker import Runtime

class MaatisOpeningTests(unittest.TestCase):
    def runtime(self, played):
        story=SimpleNamespace(plugin_id='story_loader', state={'played':list(played),'messages_total':9},
            config={'stories':[{'id':1,'module':'story1','music':'story1_theme.mp3'}]},
            _save_state=Mock(), _load_story_module=Mock(return_value=object()),
            _run_story_interactive=Mock(), _play_story_entry=Mock())
        r=Runtime.__new__(Runtime)
        r.pm=SimpleNamespace(iter_all_plugins=lambda:[story])
        r.context={}
        return r,story

    def test_existing_story_replays_only_presentation_once(self):
        r,story=self.runtime([1,2])
        r.ensure_maatis_chat_opening()
        story._run_story_interactive.assert_called_once()
        story._play_story_entry.assert_not_called()
        self.assertEqual(story.state['played'],[1,2])
        self.assertEqual(story.state['messages_total'],9)
        self.assertTrue(story.state['gui_first_chat_opening_seen'])
        r.ensure_maatis_chat_opening()
        story._run_story_interactive.assert_called_once()
        story._save_state.assert_called_once()

    def test_new_game_uses_original_story(self):
        r,story=self.runtime([])
        r.ensure_maatis_chat_opening()
        story._play_story_entry.assert_called_once_with(story.config['stories'][0],r.context)
        story._run_story_interactive.assert_not_called()

    def test_opening_precedes_intercepting_chat_plugin(self):
        r,story=self.runtime([1])
        r.llm=object()
        r.boot=SimpleNamespace(conversation=[])
        r.pm.handle_before_chat=Mock(return_value=(True,'Hinweis'))
        order=[]
        story._run_story_interactive.side_effect=lambda *a,**k:order.append('story')
        r.pm.handle_before_chat.side_effect=lambda *a:(order.append('hook') or (True,'Hinweis'))
        with patch.object(r,'select_story_campaign'),patch('builtins.print'):
            r.text('Hallo!')
        self.assertEqual(order,['story','hook'])
