"""Editable Maatis poses derived from the canonical blue-and-gold robot SVG."""
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / 'gui/assets/combat'
ARMS = 'M76 111L50 132L42 185L64 189L78 149M164 111L190 132L198 185L176 189L162 149'
EYES = 'M99 70H110M130 70H141'
POSES = {
    'ready': ('M76 111L51 126L48 163L67 168L78 146M164 111L187 124L190 157L172 164L162 145', EYES, 2),
    'blink': (ARMS, 'M99 73H110M130 73H141', 0),
    'hurt': ('M76 111L49 133L36 173L55 182L78 149M164 111L181 117L164 141L151 151', 'M100 67L108 74M108 67L100 74M131 67L139 74M139 67L131 74', -8),
    'guard': ('M76 111L58 128L83 153L99 140L78 124M164 111L180 128L154 151L141 137L162 124', 'M99 68L110 71M130 71L141 68', 3),
    'focus': ('M76 111L50 141L70 166L99 161L97 147L78 147M164 111L190 141L170 166L141 161L143 147L162 147', 'M99 73Q105 77 111 73M129 73Q135 77 141 73', 0),
    'heal': ('M76 111L55 124L52 161L72 165L78 144M164 111L185 122L178 91L159 89L155 121', 'M99 73Q105 63 111 73M129 73Q135 63 141 73', -4),
    'victory': ('M76 111L52 99L43 67L62 61L76 88M164 111L188 99L197 67L178 61L164 88', 'M99 73Q105 63 111 73M129 73Q135 63 141 73', -3),
    'tired': ('M76 111L53 141L49 187L68 190L78 152M164 111L187 141L191 187L172 190L162 152', 'M99 73L110 75M130 75L141 73', 6),
    'slash': ('M76 111L48 127L40 158L60 165L78 145M164 111L191 100L218 117L208 134L183 124L162 149', 'M99 67L110 71M130 71L141 67', 5),
    'wave': ('M76 111L51 126L52 158L72 156L78 139M164 111L191 116L215 103L224 122L196 141L162 149', EYES, 3),
    'balance': ('M76 111L48 118L30 109L24 129L53 142L78 143M164 111L192 118L210 109L216 129L187 142L162 143', 'M99 71H111M129 71H141', 0),
    'creation': ('M76 111L54 121L54 145L76 157L97 141L91 128L78 135M164 111L190 103L203 78L221 88L207 123L162 149', 'M102 67V76M136 67V76', -4),
    'connection': ('M76 111L53 104L39 88L24 102L49 132L78 143M164 111L191 99L213 85L225 103L199 124L162 145', EYES, 2),
    'respect': ('M76 111L56 128L82 153L97 140L78 124M164 111L188 105L200 124L180 143L162 149', 'M99 68L110 71M130 71L141 68', 3),
    'spark': ('M76 111L54 109L37 131L53 145L78 130M164 111L182 89L178 61L200 61L205 104L162 149', 'M99 71H111M129 71H141', -4),
    'impulse': ('M76 111L54 105L41 75L61 66L76 88M164 111L186 105L199 75L179 66L164 88', 'M102 67V76M136 67V76', 0),
}


def body_for(kind):
    source = (ART / 'maatis.svg').read_text()
    body = source[source.index('>') + 1:source.rindex('</svg>')]
    arms, eyes, tilt = POSES.get(kind, POSES['slash'])
    body = body.replace(ARMS, arms).replace(EYES, eyes)
    # Move the head together with its antenna and visor, preserving the body.
    head_start = body.index('<rect x="78"')
    head_end = body.index('<path d="M120 125')
    body = body[:head_start] + f'<g transform="rotate({tilt} 120 105)">' + body[head_start:head_end] + '</g>' + body[head_end:]
    if kind == 'blink':
        body = body.replace('stroke="#bdeefa"', 'stroke="#73a2b6" stroke-width="1.5"')
    if kind == 'heal':
        body += '<g stroke="#c6fff0" stroke-width="2" stroke-linejoin="round"><path d="M162 83V72H178V83L183 89V108Q170 117 157 108V89Z" fill="#275c61"/><path d="M159 97H181V107Q170 112 159 107Z" fill="#72dfba"/><path d="M162 71H178" stroke="#dec787" stroke-width="5"/></g>'
    if kind == 'guard':
        body += '<path d="M128 111L168 95L207 111V148Q204 183 168 202Q132 183 128 148Z" fill="#244764" stroke="#bdeefa" stroke-width="3"/><path d="M168 118L182 141L168 165L154 141Z" fill="#dec787"/>'
    return body


def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">' + body + '</svg>'


def attack_svg(kind, effect):
    colors = {'wave':'#72dfba', 'balance':'#79bdff', 'creation':'#e8aeff', 'connection':'#ffcd7d', 'respect':'#ff9fae', 'spark':'#bdeefa'}
    color = colors.get(kind, '#dec787')
    # Keep the original attack symbol, smaller and beside the raised hand.
    return svg(body_for(kind) + f'<g transform="translate(39 5) scale(.8)" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{effect}</g>')


def build_reactions():
    target = ART / 'maatis'
    target.mkdir(exist_ok=True)
    for kind in ('ready', 'blink', 'hurt', 'guard', 'focus', 'heal', 'victory', 'tired'):
        (target / f'{kind}.svg').write_text(svg(body_for(kind)))


def build():
    from build_attack_art import EFFECTS
    build_reactions()
    for kind, effect in EFFECTS.items():
        (ART / 'attacks' / f'maatis-{kind}.svg').write_text(attack_svg(kind, effect))
    print('Maatis: 8 reaction poses and 10 attack sprites rebuilt from maatis.svg.')


if __name__ == '__main__':
    build()
