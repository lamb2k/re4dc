import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import capture

class CheckpointAdmission(unittest.TestCase):
    def fixture(self,root):
        seed=root/'first';(seed/'data').mkdir(parents=True)
        state=b'FLYSAVE1 own checkpoint';exe=root/'flycast.exe';exe.write_bytes(b'pinned emulator')
        (seed/'data/disc.state').write_bytes(state)
        program={'size':7,'sha256':'program'}
        image={'track':{'sha256':'track'},'files':{'1ST_READ.BIN':program}}
        identity={'image_track_sha256':'track','program':program,'state_sha256':hashlib.sha256(state).hexdigest(),
                  'flycast_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
        (seed/'checkpoint-identity.json').write_text(json.dumps(identity))
        (seed/'run-result.json').write_text(json.dumps({'emulator_exited':True}))
        return seed,root/'second',image,exe

    def test_own_complete_line_is_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));self.assertEqual(capture.validate_checkpoint(*args),args[0]/'data')

    def test_foreign_program_or_image_is_rejected(self):
        for key in ['program','track']:
            with tempfile.TemporaryDirectory() as tmp:
                args=list(self.fixture(Path(tmp)))
                if key=='program':args[2]['files']['1ST_READ.BIN']={'size':7,'sha256':'other'}
                else:args[2]['track']['sha256']='other'
                with self.assertRaises(ValueError):capture.validate_checkpoint(*args)

    def test_mutated_state_emulator_or_live_owner_is_rejected(self):
        for key in ['state','emulator','owner']:
            with tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp))
                if key=='state':(args[0]/'data/disc.state').write_bytes(b'changed')
                elif key=='emulator':args[3].write_bytes(b'other emulator')
                else:(args[0]/'run-result.json').write_text('{"emulator_exited":false}')
                with self.assertRaises(ValueError):capture.validate_checkpoint(*args)

    def test_another_lineage_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=list(self.fixture(Path(tmp)));args[1]=Path(tmp)/'elsewhere/second'
            with self.assertRaises(ValueError):capture.validate_checkpoint(*args)

if __name__=='__main__':unittest.main()
