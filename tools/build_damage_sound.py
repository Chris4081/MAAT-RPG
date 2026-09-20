"""Synthesize Maatis' short impact cue without external samples."""
from pathlib import Path
import json
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'maatos/gui/assets/audio/combat-v1'
RATE = 48000


def main():
    t = np.arange(round(RATE*.34))/RATE
    rng = np.random.default_rng(20260912)
    kernel = np.exp(-np.linspace(-3, 3, 23)**2/2)
    kernel /= kernel.sum()
    noise = np.convolve(rng.normal(size=len(t)), kernel, mode='same')
    phase = 2*np.pi*(65*t + (185-65)*.025*(1-np.exp(-t/.025)))
    sound = (.72*np.sin(phase)*np.exp(-t/.048)
             + .25*np.sin(2*np.pi*196*t)*np.exp(-t/.030)
             + .14*np.sin(2*np.pi*317*t)*np.exp(-t/.018)
             + .65*noise*np.exp(-t/.023))
    sound *= (1-np.exp(-t/.0015))*np.clip((.335-t)/.04, 0, 1)**2
    sound *= .4/np.max(np.abs(sound))
    pcm = np.rint(np.column_stack((sound, sound))*32767).astype('<i2')
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST/'maatis_hurt.wav'
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm.tobytes())
    info = dict(file=path.name, duration=len(t)/RATE, sample_rate=RATE,
                peak_db=round(float(20*np.log10(np.max(np.abs(sound)))), 2),
                rms_db=round(float(20*np.log10(np.sqrt(np.mean(sound**2)))), 2),
                origin='Original procedural synthesis, no external samples.')
    (DEST/'manifest.json').write_text(json.dumps(info, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    main()
