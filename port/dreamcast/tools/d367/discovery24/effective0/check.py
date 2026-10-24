"""Focused extension plus original source controls; shared charged ray tranche."""
import argparse,hashlib,importlib.util,json,os,resource,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'eligible';sys.path[:0]=[str(HERE),str(BASE),str(HERE.parent)]
import pool,capability
from ledger import Ledger
from prepare_capability import checked_rows
spec=importlib.util.spec_from_file_location('baseline_controls',BASE/'check.py');baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
CAPABILITY_PATH=None;AUDIT=None;MESH=None
class ExtensionControls(unittest.TestCase):
    def tearDown(self):pool.configure(False)
    def test_compiled_future_capability_is_exact_not_current_admission(self):
        pin=capability.verify_capability(CAPABILITY_PATH);self.assertEqual(pin['status'],'REQUIRES_FUTURE_CAPABILITY_NO_CURRENT_RUNTIME_ADMISSION')
    def test_absent_foreign_and_disabled_capability_refuse(self):
        with self.assertRaises(ValueError):pool.configure(True,None)
        with self.assertRaises(ValueError):pool.configure(False,CAPABILITY_PATH)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fake.json';path.write_text('{}')
            with self.assertRaises(ValueError):pool.configure(True,path)
    def test_all95_actual_cluster_counts_and_invalid_mutations(self):
        rows=checked_rows(AUDIT,MESH);pool.configure(True,CAPABILITY_PATH)
        for row in rows:
            source=baseline.src(row['placement'],level_count=len(row['meshlet_counts']));source.update(level=0,authored_meshlet_counts=row['meshlet_counts'])
            self.assertTrue(pool.source_allowed(source))
            for counts in ([0]+row['meshlet_counts'][1:],[row['meshlet_counts'][0],1],[row['meshlet_counts'][0]],[-1,0],[1.5,0],[True,0]):
                changed=dict(source,authored_meshlet_counts=counts);self.assertFalse(pool.source_allowed(changed))
            self.assertFalse(pool.source_allowed(dict(source,level=1)))
        self.assertEqual(len(rows),95)
    def test_generic_deep_range_not_just_second_level(self):
        self.assertTrue(pool.effective0_counts([5,0,0,0]));self.assertFalse(pool.effective0_counts([5,0,0,1]));self.assertFalse(pool.effective0_counts([]))
    def test_added_source_keeps_all_original_prerequisites(self):
        pool.configure(True,CAPABILITY_PATH)
        for bad in (dict(static=False),dict(unconditional=False),dict(nonsingular=False),{'pass':2},dict(cull=1),dict(vertex_alpha=True),dict(material_eligible=False)):
            source=baseline.src(1,level_count=2,**bad);source.update(level=0,authored_meshlet_counts=[3,0]);self.assertFalse(pool.source_allowed(source))
    def test_default_off_source_pool_and_hit_identity(self):
        pool.configure(False);a=pool.EligibleScene(baseline.TOKEN);b=pool.original.EligibleScene(baseline.TOKEN)
        sources=[baseline.src(1),baseline.src(2,level_count=2),baseline.src(3,cull=1),baseline.src(4,level_count=2)]
        for source in sources:
            source.update(level=0,authored_meshlet_counts=[3,0] if source['prerequisites']['level_count']==2 else [3]);self.assertEqual(pool.source_allowed(source),pool.original.source_allowed(source))
            tri=baseline.triangle(source,1000 if source['placement']==1 else 500);self.assertEqual(a.add_source(*tri),b.add_source(*tri))
        a.build();b.build();self.assertEqual(a.meta,b.meta);self.assertEqual(a.xyz,b.xyz);self.assertEqual(a.patch,b.patch);self.assertEqual(a.patches,b.patches)
        self.assertEqual(a.nearest((0,0,0),(0,0,2000),source_before=5),b.nearest((0,0,0),(0,0,2000),source_before=5))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--capability-receipt',required=True,type=Path);ap.add_argument('--audit',required=True,type=Path);ap.add_argument('--mesh',required=True,type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False);CAPABILITY_PATH=a.capability_receipt;AUDIT=a.audit;MESH=a.mesh
    baseline.TOKEN=Ledger(a.ledger).reserve(1024,'effective0 focused and baseline controls including ray/brute parity; no refund');suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(baseline.Controls),unittest.defaultTestLoader.loadTestsFromTestCase(ExtensionControls)])
    with (a.out/'tests.log').open('x') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    pin=baseline.runtime.snapshot();(a.out/'HOST-RUNTIME.json').write_text(json.dumps(pin,indent=2)+'\n');r=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,ray_queries_used=baseline.TOKEN.used,ray_reservation_charged=baseline.TOKEN.reserved,ledger=json.loads(a.ledger.read_text()),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,classification='NO_CERTIFICATE',capability=capability.verify_capability(CAPABILITY_PATH),runtime=pin,source_pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')})
    data=(json.dumps(r,indent=2)+'\n').encode();existing=sum(p.stat().st_size for p in a.out.parent.rglob('*') if p.is_file())
    if existing+len(data)+65536>16*1024*1024:raise ValueError('Whole new evidence unit cap')
    (a.out/'HOST-CONTROLS.json').write_bytes(data);print(json.dumps(r));sys.exit(0 if result.wasSuccessful() else 1)
