"""Original MAAT level-up and victory cues; no samples or external compositions.

Rebuild with Python + NumPy and FFmpeg (libmp3lame). The game keeps its existing
MP3 paths; lossless listening copies and provenance are written alongside them.
Only oscillators, deterministic noise and locally composed note sequences are used.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'maatos'
BATTLE = GAME / 'apps/maat_rpg/plugins/battle'
PREVIEW = ROOT / 'gui-preview/celebration-sounds-v1'
RATE = 48000
ORIGIN = 'Original procedural synthesis and project note sequences; no external samples.'


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


class Cue:
    def __init__(self, seconds, seed):
        self.t = np.arange(round(seconds * RATE)) / RATE
        self.mix = np.zeros((len(self.t), 2))
        self.rng = np.random.default_rng(seed)

    def add(self, sound, start, pan=0):
        at = round(start * RATE)
        count = min(len(sound), len(self.mix) - at)
        if count <= 0:
            return
        self.mix[at:at + count, 0] += sound[:count] * np.sqrt((1 - pan) / 2)
        self.mix[at:at + count, 1] += sound[:count] * np.sqrt((1 + pan) / 2)

    def bell(self, note, start, amp=.4, decay=1.1, pan=0):
        t = np.arange(round(min(6.0, decay * 6) * RATE)) / RATE
        sound = np.zeros_like(t)
        for ratio, weight in ((1, 1), (2.003, .23), (3.99, .045)):
            sound += weight * np.sin(2 * np.pi * hz(note) * ratio * t) * np.exp(-t * ratio ** .42 / decay)
        sound *= (1 - np.exp(-t / .009)) * np.minimum(1, (t[-1] - t) / .07)
        self.add(sound * amp, start, pan)

    def glow(self, notes, start, duration, amp=.12):
        t = np.arange(round(duration * RATE)) / RATE
        envelope = (1 - np.exp(-t / .18)) * np.exp(-t / 2.9)
        envelope *= np.clip((duration - t) / .8, 0, 1) ** 2
        for index, note in enumerate(notes):
            # Gentle beating, restrained harmonics; no sampled instrument.
            f = hz(note)
            voice = (np.sin(2 * np.pi * f * t)
                     + .22 * np.sin(2 * np.pi * f * 1.0017 * t)
                     + .10 * np.sin(2 * np.pi * f * 3 * t))
            self.add(voice * envelope * amp, start, (-1) ** index * .2)

    def breath(self, start, duration=.5, amp=.07):
        t = np.arange(round(duration * RATE)) / RATE
        noise = self.rng.normal(size=len(t))
        kernel = np.exp(-np.linspace(-3, 3, 81) ** 2 / 2)
        noise = np.convolve(noise, kernel / kernel.sum(), mode='same')
        self.add(amp * noise * np.sin(np.pi * t / duration) ** 2, start)

    def pulse(self, start, amp=.13):
        t = np.arange(round(.65 * RATE)) / RATE
        phase = 2 * np.pi * (73.42 * t + 55 * .045 * (1 - np.exp(-t / .045)))
        self.add(amp * np.sin(phase) * (1 - np.exp(-t / .006)) * np.exp(-t / .12), start)

    def finish(self):
        dry = self.mix.copy()
        # Short reflections and a longer, fading stereo hall tail.
        for delay, wet in ((.041, .12), (.089, .09), (.157, .07), (.271, .05), (.443, .035)):
            frames = round(delay * RATE)
            self.mix[frames:] += dry[:-frames, ::-1] * wet
        sound = np.tanh(self.mix * .8)
        sound -= sound.mean(axis=0)
        sound *= np.clip(self.t / .005, 0, 1)[:, None]
        sound *= np.clip((len(self.t) / RATE - .005 - self.t) / .65, 0, 1)[:, None] ** 2
        gain = min(10 ** (-22 / 20) / np.sqrt(np.mean(sound ** 2)), .52 / np.max(np.abs(sound)))
        return np.rint(sound * gain * 32767).astype('<i2')


def compose():
    # Eight seconds: a five-step ascent, a luminous response, a soft final chord.
    level = Cue(8.0, 2026092001)
    level.glow((50, 57, 62), .0, 3.8, .075)
    for i, note in enumerate((62, 66, 69, 71, 74)):
        level.bell(note, .12 + i * .29, .34 + i * .025, .8, (-1) ** i * .18)
    for i, note in enumerate((76, 78, 81, 86)):
        level.bell(note, 1.85 + i * .22, .28, 1.25, (-1) ** i * .22)
    level.breath(2.2, .9, .16)
    level.pulse(3.05, .2)
    level.glow((50, 57, 62, 66, 69), 3.05, 4.95, .13)
    for i, note in enumerate((74, 78, 81, 86)):
        level.bell(note, 3.08 + i * .045, .25, 1.6, (-1) ** i * .2)
    level.bell(81, 4.35, .12, 1.25, -.12)
    level.bell(86, 4.85, .10, 1.15, .12)

    # Six seconds: grounded call-and-response with a warm major resolution.
    victory = Cue(6.0, 2026092002)
    for at, note, amp in ((.05, 57, .40), (.30, 62, .43), (.63, 66, .43),
                          (1.02, 69, .47), (1.42, 66, .32), (1.76, 74, .46)):
        victory.bell(note, at, amp, .75, -.12 if note < 66 else .12)
    for at in (.04, .62, 1.75):
        victory.pulse(at)
    victory.breath(1.5, .55, .13)
    victory.glow((50, 57, 62, 66), 1.78, 4.22, .16)
    for i, note in enumerate((69, 74, 78, 81)):
        victory.bell(note, 2.0 + i * .09, .21, 1.25, (-1) ** i * .18)
    return {'levelup': level.finish(), 'victory': victory.finish()}


def write_wav(path, samples):
    with wave.open(str(path), 'wb') as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(samples.tobytes())


def main():
    encoder = shutil.which('ffmpeg')
    if not encoder:
        raise SystemExit('FFmpeg with libmp3lame is required to rebuild the MP3 assets.')
    PREVIEW.mkdir(parents=True, exist_ok=True)
    specs = {
        'levelup': ('MAAT - Aufstieg des Lichts', BATTLE / 'sounds/levelup.mp3'),
        'victory': ('MAAT - Sieg der Resonanz', BATTLE / 'music/victory.mp3'),
    }
    manifest = {'version': 1, 'created': '2026-09-20', 'origin': ORIGIN,
                'authoring': 'MAAT RPG project; AI-assisted procedural sound design under Christof Krieg\u2019s direction.',
                'source': 'tools/build_celebration_sounds.py (project root)',
                'licensing': 'Project-created media; no Pixabay/Suno or other sample-library content. This manifest does not grant a new separate media license.',
                'format': 'MP3 192 kbps / 48000 Hz stereo; lossless 16-bit WAV previews',
                'sounds': {}}
    for name, samples in compose().items():
        title, destination = specs[name]
        wav = PREVIEW / (name + '.wav')
        write_wav(wav, samples)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Finish encoding before atomically replacing the current game asset.
        with tempfile.TemporaryDirectory(prefix='maat-celebration-') as temp:
            encoded = Path(temp) / (name + '.mp3')
            subprocess.run([encoder, '-nostdin', '-hide_banner', '-loglevel', 'error',
                            '-y', '-i', str(wav), '-map_metadata', '-1',
                            '-codec:a', 'libmp3lame', '-b:a', '192k', '-ar', str(RATE), '-ac', '2',
                            '-metadata', 'title=' + title, '-metadata', 'artist=MAAT RPG',
                            '-metadata', 'album=MAAT RPG - Original Game Effects',
                            '-metadata', 'date=2026', '-metadata', 'comment=' + ORIGIN,
                            str(encoded)], check=True)
            staged = destination.with_suffix('.mp3.tmp')
            shutil.copyfile(encoded, staged)
            staged.replace(destination)
        floating = samples.astype(float) / 32768
        manifest['sounds'][name] = {
            'title': title, 'file': str(destination.relative_to(GAME)),
            'preview': str(wav.relative_to(ROOT)), 'duration_pcm_seconds': len(samples) / RATE,
            'peak_dbfs': round(float(20 * np.log10(np.max(np.abs(floating)))), 2),
            'rms_dbfs': round(20 * float(np.log10(np.sqrt(np.mean(floating ** 2)))), 2),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'wav_sha256': hashlib.sha256(wav.read_bytes()).hexdigest(),
        }
    data = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    (BATTLE / 'sounds/original-cues-manifest.json').write_text(data, encoding='utf-8')
    (PREVIEW / 'manifest.json').write_text(data, encoding='utf-8')
    print(data)


if __name__ == '__main__':
    main()
