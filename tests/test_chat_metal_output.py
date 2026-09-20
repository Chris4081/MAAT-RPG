import unittest
from unittest.mock import patch
from test_desktop import APP
from gui.game_worker import Output

BLOCK='''ggml_metal_device_init: tensor API disabled for pre-M5 and pre-A19 devices
ggml_metal_library_init: using embedded metal library
ggml_metal_library_init: loaded in 0.008 sec
ggml_metal_rsets_init: creating a residency set collection (keep_alive = 180 s)
ggml_metal_device_init: GPU name:   MTL0 (Apple M4)
ggml_metal_device_init: GPU family: MTLGPUFamilyApple9  (1009)
ggml_metal_device_init: GPU family: MTLGPUFamilyCommon3 (3003)
ggml_metal_device_init: GPU family: MTLGPUFamilyMetal4  (5002)
ggml_metal_device_init: simdgroup reduction   = true
ggml_metal_device_init: simdgroup matrix mul. = true
ggml_metal_device_init: has unified memory    = true
ggml_metal_device_init: has bfloat            = true
ggml_metal_device_init: has tensor            = false
ggml_metal_device_init: use residency sets    = true
ggml_metal_device_init: use shared buffers    = true
ggml_metal_device_init: recommendedMaxWorkingSetSize  = 19069.67 MB
'''

class ChatMetalTests(unittest.TestCase):
    def test_entire_startup_block_never_becomes_chat(self):
        out=Output()
        with patch('gui.game_worker.emit') as emit:
            out.write(BLOCK);out.flush()
            emit.assert_not_called()
            out.write('Maatis: Wer bist du?\n')
            emit.assert_called_once_with('output',text='Maatis: Wer bist du?\n')

    def test_split_flushed_native_lines_and_normal_streaming(self):
        out=Output();seen=[]
        with patch('gui.game_worker.emit',side_effect=lambda kind,**data:seen.append(data['text'])):
            for line in BLOCK.splitlines(keepends=True):
                for character in line:
                    out.write(character);out.flush()
            self.assertEqual(''.join(seen),'')
            for word in ['Die ', 'Reise ', 'beginnt.']:
                out.write(word);out.flush()
            self.assertEqual(''.join(seen),'Die Reise beginnt.')

    def test_unknown_errors_survive_including_unterminated_line(self):
        out=Output();seen=[]
        errors='ggml_metal_library_init: failed to load library\nllama_decode returned -3\n'
        with patch('gui.game_worker.emit',side_effect=lambda kind,**data:seen.append(data['text'])):
            out.write(BLOCK+errors)
            out.write('ggml_metal_device_init: unexpected error');out.flush(force=True)
        self.assertEqual(''.join(seen),errors+'ggml_metal_device_init: unexpected error')
