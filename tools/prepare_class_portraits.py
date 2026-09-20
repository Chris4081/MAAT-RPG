"""Freistellen der sechs freigegebenen Originale, ohne sie neu zu zeichnen.

Development tool only: Pillow, NumPy and SciPy are not game dependencies.
Run with Python 3 from any directory; source PNGs are never overwritten.
The reviewed seed points apply to this specific 1254 x 1254 portrait set.
"""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'maatos/gui/assets/classes'
OUTPUT = ART / 'transparent-v1'
CLASSES = ('normal', 'robo', 'engelchen', 'magier', 'priester', 'puppy')
# Enclosed background holes: inside the floating orb and the priest's staff ring.
# Dark hair, visor, boots, costume ears and robe panels must remain opaque.
HOLES = {'magier': [(270, 600)], 'priester': [(312, 340)]}


def cutout(rgb, name):
    if rgb.shape != (1254, 1254, 3):
        raise ValueError(f'{name}: source dimensions changed; review the mask first')
    dark = (rgb[:, :, 0] < 65) & (rgb[:, :, 1] < 70) & (rgb[:, :, 2] < 95)
    labels, _ = ndimage.label(dark)
    background_ids = []
    for x, y in [(0, 0), *HOLES.get(name, [])]:
        if not labels[y, x]:
            raise ValueError(f'{name}: background seed is no longer dark')
        background_ids.append(labels[y, x])
    background = np.isin(labels, background_ids)
    foreground = ~background

    # Recover partial edge coverage from the nearby gold outline/background.
    # This prevents a dark matte fringe when composited over the arena gradient.
    inside = ndimage.distance_transform_edt(foreground)
    outside = ndimage.distance_transform_edt(background)
    band = (inside <= 4) & (outside <= 4)
    near_fg = ndimage.distance_transform_edt(inside < 4, return_distances=False,
                                           return_indices=True)
    near_bg = ndimage.distance_transform_edt(outside < 4, return_distances=False,
                                           return_indices=True)
    f = rgb[near_fg[0][band], near_fg[1][band]].astype(np.float64)
    b = rgb[near_bg[0][band], near_bg[1][band]].astype(np.float64)
    c = rgb[band].astype(np.float64)
    difference = f - b
    coverage = np.clip(np.sum((c-b)*difference, axis=1) /
                       np.maximum(1., np.sum(difference*difference, axis=1)), 0., 1.)
    coverage[coverage < .015] = 0.
    coverage[coverage > .995] = 1.
    edge_rgb = np.clip((c-(1.-coverage[:, None])*b) /
                       np.maximum(coverage[:, None], 1./255), 0, 255)
    rgba = np.dstack((rgb, foreground.astype(np.uint8)*255))
    rgba[band, :3] = np.rint(edge_rgb).astype(np.uint8)
    rgba[band, 3] = np.rint(coverage*255).astype(np.uint8)
    rgba[rgba[:, :, 3] == 0, :3] = 0
    # All interior colors are copied, including those matching the navy background.
    assert np.array_equal(rgba[inside > 4, :3], rgb[inside > 4])
    assert (rgba[inside > 4, 3] == 255).all()
    return rgba


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {'method': 'Local connected-background extraction with edge matting',
                'source_set': 'Approved class-concepts-v2; originals preserved',
                'generated_variants_used': False, 'assets': []}
    for name in CLASSES:
        source = ART / f'maatis-{name}.png'
        target = OUTPUT / source.name
        original_hash = sha256(source.read_bytes()).hexdigest()
        with Image.open(source) as image:
            rgb = np.asarray(image.convert('RGB'))
        rgba = cutout(rgb, name)
        Image.fromarray(rgba).save(target)
        assert sha256(source.read_bytes()).hexdigest() == original_hash
        manifest['assets'].append(dict(name=name, source='../'+source.name,
            source_sha256=original_hash, file=target.name,
            sha256=sha256(target.read_bytes()).hexdigest(), width=1254, height=1254,
            mode='RGBA', transparent_pixels=int((rgba[:, :, 3] == 0).sum()),
            partial_alpha_pixels=int(((rgba[:, :, 3] > 0) & (rgba[:, :, 3] < 255)).sum())))
        print(f'{name}: RGBA saved to {target}')
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
