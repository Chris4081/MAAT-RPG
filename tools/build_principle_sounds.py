"""Create MAAT's five original, deterministic attack sounds (no sampled audio).

Run with Python + NumPy. Runtime playback needs only the bundled PCM WAV files.
"""
from pathlib import Path
import hashlib
import json
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'maatos/gui/assets/audio/principles-v1'
PREVIEW = ROOT / 'gui-preview/principle-sounds-v1'
RATE = 48000
DURATION = 1.35
NAMES = {
    'h_harmony': ('H · Harmonie', 'Warmer Akkord mit einer weichen Lichtwelle.'),
    'b_balance': ('B · Balance', 'Zwei gleich starke, räumlich versetzte Impulse.'),
    's_creation': ('S · Schöpfungskraft', 'Aufsteigende Energie mit funkelnden Obertönen.'),
    'v_connection': ('V · Verbundenheit', 'Verwobene Klangwellen mit antwortenden Echos.'),
    'r_respect': ('R · Respekt', 'Tiefer Schutzimpuls mit warmem, metallischem Nachklang.'),
}


class Sound:
    def __init__(self, seed):
        self.t = np.arange(round(RATE * DURATION)) / RATE
        self.mix = np.zeros((len(self.t), 2))
        self.rng = np.random.default_rng(seed)

    def add(self, samples, pan=0.):
        # Restrained equal-power stereo; every cue also works in mono.
        self.mix[:, 0] += samples * np.sqrt((1-pan)/2)
        self.mix[:, 1] += samples * np.sqrt((1+pan)/2)

    def bell(self, hz, start=0., amp=1., decay=.22, pan=0., partials=(1., .22, .06)):
        t = np.maximum(0., self.t-start)
        attack = 1-np.exp(-t/.008)
        for i, weight in enumerate(partials, 1):
            envelope = attack * np.exp(-t * (1+.45*(i-1))/decay)
            self.add(amp * weight * np.sin(2*np.pi*hz*i*t) * envelope, pan)

    def air(self, start=0., amp=.12, decay=.09, pan=0.):
        noise = self.rng.normal(size=len(self.t))
        kernel = np.exp(-np.linspace(-3, 3, 41)**2/2)
        kernel /= kernel.sum()
        noise = np.convolve(noise, kernel, mode='same')
        t = np.maximum(0., self.t-start)
        self.add(amp * noise * (1-np.exp(-t/.01))*np.exp(-t/decay), pan)

    def sweep(self, low, high, start=0., amp=.4, decay=.13, pan=0.):
        t = np.maximum(0., self.t-start)
        # Exponential pitch approach, including a short attack to avoid clicks.
        phase = 2*np.pi*(high*t + (low-high)*.095*(1-np.exp(-t/.095)))
        self.add(amp*np.sin(phase)*(1-np.exp(-t/.004))*np.exp(-t/decay), pan)

    def finish(self):
        dry = self.mix.copy()
        for seconds, wet in ((.043, .16), (.089, .10), (.151, .055)):
            delay = round(seconds*RATE)
            self.mix[delay:] += dry[:-delay, ::-1]*wet
        # Gentle saturation, conservative peak/RMS, and a clean silent tail.
        sound = np.tanh(self.mix*.72)
        sound -= sound.mean(axis=0)
        sound *= np.minimum(1., self.t/.003)[:, None]
        sound *= np.clip((DURATION-.004-self.t)/.12, 0., 1.)[:, None]**2
        rms = np.sqrt(np.mean(sound**2))
        gain = min(10**(-21/20)/rms, .56/np.max(np.abs(sound)))
        return np.rint(sound*gain*32767).astype('<i2')


def make_sounds():
    h = Sound(10)
    for hz, at, strength, pan in ((293.665, 0, 1, -.18), (369.994, .025, .65, .18),
                                 (440, .05, .48, 0), (587.33, .085, .22, -.10)):
        h.bell(hz, at, strength, .24, pan)
    h.air(amp=.17, decay=.14)

    b = Sound(20)
    b.bell(220, 0, .95, .115, -.24)
    b.bell(330, .185, .95, .115, .24)
    b.sweep(180, 95, amp=.27, decay=.07, pan=-.15)
    b.sweep(270, 143, .185, .27, .07, .15)
    b.bell(440, .35, .18, .17)

    s = Sound(30)
    s.sweep(180, 820, amp=.44, decay=.14)
    for i, hz in enumerate((440, 587.33, 739.989, 1174.66)):
        s.bell(hz, .018+i*.085, .68-i*.10, .115, (-1)**i*.22)
    s.air(amp=.30, decay=.12)

    v = Sound(40)
    v.bell(293.665, amp=.8, decay=.27, pan=-.23)
    v.bell(295.665, amp=.65, decay=.27, pan=.23)
    for at, hz, pan in ((.13, 440, .22), (.26, 587.33, -.22), (.39, 440, .12)):
        v.bell(hz, at, .30, .17, pan, (1, .09))

    r = Sound(50)
    r.sweep(132, 65, amp=1.05, decay=.13)
    r.bell(164.81, amp=.60, decay=.22)
    r.bell(329.63, .015, .36, .19, -.12)
    r.bell(451, .02, .12, .10, .12, (1, .08))
    r.air(amp=.40, decay=.055)
    return dict(zip(NAMES, (sound.finish() for sound in (h, b, s, v, r))))


def write_wav(path, samples):
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(samples.tobytes())


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    sounds = make_sounds()
    manifest = {'format':'PCM signed 16-bit stereo / 48000 Hz',
                'origin':'Original procedural synthesis, no external samples.', 'sounds':{}}
    preview = [np.zeros((RATE//3, 2), dtype='<i2')]
    for name, samples in sounds.items():
        path = DEST / (name+'.wav')
        write_wav(path, samples)
        floating = samples.astype(float)/32768
        manifest['sounds'][name] = dict(title=NAMES[name][0], description=NAMES[name][1],
            duration=len(samples)/RATE,
            peak_db=round(float(20*np.log10(np.max(np.abs(floating)))), 2),
            rms_db=round(float(20*np.log10(np.sqrt(np.mean(floating**2)))), 2),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        preview.extend((samples, np.zeros((int(RATE*.65), 2), dtype='<i2')))
    (DEST/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    write_wav(PREVIEW/'H-B-S-V-R.wav', np.concatenate(preview))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
