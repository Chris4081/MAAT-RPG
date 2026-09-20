"""Rebuild all regular Egyptian enemies and their ten matching attack poses.

Stable IDs keep saves, enemy names, DE/EN, the editor and catalog compatible.
Only regular enemies are replaced; boss and Maatis assets are separate.
"""
from build_attack_art import ART, build
from egyptian_enemy_shapes import SHAPES


def build_monsters():
    for name, shapes in SHAPES.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">'
               '<g fill="#535b83" stroke="#c69ce9" stroke-width="2.5" '
               'stroke-linejoin="round" stroke-linecap="round">'
               f'{shapes}</g></svg>')
        (ART / f'{name}.svg').write_text(svg, encoding='utf-8')
    build(characters=set(SHAPES))
    print(f'{len(SHAPES)} Egyptian regular enemy portraits')


if __name__ == '__main__':
    build_monsters()
