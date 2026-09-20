"""Installed app resources must never be used as writable profile storage."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

GAME = Path(__file__).resolve().parents[1] / 'maatos'
sys.path.insert(0, str(GAME))


class InstalledStorageTests(unittest.TestCase):
    def test_plugins_initialize_and_save_without_writing_into_app(self):
        with tempfile.TemporaryDirectory(prefix='maat-install-storage-') as temp:
            root = Path(temp).resolve()
            env = {f'MAAT_{name}_DIR': str(root / name.lower())
                   for name in ('APP_SUPPORT', 'DATA', 'STATE', 'LOGS', 'MODELS', 'SAVES', 'CACHE')}
            mkdir = os.makedirs
            def profile_makedirs(path, *args, **kwargs):
                if not Path(path).resolve().is_relative_to(root):
                    raise PermissionError('Installed app is read-only: ' + str(path))
                return mkdir(path, *args, **kwargs)
            with patch.dict(os.environ, env), patch('pathlib.Path.home', return_value=root), patch('os.makedirs', side_effect=profile_makedirs):
                for folder, cls in (('dungeon_60', 'DungeonState'), ('dungeon_500', 'Dungeon500State'),
                                    ('dungeon_1000', 'Dungeon1000State')):
                    path = GAME / 'apps/maat_rpg/plugins' / folder / 'plugin_main.py'
                    spec = importlib.util.spec_from_file_location('installed_' + folder, path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    state = getattr(module, cls)('/Applications/MAAT RPG.app/Contents/Resources/maatos')
                    state.data['runs'] = 3
                    state.save()
                    self.assertTrue(Path(state.path).is_relative_to(root))
                    self.assertEqual(getattr(module, cls)('/Applications/MAAT RPG.app').data['runs'], 3)
                from shared.plugins.maat_bki.plugin_main import Plugin as BKI
                from shared.plugins.maat_memauto.plugin_main import Plugin as MemAuto
                from shared.core.self_evolution import SelfEvolutionEngine
                self.assertTrue(Path(BKI().store_path).is_relative_to(root))
                memory = MemAuto()
                memory.memories = []
                memory._save_memories()
                self.assertTrue(Path(memory.mem_path).is_relative_to(root))
                evo = SelfEvolutionEngine(None, None, None)
                evo._save_state()
                self.assertTrue(Path(evo.base_dir).is_relative_to(root))


if __name__ == '__main__':
    unittest.main()
