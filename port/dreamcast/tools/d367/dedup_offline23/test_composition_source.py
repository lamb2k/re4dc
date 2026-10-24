import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import check_composition as c


class CompositionSourceTests(unittest.TestCase):
    def test_dirty_git_refused_before_extraction_or_output(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            root=Path(tmp);tree=root/'source';tree.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(tree),*args],stderr=subprocess.DEVNULL,text=True).strip()
            git('init');git('config','user.name','Host control');git('config','user.email','host@example.invalid')
            source=tree/'native_static.cpp';source.write_text('original frozen source\\n')
            git('add','native_static.cpp');git('commit','-m','Freeze fixture');head=git('rev-parse','HEAD')
            c.authenticate_source(tree,head)
            source.write_text('tracked changed after freeze\\n');output=root/'compiled'
            with patch('sys.argv',['check_composition.py','--source-tree',str(tree),'--expected-source',head,'--output',str(output)]),patch.object(c,'generate') as extraction:
                with self.assertRaisesRegex(ValueError,'Tracked source tree is dirty'):c.main()
                extraction.assert_not_called();self.assertFalse(output.exists())
            source.write_text('original frozen source\\n')
            git('add','native_static.cpp')
            c.authenticate_source(tree,head)
            with self.assertRaisesRegex(ValueError,'HEAD mismatch'):c.authenticate_source(tree,'0'*40)

    def test_snapshot_input_mutation_refused(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            tree=Path(tmp);f=tree/'native_static.cpp';f.write_bytes(b'frozen')
            pins=dict(source='a'*40,files={f.name:hashlib.sha256(f.read_bytes()).hexdigest()})
            (tree/'source-pins.json').write_text(json.dumps(pins))
            c.authenticate_source(tree,'a'*40)
            f.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Snapshot input changed'):c.authenticate_source(tree,'a'*40)
