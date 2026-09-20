"""Extract the approved, existing pose boards (development tool, not a dependency).

Sources remain unchanged. Reviewed crop/foot anchors exclude headings and labels.
RGBA sprites share the standard portrait's height and foot baseline. No AI redraw.
"""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gui-preview/class-action-sets-v1'
ART = ROOT / 'maatos/gui/assets/classes'
OUTPUT = ART / 'actions-v1'
POSES = ('standard', 'ready', 'blink', 'tired', 'wave', 'balance', 'creation',
         'connection', 'respect', 'slash', 'claw', 'sand', 'spark', 'impulse',
         'focus', 'heal', 'hurt', 'guard', 'victory', 'charged')
# x cell starts, y starts, foot y, standard figure height, per-pose body x in cell.
LAYOUT = {
    'normal': ([17,293,569,846], [72,339,603,864,1122], [282,547,805,1068,1320], 194,
               [127,127,127,137, 108,123,107,119, 112,99,103,109, 115,106,131,132, 119,113,131,132]),
    'robo': ([15,293,569,846], [77,335,581,832,1087], [277,529,774,1028,1286], 178,
             [127,131,127,131, 107,109,111,111, 116,97,111,111, 115,101,128,127, 116,108,121,132]),
    'engelchen': ([15,293,570,847], [66,325,581,835,1092], [268,523,773,1031,1288], 182,
                  [126,134,126,139, 109,115,111,119, 111,104,105,118, 112,112,127,131, 133,112,124,132]),
    'magier': ([19,296,572,850], [62,321,580,833,1089], [276,531,781,1041,1300], 199,
               [132,132,132,132, 117,123,121,130, 115,104,111,122, 117,119,133,137, 119,119,132,134]),
    'priester': ([16,294,571,848], [69,330,586,843,1096], [275,531,783,1043,1297], 190,
                 [133,133,133,139, 121,127,125,127, 117,121,114,122, 121,124,124,126, 125,122,129,130]),
    'puppy': ([17,294,570,847], [70,323,576,829,1085], [271,521,774,1029,1286], 178,
              [129,123,126,137, 111,115,109,117, 109,109,116,115, 113,115,126,130, 111,115,124,130]),
}


