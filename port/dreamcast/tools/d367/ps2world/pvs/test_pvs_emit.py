import contextlib,hashlib,io,json,struct,tempfile,unittest
from pathlib import Path
from pvs_emit import emit


class EmitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.w=Path(self.temp.name)
        (self.w/'meta.json').write_text(json.dumps(dict(mesh_crc=1,mesh_bytes=1,sidecar_crc=1)))
        # The sole cell is at x=0..4m, camera y=1m. A target at 9m is
        # visible without an occluder, but absent from the finite ray sample.
        (self.w/'cells.bin').write_bytes(struct.pack('<3I3f2f4BB',1,1,2,0.,0.,4000.,1000.,1000.,1,0,0,0,1))
        (self.w/'inst.tsv').write_text('header\n'+'\t'.join(map(str,[0,0,0,0,0,0,0,0,-10000,0,-10000,10000,0,10000,6,2,0]))+'\n'+'\t'.join(map(str,[1,1,1,1,1,0,0,0,9000,2000,0,9100,2100,0,3,1,0]))+'\n')
        self.out=self.w/'out.pvs'
    def tearDown(self):self.temp.cleanup()
    def run_emit(self,**kw):
        with contextlib.redirect_stdout(io.StringIO()):emit(self.w,self.out,1,3000,**kw)
    def test_default_refuses_under_approximation(self):
        with self.assertRaisesRegex(ValueError,'sampled ray sets'):self.run_emit()
        self.assertFalse(self.out.exists())
    def test_research_reproduces_visible_target_loss(self):
        self.run_emit(research=True)
        b=self.out.read_bytes();idx=struct.unpack_from('<H',b,64)[0]
        self.assertFalse(b[72+idx]&2)
        self.assertFalse(json.loads(Path(str(self.out)+'.admission.json').read_text())['runtime_admitted'])
    def proof(self):
        (self.w/'proof-bits.bin').write_bytes(b'\x03')
        report=dict(kind='continuous-triangle-geometric-candidate',instances=2,cells=1,pinned_instances=[],hashes={name:hashlib.sha256((self.w/name).read_bytes()).hexdigest() for name in ('meta.json','cells.bin','inst.tsv','proof-bits.bin')})
        (self.w/'proof.json').write_text(json.dumps(report))
    def test_unproved_target_is_retained(self):
        self.proof();self.run_emit(geometric=True)
        b=self.out.read_bytes();self.assertTrue(b[72]&2)
    def test_stale_cells_refused(self):
        self.proof();(self.w/'cells.bin').write_bytes((self.w/'cells.bin').read_bytes()+b'\0')
        with self.assertRaisesRegex(AssertionError,'stale proof input'):self.run_emit(geometric=True)
        self.assertFalse(self.out.exists())
    def test_stale_bits_refused(self):
        self.proof();(self.w/'proof-bits.bin').write_bytes(b'\x01')
        with self.assertRaisesRegex(AssertionError,'stale proof input'):self.run_emit(geometric=True)
        self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
