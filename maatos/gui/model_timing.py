"""Local timings for loading and first visible response, without timing user idle time."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from statistics import median
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from shared.core.model_settings import normalize_tuning


def timing_key(event, language='de'):
    name = str(event.get('name', ''))
    try:
        stat = Path(name).stat() if Path(name).is_absolute() else None
        file_info = [stat.st_size, stat.st_mtime_ns] if stat else None
    except OSError:
        file_info = None
    tuning = normalize_tuning(event.get('tuning'))
    data = dict(revision=1, name=name, file=file_info, language=language,
                backend=event.get('backend'), context=event.get('n_ctx',20000),
                tuning=tuning if tuning['mode']=='manual' else {'mode':'auto'},
                system=platform.system(), machine=platform.machine(), cpus=os.cpu_count())
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


class ModelTiming(QWidget):
    def __init__(self, read_settings, save_settings, parent=None, clock=time.monotonic):
        super().__init__(parent)
        self.read_settings, self.save_settings, self.clock = read_settings, save_settings, clock
        self.language = 'de'
        layout=QVBoxLayout(self);layout.setContentsMargins(0,4,0,0);layout.setSpacing(4)
        self.title=QLabel();self.detail=QLabel();self.detail.setObjectName('muted')
        for item in (self.title,self.detail):
            item.setTextFormat(Qt.PlainText);item.setWordWrap(True);layout.addWidget(item)
        self.bar=QProgressBar();self.bar.setObjectName('xp');self.bar.setFixedHeight(5);self.bar.setTextVisible(False)
        layout.addWidget(self.bar)
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.render)
        self.reset()

    def reset(self):
        self.timer.stop()
        self.phase='idle';self.key=None;self.name='';self.started=None
        self.first_pending=True;self.metric=None;self.expected=None
        self.load_seconds=None;self.token_seconds=None
        self.render()

    def set_language(self, language):
        self.language=language;self.render()

    def t(self,de,en):
        return en if self.language=='en' else de

    def samples(self, metric):
        try:
            values=self.read_settings().get('gui_model_timings',{}).get(self.key,{}).get(metric,[])
            return [float(v) for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)
                    and math.isfinite(v) and 0<v<86400][-3:]
        except (TypeError,AttributeError):
            return []

    def record(self, metric, seconds):
        if not self.key or not 0<seconds<86400:
            return
        try:
            saved=self.read_settings().get('gui_model_timings',{})
            saved=dict(saved) if isinstance(saved,dict) else {}
            row=saved.pop(self.key,{})
            row=dict(row) if isinstance(row,dict) else {}
            row[metric]=(self.samples(metric)+[round(seconds,3)])[-3:]
            saved[self.key]=row
            # Keep a small per-profile cache; no prompts or conversation text.
            self.save_settings({'gui_model_timings':dict(list(saved.items())[-20:])})
        except (OSError,ValueError,TypeError):
            pass  # A timing estimate must never interrupt gameplay.

    def begin(self,phase,metric):
        self.phase=phase;self.metric=metric;self.started=self.clock()
        samples=self.samples(metric);self.expected=median(samples) if samples else None
        self.timer.start();self.render()

    def handle(self, event):
        kind=event.get('event')
        if kind=='model_load_started':
            self.reset();self.name=Path(str(event.get('name',''))).name
            self.key=timing_key(event,self.language);self.begin('loading','load')
        elif kind=='model' and event.get('status')=='ready':
            if self.phase=='loading':
                self.load_seconds=max(.001,self.clock()-self.started);self.record('load',self.load_seconds)
            self.name=Path(str(event.get('name',self.name))).name
            self.phase='ready';self.first_pending=True;self.started=None;self.timer.stop();self.render()
        elif kind=='chat_generation':
            self.begin('preparing','first_token' if self.first_pending else 'reply_token')
        elif kind=='chat_first_token' and self.phase=='preparing':
            self.token_seconds=max(.001,self.clock()-self.started);self.record(self.metric,self.token_seconds)
            self.first_pending=False;self.phase='streaming';self.started=None;self.timer.stop();self.render()
        elif kind=='chat_cancelled' or (kind=='busy' and not event.get('value') and self.phase=='preparing'):
            self.phase='cancelled';self.started=None;self.timer.stop();self.render()
        elif kind in ('error','model_error','stopped') or (kind=='model' and event.get('status')=='unloaded'):
            self.phase='error' if kind in ('error','model_error') else 'idle'
            self.started=None;self.timer.stop();self.render()

    @staticmethod
    def duration(seconds):
        seconds=max(0,int(round(seconds)));minutes,seconds=divmod(seconds,60)
        return f'{minutes}:{seconds:02d}'

    def render(self):
        active=self.phase in ('loading','preparing')
        self.bar.setVisible(active)
        suffix=' · '+self.name if self.name else ''
        if active:
            elapsed=max(0,self.clock()-self.started)
            self.title.setText(self.t('⏳ KI-Modell wird geladen','⏳ Loading AI model')+suffix if self.phase=='loading'
                               else self.t('⏳ KI bereitet die Antwort vor · Warte auf den ersten Token',
                                           '⏳ AI is preparing the reply · Waiting for the first token'))
            detail=self.t('Vergangen: ','Elapsed: ')+self.duration(elapsed)
            if self.expected is None:
                detail+=self.t(' · Erste Messung – noch keine Restzeit bekannt.',' · First measurement – no remaining-time estimate yet.')
                self.bar.setRange(0,0)
            else:
                if elapsed<self.expected:
                    detail+=self.t(' · Geschätzt noch ≈ ',' · Estimated remaining ≈ ')+self.duration(self.expected-elapsed)
                else:
                    detail+=self.t(' · Dauert länger als zuletzt; läuft weiter.',' · Taking longer than before; still running.')
                self.bar.setRange(0,100);self.bar.setValue(min(95,int(100*elapsed/self.expected)))
            if self.phase=='loading':
                samples=self.samples('first_token')
                if samples:
                    detail+=self.t(' Danach erster Antwort-Token zuletzt nach ≈ ',' After loading, the first reply token previously took ≈ ')+self.duration(median(samples))+'.'
            self.detail.setText(detail)
        elif self.phase in ('ready','streaming'):
            self.title.setText(self.t('✓ KI-Modell geladen','✓ AI model loaded')+suffix)
            details=[]
            if self.load_seconds is not None:
                details.append(self.t('Ladezeit: ','Load time: ')+self.duration(self.load_seconds))
            if self.phase=='streaming':
                details.append(self.t('Erster Token empfangen nach ','First token received after ')+self.duration(self.token_seconds))
            else:
                samples=self.samples('first_token')
                details.append(self.t('Erste Antwort: zuletzt ≈ ','First reply: previously ≈ ')+self.duration(median(samples))
                               if samples else self.t('Die erste Antwort wird beim Schreiben gemessen.','The first reply will be timed when you send a message.'))
            self.detail.setText(' · '.join(details))
        else:
            self.title.setText(self.t('⏹ Antwort abgebrochen','⏹ Reply cancelled') if self.phase=='cancelled'
                               else self.t('⚠ KI-Vorgang fehlgeschlagen','⚠ AI operation failed') if self.phase=='error'
                               else self.t('KI-Modell noch nicht geladen','AI model not loaded yet'))
            self.detail.setText(self.t('Die Zeitmessung startet beim Laden und erneut vor der ersten Antwort.',
                                      'Timing starts when the model loads and again before the first reply.'))
        self.setToolTip(self.t('Schätzung aus bis zu drei Messungen dieses Modells mit diesen Einstellungen auf diesem System. Eingabelänge und Systemlast können die Zeit verändern; Pausen zwischen Laden und Schreiben zählen nicht.',
                              'Estimated from up to three runs of this model with these settings on this system. Input length and system load can change the timing; idle time between loading and chatting is excluded.'))
