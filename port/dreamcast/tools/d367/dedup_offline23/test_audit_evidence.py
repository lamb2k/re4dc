"""Evidence-only tests: no target, guest, disc or real screenshot work."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import audit_evidence as ae


MOVIE = '''SCNDEDUP3 room=100 meshlets=1967 repeats=14490 extra_heap=0 source_crc=fb35ea9c actual_crc=dceeb3ac
MOVIEARENA borrow id=10030 token=1 gen=1 capacity=1562656
SCNDEDUP3 room=100 meshlets=1967 repeats=14490 extra_heap=0 source_crc=fb35ea9c actual_crc=dceeb3ac
MOVIEARENA return token=1 restored=1
route movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340 heap_before=140448 heap_active=140448 wall_us=11924163 media_us=11344666
route movie cadence id=10030 shown=340 dropped=0
'''


class EvidenceTests(unittest.TestCase):
    def test_movie_requires_all_picture_counts_and_matching_loan(self):
        report=ae.summarize(MOVIE,{})
        movie=report['movies'][0]
        self.assertTrue(movie['complete_picture_counts_observed'])
        self.assertTrue(movie['restored_observed'])
        self.assertEqual(movie['heap_before'],140448)
        self.assertEqual(movie['wall_us'],11924163)
        self.assertEqual(len(movie['dedup_rows_between_borrow_and_return']),1)
        self.assertFalse(ae.summarize(MOVIE.replace('presented=340','presented=339'),{})['movies'][0]['complete_picture_counts_observed'])
        self.assertFalse(ae.summarize(MOVIE.replace('return token=1','return token=2'),{})['movies'][0]['restored_observed'])
        self.assertTrue(report['pixel_identity'].startswith('NOT_EVALUATED'))

    def test_diagnostic_flags_absent_disabled_enabled_and_untrusted(self):
        for knobs,trusted,state in (({},True,'FLAG_ABSENT'),({'TEX_CHECK':'0'},True,'NOT_INSTRUMENTED'),
                                    ({'TEX_CHECK':'1'},True,'INSTRUMENTED_NO_TELEMETRY'),({'TEX_CHECK':'1'},False,'UNVERIFIED_PROGRAMME')):
            self.assertEqual(ae.summarize('',knobs,trusted)['texchk']['state'],state)
        report=ae.summarize('TEXCHK fails=0 changes=0',{'TEX_CHECK':'1'})['texchk']
        self.assertEqual(report['state'],'INSTRUMENTED_OBSERVATIONS_ONLY')
        self.assertEqual(report['gate_verdict'],'NOT_EVALUATED')

    def test_diagnostic_failures_and_separate_cast_census(self):
        text='''TEXCHK FAIL fails=2 changes=1
NMRS r=101 declined=1 registry_declined=0 absent=2
LEONGC armed
LEONGC f=20
vram gaps: r=101 refusals=1 nocontig=2 guard_p=0
FAULT: invalid address
'''
        report=ae.summarize(text,{'TEX_CHECK':'1','MCHECK_LEONGC':'1','VRAM_ROOM_LOG':'1'})
        self.assertEqual(report['texchk']['maximum_fails'],2)
        self.assertEqual(len(report['texchk']['explicit_failure_rows']),1)
        self.assertEqual(report['cast_gc']['state'],'FLAG_ABSENT')
        self.assertEqual(len(report['cast_gc']['gc_fallback_rows']),1)
        self.assertEqual(len(report['leon_gc']['fallback_rows']),1)
        self.assertEqual(report['vram']['maximum_counters']['nocontig'],2)
        self.assertEqual(report['faults']['count'],1)
        self.assertEqual(report['vram']['gate_verdict'],'NOT_EVALUATED')

    def test_kos_held_headroom_does_not_assert_scene_endpoint(self):
        report=ae.summarize('kos squeeze: held=49152 frag=1\nkos watch: headroom=5000 top=4500\nkos watch: headroom=4000 top=3000',{'KOS_WATCH':'1','KOS_SQUEEZE':'1'})['kos']
        self.assertEqual(report['held_values'],[49152])
        self.assertEqual(report['minimum_headroom'],4000)
        self.assertEqual(report['minimum_top'],3000)
        self.assertEqual(report['gate_verdict'],'NOT_EVALUATED')

    def test_fault_markers_separate_zero_counters_and_readiness(self):
        report=ae.summarize('CRASH_SCREEN: ready (fault, halt, 30 s hang)\nnative stream: missing=0 loads=8\nHALT=0 FAULT=0 MISSING=0\nmissing=2\nFAULT: address',{})['faults']
        self.assertEqual(report['count'],2)
        self.assertEqual(len(report['zero_counter_rows']),2)
        self.assertEqual(len(report['informational_marker_rows']),1)

    def test_bom_logs_decode_without_nul(self):
        self.assertEqual(ae.text_bytes('SCNDEDUP3 room=100'.encode('utf-16')),'SCNDEDUP3 room=100')
        self.assertEqual(ae.text_bytes(b'\xef\xbb\xbfTEXCHK fails=0'),'TEXCHK fails=0')

    def test_audit_pins_capture_binding_and_incomplete_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cap=root/'capture';cap.mkdir();base=root/'base';base.mkdir()
            fixture=root/'fixture.txt';fixture.write_bytes(b'room 0x100\r\n')
            wire=b'room 0x100\n';files={}
            for name in ('re4dc-game.elf','candidate.txt','stack.txt','resolved-knobs.txt','syms.txt'):
                path=root/name;path.write_text('TEX_CHECK=0\nSCENERY_DEDUP=3\n' if name=='resolved-knobs.txt' else name)
                files[name]=ae.pin(path)
            plan=root/'plan.json';plan.write_text(json.dumps({'arms':{'on':{'program':{'files':files}}}}))
            (base/'base.json').write_text(json.dumps({'elf':str(root/'re4dc-game.elf')}))
            result={'status':'INCOMPLETE','seconds':60,'emu':'harness','disc':str(base),'fixtures':{'warp':{'bytes':len(wire),'sha256':hashlib.sha256(wire).hexdigest()}}}
            (cap/'run-result.json').write_text(json.dumps(result));(cap/'run-output.txt').write_text(MOVIE)
            args=SimpleNamespace(capture=cap,program_plan=plan,arm='on',fixture=fixture,fixture_sha256=ae.pin(fixture)['sha256'],base_json=base/'base.json',track_sha256=None,expected_emu='console')
            report=ae.audit(args)
            self.assertFalse(report['identity_errors'])
            self.assertTrue(report['programme_pins_verified'])
            self.assertFalse(report['run']['emulator_matches'])
            self.assertEqual(len(report['warnings']),2)
            self.assertEqual(report['gate_verdict'],'NOT_EVALUATED')
            (root/'re4dc-game.elf').write_text('different')
            report=ae.audit(args)
            self.assertIn('Programme pin mismatch: re4dc-game.elf',report['identity_errors'])
            self.assertEqual(report['observations']['texchk']['state'],'UNVERIFIED_PROGRAMME')
            result['disc']=str(root/'other');(cap/'run-result.json').write_text(json.dumps(result))
            self.assertIn('Capture disc path differs from explicit base manifest directory',ae.audit(args)['identity_errors'])

    def test_exact_screenshot_inventory_is_only_file_hashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shots=root/'shots';shots.mkdir()
            # Byte sentinel tests inventory hashing; no rendered media is generated.
            shot=shots/'sentinel.png';shot.write_bytes(b'inventory-only')
            (shots/'notes.txt').write_text('excluded')
            inventory,notes=ae.screenshot_inventory(root)
            self.assertFalse(notes)
            self.assertEqual(len(inventory),1)
            self.assertEqual(inventory[0]['relative_path'],'shots/sentinel.png')
            self.assertEqual(inventory[0]['sha256'],hashlib.sha256(b'inventory-only').hexdigest())


if __name__=='__main__':unittest.main()