def cutout(rgb, anchor, foot, name):
    # Teal costumes stay solid; background, including the spaces inside effect
    # rings and the floor ellipse, is removed. Preserve enclosed hair/visor/robe.
    dark = (rgb[:,:,0] < 48) & (rgb[:,:,1] < 60) & (rgb[:,:,2] < 86)
    # The stage already paints a floor ring. These boards have a much dimmer,
    # single-pixel gold ellipse beneath the bright feet: remove that duplicate.
    r,g,b = (rgb[:,:,channel].astype(int) for channel in range(3))
    floor = (np.indices(dark.shape)[0] > foot-18) & (r < 210) & (g-r < 20) & (b-r < 45)
    dark |= floor
    labels, count = ndimage.label(dark)
    border = set(np.concatenate((labels[0], labels[-1], labels[:,0], labels[:,-1])))
    foreground = ~dark
    for ident, box in enumerate(ndimage.find_objects(labels), 1):
        if ident in border or box is None:
            continue
        ys, xs = box
        region = labels[box] == ident
        cy, cx = np.argwhere(region).mean(axis=0) + (ys.start, xs.start)
        # Enclosed dark costume parts; large empty circles remain transparent.
        in_head = abs(cx-anchor) < 46 and foot-180 < cy < foot-65
        in_robe = name == 'magier' and abs(cx-anchor) < 36 and foot-80 < cy < foot-8
        if (in_head or in_robe) and region.sum() < 5200:
            foreground[box] |= region

    # Recover anti-aliased outlines without leaving a dark rectangular matte.
    inside = ndimage.distance_transform_edt(foreground)
    outside = ndimage.distance_transform_edt(~foreground)
    band = (inside <= 2) & (outside <= 2)
    fi = ndimage.distance_transform_edt(inside < 2, return_distances=False, return_indices=True)
    bi = ndimage.distance_transform_edt(outside < 2, return_distances=False, return_indices=True)
    f, b, c = (arr.astype(float) for arr in
               (rgb[fi[0][band],fi[1][band]], rgb[bi[0][band],bi[1][band]], rgb[band]))
    diff = f-b
    alpha = np.clip(((c-b)*diff).sum(axis=1) / np.maximum(1., (diff*diff).sum(axis=1)),0,1)
    alpha[alpha < .03] = 0
    rgba = np.dstack((rgb, foreground.astype(np.uint8)*255))
    rgba[band,:3] = np.rint(np.clip((c-(1-alpha[:,None])*b)/np.maximum(alpha[:,None],1/255),0,255)).astype('uint8')
    rgba[band,3] = np.rint(alpha*255).astype('uint8')
    # Discard isolated sub-pixel remnants of the printed ellipse, while keeping
    # feet and the priest's staff (connected to the complete character).
    pieces, _ = ndimage.label(rgba[:,:,3] > 3)
    for ident, box in enumerate(ndimage.find_objects(pieces),1):
        if box is not None and box[0].start > foot-18:
            region = pieces[box] == ident
            if region.sum() < 180:
                rgba[box][region,3] = 0
    rgba[rgba[:,:,3] == 0,:3] = 0
    return Image.fromarray(rgba)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {'version':1, 'source_set':'gui-preview/class-action-sets-v1',
                'method':'Local extraction of existing illustrations; no redraw', 'assets':[]}
    preview = Image.new('RGB',(6*256,20*280),'#142947')
    draw = ImageDraw.Draw(preview)
    for column, (name, (xs, tops, feet, height, anchors)) in enumerate(LAYOUT.items()):
        source = SOURCE/f'maatis-{name}-set.png'
        source_hash = sha256(source.read_bytes()).hexdigest()
        sheet = Image.open(source).convert('RGB')
        standard = Image.open(ART/f'transparent-v1/maatis-{name}.png')
        bbox = standard.getchannel('A').getbbox()
        scale = ((bbox[3]-bbox[1])/standard.height*320) / height
        baseline = bbox[3]/standard.height*320
        for i, pose in enumerate(POSES):
            row, col = divmod(i,4)
            crop = (xs[col]+2, tops[row]+2, xs[col]+260, feet[row]+14)
            rgb = np.asarray(sheet.crop(crop))
            sprite = cutout(rgb, anchors[i]-2, feet[row]-crop[1], name)
            sprite = sprite.resize((round(sprite.width*scale),round(sprite.height*scale)), Image.Resampling.LANCZOS)
            # Extra transparent margin lets waves/claws extend beyond the body
            # without shrinking Maatis or cutting effects off at the frame edge.
            canvas = Image.new('RGBA',(416,416))
            x = 48 + round(160-(anchors[i]-2)*scale)
            y = 48 + round(baseline-(feet[row]-crop[1])*scale)
            canvas.alpha_composite(sprite,(x,y))
            target = OUTPUT/name/f'{pose}.png'
            target.parent.mkdir(exist_ok=True)
            canvas.save(target)
            manifest['assets'].append(dict(class_id=name, pose=pose, file=f'{name}/{pose}.png',
                source=source.name, source_sha256=source_hash, crop=list(crop),
                anchor=[anchors[i]+xs[col],feet[row]], sha256=sha256(target.read_bytes()).hexdigest()))
            preview.paste(canvas.resize((256,256),Image.Resampling.LANCZOS),(column*256,i*280),
                          canvas.resize((256,256),Image.Resampling.LANCZOS))
            draw.text((column*256+8,i*280+258),f'{name} / {pose}',fill='#edcd7f')
        assert sha256(source.read_bytes()).hexdigest() == source_hash
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    out = ROOT/'gui-preview/class-animations-v1'
    out.mkdir(exist_ok=True)
    for start, end, label in [(0,4,'idle'),(4,8,'principles'),(8,12,'attacks'),(12,16,'support'),(16,20,'reactions')]:
        preview.crop((0,start*280,1536,end*280)).save(out/f'poses-{label}.png')
    print(f'Extracted {len(manifest["assets"])} RGBA poses into {OUTPUT}')


if __name__ == '__main__':
    main()
