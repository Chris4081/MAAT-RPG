"""A post-stream plugin edit revises the same reply, including queued UI text."""
from contextlib import nullcontext, redirect_stdout
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser
from gui.chat_response import ChatResponse
from gui.text_stream import TextStream
from shared.plugins.anti_repeat.plugin_main import Plugin as AntiRepeat


class ChatResponseTests(unittest.TestCase):
    def test_revisions_preserve_other_text_with_queued_boundaries(self):
        original = '🤖 Hallo Maatis!\nGemeinsam nach Terra.\nGemeinsam nach Terra.'
        for finish in (True, False):
            for revised in (AntiRepeat().after_response(original), original+'\nEin neuer Hinweis.',
                            'Neue Einleitung:\n'+original):
                with self.subTest(finish=finish, revised=revised):
                    views = [QTextBrowser(), QTextBrowser()]
                    editor, stream = ChatResponse(views), TextStream()
                    def append(text):
                        for view in views:
                            cursor = QTextCursor(view.document())
                            cursor.movePosition(QTextCursor.End);cursor.insertText(text)
                    stream.chunk.connect(append)
                    stream.append('Alte Nachricht und Story.\n')
                    stream.mark(lambda: editor.handle(dict(action='begin',id='one')))
                    stream.append('\n'+original+'\n\n')
                    stream.mark(lambda: editor.handle(dict(action='end',id='one')))
                    stream.append('Quest erfüllt: +10 XP.\n')
                    stream.mark(lambda: editor.handle(dict(action='replace',id='one',original=original,text=revised)))
                    stream.append('Du · nächste Frage')
                    stream.timer.stop()
                    if finish:stream.finish()
                    else:
                        while stream.running:stream.advance()
                    for view in views:
                        self.assertEqual(view.toPlainText(),'Alte Nachricht und Story.\n\n'+revised+'\n\nQuest erfüllt: +10 XP.\nDu · nächste Frage')
                        view.close();view.deleteLater()

    def test_cancel_clear_and_stale_replacement_never_replay_text(self):
        view=QTextBrowser();editor=ChatResponse([view]);stream=TextStream()
        stream.append('cancelled');callback=Mock();stream.mark(callback);stream.clear();stream.finish()
        callback.assert_not_called()
        editor.handle(dict(action='begin',id='one'))
        view.insertPlainText('An old reply')
        editor.handle(dict(action='end',id='one'))
        view.clear();view.setPlainText('A different conversation')
        editor.handle(dict(action='replace',id='one',original='An old reply',text='Must not appear'))
        self.assertEqual(view.toPlainText(),'A different conversation')
        editor.handle(dict(action='replace',id='stale',original='conversation',text='Must not appear'))
        self.assertEqual(view.toPlainText(),'A different conversation')
        view.close();view.deleteLater()

    def test_worker_emits_revision_instead_of_reprinting_for_both_adapters(self):
        from gui import game_worker as worker
        from shared.core import streaming
        text='Hallo Maatis!\nDer Weg ist offen.\nDer Weg ist offen.'
        revised=AntiRepeat().after_response(text)
        for backend in ('llama', 'llama_intel'):
            r=worker.Runtime.__new__(worker.Runtime)
            r.boot=SimpleNamespace(conversation=[{'role':'system','content':'MAAT-RPG'}])
            r.llm={'backend':backend};r.perf={'gui_mode':True};r.context={};r.language='de'
            for name in ('archive_chat','select_story_campaign','ensure_maatis_chat_opening','restore_chat_prompt','complete_chat_turn'):
                setattr(r,name,Mock())
            r.game_event_output=nullcontext
            r.pm=Mock()
            r.pm.handle_before_chat.return_value=(False,None)
            r.pm.has_before_final_response.return_value=False
            r.pm.get_streaming_plugins.return_value=[]
            r.pm.handle_after_response.side_effect=lambda reply,context:AntiRepeat().after_response(reply)
            r.pm.generation_system_messages.return_value=[]
            output=io.StringIO()
            with patch.object(streaming,'backend_stream_chat',return_value=iter([text])) as native, \
                 patch.object(worker,'emit') as emit, redirect_stdout(output):
                r.text('Hallo')
            native.assert_called_once()
            self.assertEqual(output.getvalue().count('Hallo Maatis!'),1)
            actions=[c.kwargs['action'] for c in emit.call_args_list if c.args[0]=='chat_response']
            self.assertEqual(actions,['begin','end','replace'])
            final=next(c.kwargs for c in emit.call_args_list if c.kwargs.get('action')=='replace')
            self.assertEqual((final['original'],final['text']),(text,revised))
            self.assertEqual(r.boot.conversation[-1],{'role':'assistant','content':revised})

    def test_delta_tokens_preserve_numbers_whitespace_and_markdown(self):
        from shared.core import streaming
        chunks=['1','0','0',' ',' ','*','*','x','*','*']
        for backend in ('llama','llama_intel'):
            with patch.object(streaming,'backend_stream_chat',return_value=iter(chunks)), \
                 patch.object(streaming,'key_pressed',return_value=False),redirect_stdout(io.StringIO()):
                result=''.join(streaming.stream_chat_completion({'backend':backend},[],{'gui_mode':True}))
            self.assertEqual(result,'100  **x**')

    def test_companion_postprocessing_does_not_replay_its_stream(self):
        from gui import game_worker as worker
        r=worker.Runtime.__new__(worker.Runtime)
        r.complete_chat_turn=Mock();r.game_event_output=nullcontext;r.context={}
        r._companion_response_id='companion';r.pm=Mock()
        original='Eine Frage?\nEine Frage?'
        r.pm.handle_after_response.return_value='Eine Frage?'
        output=io.StringIO()
        with patch.object(worker,'emit') as emit,redirect_stdout(output):
            r.companion_after_response(original)
        self.assertEqual(output.getvalue(),'')
        emit.assert_called_once_with('chat_response',action='replace',id='companion',original=original,text='Eine Frage?')

    def test_real_window_routes_response_markers_without_a_second_copy(self):
        import os
        from gui.live_window import LiveWindow
        from test_live_window import SilentAudio
        from apps.maat_rpg import session_shared
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window=LiveWindow(audio=SilentAudio())
            try:
                window.phase='playing';window.journal.clear();window.world_output.clear()
                layout=window.chat_level_panel.layout()
                self.assertLess(layout.indexOf(window.chat_xp_bar),layout.indexOf(window.model_timing))
                self.assertLess(layout.indexOf(window.model_timing),layout.indexOf(window.wiki_source))
                window.receive({'event':'wiki_context','titles':['Mona Lisa'],'terms':['Mona Lisa']})
                wiki=window.wiki_source.text()
                events=[{'event':'output','text':'Vorher\n'},
                        {'event':'chat_response','action':'begin','id':'wire'},
                        {'event':'output','text':'Hallo!\nHallo!\n'},
                        {'event':'chat_response','action':'end','id':'wire'},
                        {'event':'output','text':'Quest erfüllt\n'},
                        {'event':'chat_response','action':'replace','id':'wire','original':'Hallo!\nHallo!','text':'Hallo!'}]
                for event in events:window.receive(event)
                window.text_stream.finish()
                self.assertEqual(window.journal.toPlainText(),'Vorher\nHallo!\nQuest erfüllt\n')
                self.assertEqual(window.world_output.toPlainText(),window.journal.toPlainText())
                self.assertEqual(window.wiki_source.text(),wiki)
            finally:
                window.game.shutdown();window.close();window.deleteLater();APP.processEvents()
