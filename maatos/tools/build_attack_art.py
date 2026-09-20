"""Rebuild attack sprites from the canonical, editable combat SVGs."""
from pathlib import Path
import json
from build_maatis_art import attack_svg, build_reactions

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'gui/assets/combat'
OUT = ART/'attacks'
# Effects face right; enemy sprites mirror only the effect, preserving their identity.
EFFECTS = {
 'slash': '<path d="M137 51Q215 85 222 161Q188 101 137 51Z" fill="#fff0b2"/><path d="M162 70L226 118M169 172L229 135"/>',
 'claw': '<path d="M154 59Q194 95 204 164M177 49Q213 91 223 149M133 79Q176 116 182 184" stroke-width="7"/><path d="M200 156l12 18-3-24M219 142l10 16-2-24"/>',
 'wave': '<path d="M153 65Q204 116 153 178M174 49Q233 116 174 194M194 41Q253 116 194 203" stroke-width="5"/>',
 'spark': '<path d="M186 37L152 115H185L164 193L225 93H191L218 37Z" fill="#bdeefa" stroke="#f9e6a2"/><path d="M133 60l-9-13M225 174l10 11"/>',
 'sand': ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e8c576"/>' for x,y,r in [(164,62,3),(196,80,5),(220,110,4),(178,107,3),(204,145,5),(161,165,4),(226,176,3)])+'<path d="M137 182Q224 194 223 134M139 75Q206 44 227 104"/>',
 'balance': '<path d="M150 112H222M186 66V169M153 84H220M153 84L140 121H166ZM220 84L207 121H233Z"/><circle cx="186" cy="66" r="7" fill="#fff0b2"/>',
 'creation': '<path d="M189 54L199 95L234 115L199 135L189 179L179 135L145 115L179 95Z" fill="#f4d184"/><circle cx="189" cy="115" r="13" fill="#fff9d4"/>',
 'connection': '<path d="M151 76L216 111L161 164L151 76M140 121L216 111"/><circle cx="151" cy="76" r="10" fill="#bdeefa"/><circle cx="216" cy="111" r="13" fill="#fff0b2"/><circle cx="161" cy="164" r="10" fill="#bdeefa"/>',
 'respect': '<path d="M148 64L188 48L229 64V114Q228 158 188 184Q148 157 148 114Z" fill="#254c65"/><path d="M168 111L184 132L212 91" stroke="#fff0b2" stroke-width="6"/>',
 'impulse': '<circle cx="181" cy="115" r="44"/><circle cx="181" cy="115" r="29"/><path d="M181 45V68M181 162V187M110 115H135M226 115H239M131 66L148 83M214 149L232 168M129 165L148 146M214 80L232 62" stroke-width="5"/><circle cx="181" cy="115" r="15" fill="#fff0b2"/>',
}

def build(characters=None):
 OUT.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((OUT/'manifest.json').read_text()) if characters is not None and (OUT/'manifest.json').is_file() else {}
 sources=sorted(ART.glob('*.svg'))
 if characters is not None:
  missing=set(characters)-{p.stem for p in sources}
  if missing:raise ValueError(f'Missing character art: {sorted(missing)}')
  sources=[p for p in sources if p.stem in characters]
 for source in sources:
  original=source.read_text()
  body=original[original.index('>')+1:original.rindex('</svg>')]
  hero=source.stem=='maatis'
  # Maatis raises both arms; other figures lean into their attack.
  if hero:
   body=body.replace('M76 111L50 132L42 185L64 189L78 149M164 111L190 132L198 185L176 189L162 149', 'M76 111L52 106L44 137L63 143L78 130M164 111L194 89L218 105L203 121L180 126L162 149')
  manifest[source.stem]={}
  for kind,effect in EFFECTS.items():
   pose='translate(-5 8) rotate(9 120 170) scale(.9)' if hero else 'translate(23 8) rotate(-9 120 170) scale(.9)'
   mirrored='' if hero else 'transform="translate(240 0) scale(-1 1)"'
   svg=attack_svg(kind, effect) if hero else f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240"><g transform="{pose}">{body}</g><g {mirrored} fill="none" stroke="#dec787" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{effect}</g></svg>'
   filename=f'{source.stem}-{kind}.svg'
   (OUT/filename).write_text(svg)
   manifest[source.stem][kind]=filename
 if characters is None:
  for kind,effect in EFFECTS.items():
   (OUT/f'overlay-{kind}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240"><g fill="none" stroke="#dec787" stroke-width="3" stroke-linecap="round">{effect}</g></svg>')
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
 if characters is None:build_reactions()
 print(f'{len(sources)*len(EFFECTS)} character attack sprites built')

if __name__=='__main__': build()
