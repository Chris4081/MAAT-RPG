"""Create the original, quiet story page click; no sampled audio is used."""
from pathlib import Path
import json
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'maatos/gui/assets/audio/ui-v1'
RATE = 48000


def main():
    t = np.arange(round(RATE*.12))/RATE
    rng = np.random.default_rng(20260911)
    noise = np.convolve(rng.normal(size=len(t)), np.ones(9)/9, mode='same')
    # A soft tactile tick with a very short, warm glass-like tail.
    sound = (.58*np.sin(2*np.pi*1180*t)*np.exp(-t/.011)
             + .32*np.sin(2*np.pi*790*t)*np.exp(-t/.023)
             + .16*noise*np.exp(-t/.009))
    sound *= (1-np.exp(-t/.0009)) * np.clip((.116-t)/.015, 0, 1)**2
    sound *= .19 / np.max(np.abs(sound))
    pcm = np.rint(np.column_stack((sound, sound))*32767).astype('<i2')
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / 'story_advance.wav'
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
