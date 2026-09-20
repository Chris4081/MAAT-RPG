"""Adapt the original boss and credits scripts without running their terminal UI."""
from pathlib import Path
import runpy

TITLES = {
    'boss_scene_1':'Boss I · Der erste Schatten fällt',
    'boss_scene_2':'Boss II · Die nächste Prüfung',
    'boss_scene_3':'Boss III · Die Prüfung der Schöpfungskraft',
    'boss_scene_4':'Boss IV · Die Prüfung der Verbundenheit',
    'boss_scene_5':'Boss V · Die Prüfung der Wahrheit',
    'credits':'MAAT RPG · Finale und Abspann',
}


def cutscene_payload(path, language='de'):
    path = Path(path)
    if path.stem not in TITLES:
        return None
    title = TITLES[path.stem]
    if language == 'en':
        from gui.cutscenes_en import TEXT, TITLES as EN_TITLES
        lines = TEXT[path.stem].splitlines()
        title = EN_TITLES[path.stem]
    else:
        module = runpy.run_path(str(path), run_name='maat_gui_cutscene')
        lines = module['get_lines']()
    # Terminal-only prompts are replaced by the GUI's next/skip controls.
    lines = [line for line in lines if not line.strip().startswith('Drücke ENTER')]
    track_name = 'credits_theme.mp3' if path.stem == 'credits' else path.stem+'.mp3'
    tracks = ['credits_en.mp3', track_name] if path.stem == 'credits' and language == 'en' else [track_name]
    music = next((candidate for name in tracks
                  for candidate in (path.parent/name, path.parent/'music'/name)
                  if candidate.is_file()), None)
    return dict(lines=lines, music=str(music) if music else None,
                entry={'module':path.stem,'name':title})
