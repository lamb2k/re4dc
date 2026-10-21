import importlib.util,sys,unittest
from pathlib import Path
T=Path(__file__).resolve().parents[1]/'tools/d367/issue52_visuals'
sys.path.insert(0,str(T));import audit


class SourceBindings(unittest.TestCase):
    def test_rejects_ambiguous_same_archive_index(self):
        def row(key):return dict(key=key,source_references=[dict(file_sha256='abc',arc_index=32,image=0,width=256,height=256)])
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            audit.image_keys([row('a'),row('b')],'abc',32)
        self.assertEqual(audit.image_keys([row('a'),row('b')],'other',32),{})

    def test_mask_cannot_silently_fall_back_to_diffuse(self):
        bindings={0:('680fc44c-1c7b1805',256,256)}
        with self.assertRaisesRegex(ValueError,'mask.*unbound'):
            audit.material_key(0,1,4,bindings)
        self.assertEqual(audit.material_key(0,1,0,bindings),'680fc44c-1c7b1805')

    def test_pair_requires_shared_dimensions(self):
        bindings={0:('680fc44c-1c7b1805',256,256),1:('cd2fdf7b-98123ca6',128,256)}
        with self.assertRaisesRegex(ValueError,'dimensions'):
            audit.material_key(0,1,4,bindings)
        bindings[1]=('cd2fdf7b-98123ca6',256,256)
        self.assertEqual(audit.material_key(0,1,4,bindings),'d1fdb548-e80a6158')
        self.assertIsNone(audit.material_key(255,1,4,{}))

if __name__=='__main__':unittest.main()
