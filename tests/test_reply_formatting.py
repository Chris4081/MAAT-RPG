"""Actual Qt tables/code, streaming boundaries, revisions and profile switches."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtGui import QTextCursor, QTextTable
from PySide6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout
from gui.chat_response import ChatResponse
from gui.reply_formatting import math_markdown, readable_math, trim_transcript, formatted_fragment
from gui.desktop import STYLE
from gui.reading_style import set_reader_size
from shared.core.ai_plugin_settings import DEFAULTS, SNAPSHOT
from shared.core.thinking_mode import prepare_generation_messages
import test_ai_plugins as helpers


SAMPLE = '''## Maatis · Deine Reise

**Harmonie** und *Balance* wirken zusammen.

| Prinzip | Wert | Bedeutung |
| --- | ---: | --- |
| Harmonie | 5/10 | Zusammenspiel |
| Balance | 6/10 | Ausgleich |

$$Stability = \\min(R, \\sqrt[4]{H \\cdot B \\cdot S \\cdot V})$$

```python
PlayerHP = 42
if PlayerHP > 0:
    print("Maatis bleibt Maatis")
```

Weiter geht es auf Terra. ✨
'''


def append(view, text):
    cursor=QTextCursor(view.document());cursor.movePosition(QTextCursor.End);cursor.insertText(text)


class FormattingTests(unittest.TestCase):
    def setUp(self):
        self.views=[QTextBrowser(),QTextBrowser()]
        self.hosts=[]
        for view in self.views:
            host=QWidget();host.setStyleSheet(STYLE);QVBoxLayout(host).addWidget(view);self.hosts.append(host)
            set_reader_size(view,26)
            view.document().setMaximumBlockCount(500)
            self.addCleanup(view.deleteLater)
            self.addCleanup(view.close)
            self.addCleanup(host.deleteLater);self.addCleanup(host.close)

    def reply(self, raw, enabled=True):
        editor=ChatResponse(self.views,formatting=lambda:enabled)
        editor.handle({'action':'begin','id':'test'})
        for view in self.views:append(view,raw)
        editor.handle({'action':'end','id':'test'})
        return editor

    def test_final_format_has_tables_headings_and_preserves_code_case_and_indent(self):
        self.reply(SAMPLE)
        for view in self.views:
            text=view.toPlainText()
            self.assertNotIn('## ',text);self.assertNotIn('**',text);self.assertNotIn('```',text)
            self.assertIn('⁴√(H · B · S · V)',text)
            self.assertIn('PlayerHP = 42\nif PlayerHP > 0:\n    print("Maatis bleibt Maatis")',text)
            tables=[f for f in view.document().rootFrame().childFrames() if isinstance(f,QTextTable)]
            self.assertEqual(len(tables),1)
            self.assertEqual((tables[0].rows(),tables[0].columns()),(3,3))
            self.assertEqual(view.document().begin().blockFormat().headingLevel(),2)
            self.assertEqual(view.document().maximumBlockCount(),0)
            block = view.document().begin()
            while block.isValid():
                fragment = block.begin()
                while not fragment.atEnd():
                    self.assertEqual(fragment.fragment().charFormat().foreground().color().name(), '#ffffff')
                    fragment += 1
                block = block.next()
        if os.environ.get('MAAT_FORMATTING_SCREENSHOTS'):
            target=Path(os.environ['MAAT_FORMATTING_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
            host=self.hosts[0];host.resize(1080,900);host.show();APP.processEvents()
            self.assertTrue(host.grab().save(str(target/'formatted-reply.png')))

    def test_off_is_exact_plain_text_and_active_reply_keeps_its_setting(self):
        self.reply(SAMPLE,False)
        for view in self.views:self.assertEqual(view.toPlainText(),SAMPLE)
        state=[False];editor=ChatResponse(self.views,formatting=lambda:state[0])
        editor.handle({'action':'begin','id':'next'});state[0]=True
        for view in self.views:append(view,'**Still plain**\n')
        editor.handle({'action':'end','id':'next'})
        for view in self.views:self.assertTrue(view.toPlainText().endswith('**Still plain**\n'))

    def test_render_only_after_stream_end_and_revision_keeps_later_status(self):
        raw='## 🤖 Maatis\n\n**Hello Terra**\n\n```python\nHP = 20\n```\n'
        revised=raw.replace('Hello Terra','Welcome to Terra').replace('HP = 20','HP = 21')
        for view in self.views:append(view,'Earlier text\n')
        editor=ChatResponse(self.views,formatting=lambda:True)
        editor.handle({'action':'begin','id':'one'})
        for part in (raw[:10],raw[10:]):
            for view in self.views:append(view,part)
        self.assertIn('**Hello Terra**',self.views[0].toPlainText())
        editor.handle({'action':'end','id':'one'})
        for view in self.views:append(view,'Quest complete: +10 XP\n')
        editor.handle({'action':'replace','id':'one','original':raw.strip('\n'),'text':revised.strip('\n')})
        for view in self.views:
            text=view.toPlainText()
            self.assertEqual(text.count('Welcome to Terra'),1)
            self.assertNotIn('Hello Terra',text);self.assertNotIn('HP = 20',text)
            self.assertTrue(text.startswith('Earlier text\n'))
            self.assertTrue(text.endswith('Quest complete: +10 XP\n'))
            self.assertEqual(view.document().find('Welcome to Terra').charFormat().foreground().color().name(), '#ffffff')
            self.assertEqual(view.document().find('HP = 21').charFormat().foreground().color().name(), '#ffffff')

    def test_trailing_table_revision_and_next_reply_remain_outside_table(self):
        raw='| A | B |\n|---|---|\n|one|two|\n'
        editor=self.reply(raw)
        for view in self.views:append(view,'NEXT STATUS\n')
        editor.handle({'action':'replace','id':'test','original':raw.strip(),'text':raw.strip().replace('two','three')})
        for view in self.views:
            self.assertIn('three',view.toPlainText());self.assertEqual(view.toPlainText().count('NEXT STATUS'),1)
            cursor=view.document().find('NEXT STATUS')
            self.assertIsNone(cursor.currentTable())

    def test_old_tables_are_trimmed_as_whole_frames_and_cleared_replies_do_not_reappear(self):
        editor=self.reply(SAMPLE)
        for view in self.views:
            for i in range(520):append(view,f'old line {i}\n')
            trim_transcript(view)
            self.assertLessEqual(view.document().blockCount(),500)
            self.assertIn('old line 519',view.toPlainText())
            view.clear();view.setPlainText('New profile')
        editor.handle({'action':'replace','id':'test','original':SAMPLE.strip(),'text':'OLD MUST NOT RETURN'})
        for view in self.views:self.assertEqual(view.toPlainText(),'New profile')

    def test_no_final_newline_still_keeps_next_status_outside_code(self):
        from PySide6.QtGui import QTextFormat
        self.reply('```python\nKeepCase = 1\n```')
        for view in self.views:
            append(view,'STATUS after reply')
            cursor=view.document().find('STATUS after reply')
            self.assertFalse(cursor.blockFormat().hasProperty(QTextFormat.BlockCodeFence))
            self.assertIn('KeepCase = 1\nSTATUS after reply',view.toPlainText())

    def test_math_subset_unknown_commands_and_code_are_non_destructive(self):
        self.assertEqual(readable_math(r'\frac{H\cdot B}{\Delta E + \epsilon}'),'('+ 'H· B'+')/(Δ E + ε)')
        self.assertEqual(readable_math(r'x^{2}+H_{1}'),'x²+H₁')
        unsupported=r'\begin{matrix}1&2\end{matrix}'
        self.assertEqual(readable_math(unsupported),unsupported)
        code='```python\nPriceUSD = "$5"\npattern = r"$x^{2}$"\n```'
        self.assertEqual(math_markdown(code),code)
        self.assertEqual(math_markdown('`$x^2$`'), '`$x^2$`')
        self.assertEqual(math_markdown('Price: $5 and $10.'),'Price: $5 and $10.')

    def test_no_external_resources_or_html_execution(self):
        from gui.reply_formatting import LocalDocument
        with patch.object(LocalDocument,'loadResource',return_value=None) as resources:
            fragment=formatted_fragment('![secret](file:///private/secret.txt)\n\n[link](https://example.com)\n\n<script>raw</script>',self.views[0].font())
        cursor=QTextCursor(self.views[0].document());cursor.insertFragment(fragment)
        document=self.views[0].document();block=document.begin()
        while block.isValid():
            it=block.begin()
            while not it.atEnd():
                fmt=it.fragment().charFormat();self.assertFalse(fmt.isImageFormat());self.assertFalse(fmt.isAnchor());it+=1
            block=block.next()
        self.assertIn('<script>raw</script>',document.toPlainText())

    def test_prompt_language_disable_and_no_accumulation(self):
        context={'pm':helpers.manager(),SNAPSHOT:dict(DEFAULTS)}
        for language,phrase in [('de','Groß- und Kleinschreibung'),('en','correct capitalization')]:
            prepared=prepare_generation_messages([{'role':'user','content':'Hallo'}],language=language,runtime_context=context)
            block=next(m['content'] for m in prepared if m['content'].startswith('[MAAT_FORMATTING]'))
            self.assertIn(phrase,block)
            repeated=prepare_generation_messages(prepared,language=language,runtime_context=context)
            self.assertEqual(str(repeated).count('[MAAT_FORMATTING]'),1)
            context[SNAPSHOT]['response_formatting_enabled']=False
            disabled=prepare_generation_messages(repeated,language=language,runtime_context=context)
            self.assertNotIn('[MAAT_FORMATTING]',str(disabled))
            context[SNAPSHOT]['response_formatting_enabled']=True


class LiveFormattingTests(unittest.TestCase):
    setUp=helpers.PluginMenuIntegrationTests.setUp
    close_windows=helpers.PluginMenuIntegrationTests.close_windows
    window=helpers.PluginMenuIntegrationTests.window
    ready=helpers.PluginMenuIntegrationTests.ready

    def test_real_profile_toggle_routes_chat_through_rich_or_plain_display(self):
        from apps.maat_rpg import session_shared
        session_shared.write_application_language('en')
        window=self.window();self.ready(window);window.phase='playing'
        window.input.setText('My next draft')
        self.assertTrue(window.plugin_panel.boxes['response_formatting_enabled'].isChecked())
        for enabled in (True,False):
            window.plugin_panel.boxes['response_formatting_enabled'].setChecked(enabled)
            window.journal.clear();window.world_output.clear()
            window.journal.append('<p style="color:#dac48e">You · Hello Terra</p>')
            window.receive({'event':'chat_response','action':'begin','id':'format'})
            window.receive({'event':'output','text':'\n\n'+SAMPLE[:10]})
            window.text_stream.finish()
            self.assertEqual(window.journal.document().find('Maatis').charFormat().foreground().color().name(), '#ffffff')
            for event in ({'event':'output','text':SAMPLE[10:]},
                          {'event':'chat_response','action':'end','id':'format'}):
                window.receive(event)
            window.text_stream.finish()
            for view in (window.journal,window.world_output):
                self.assertEqual(any(isinstance(f,QTextTable) for f in view.document().rootFrame().childFrames()),enabled)
                if not enabled:self.assertTrue(view.toPlainText().endswith(SAMPLE))
                self.assertEqual(view.document().find('Maatis').charFormat().foreground().color().name(), '#ffffff')
                self.assertEqual(view.document().find('PlayerHP = 42').charFormat().foreground().color().name(), '#ffffff')
            self.assertEqual(window.journal.document().find('You · Hello Terra').charFormat().foreground().color().name(), '#dac48e')
            self.assertEqual(window.input.text(),'My next draft')
            from gui.desktop import MaatWindow
            with patch.object(window.session, 'send_text'):
                MaatWindow.send(window)
            self.assertEqual(window.journal.document().find('My next draft').charFormat().foreground().color().name(), '#dac48e')
            window.input.setText('My next draft')


if __name__=='__main__':unittest.main()
