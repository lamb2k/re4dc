"""Host-only controls. Fake nested reader records calls; it is not a guest."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import capsule
import console_guard as g

REPO = Path(__file__).resolve().parents[5]


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rr-guard-host-')
        self.cap = Path(self.tmp.name)
        shutil.copyfile('/bin/sleep', self.cap / 'flycast.exe')
        (self.cap / 'flycast.exe').chmod(0o700)
        (self.cap / 'emu.cfg').write_text('host-only config\n')

    def tearDown(self):
        self.tmp.cleanup()

    def guard(self, deadline=.2, free=lambda: 10**20, popen=None):
        # Actual ordinary host child; replace disc.gdi with a numeric sleep delay
        # only within this host adapter, leaving production invocation validation.
        def host_popen(args, *a, **kw):
            return subprocess.Popen([args[0], '.04'], *a, **kw)
        return g.ChildGuard(self.cap, g.sha(self.cap/'flycast.exe'), free,
                            deadline=deadline, popen=popen or host_popen)

    def launch(self, guard):
        return guard.launch([str(self.cap/'flycast.exe'), 'disc.gdi'], cwd=self.cap)

    def test_actual_short_child_and_saved_cfg(self):
        guard=self.guard(); self.launch(guard).wait(); d=guard.finish()
        self.assertEqual(d['status'], 'PROCESS_GUARD_PASS')
        self.assertLess(d['observed_child_elapsed_upper_s'], .2)
        self.assertEqual((self.cap/'emu.cfg').read_bytes(), (self.cap/'bounded-launch-emu.cfg').read_bytes())
        self.assertFalse(d['runtime_qualified'])

    def test_actual_deadline_handle_only(self):
        unrelated=subprocess.Popen(['/bin/sleep', '2'])
        def slow(args, *a, **kw): return subprocess.Popen([args[0], '2'], *a, **kw)
        guard=self.guard(.05, popen=slow)
        try:
            self.launch(guard).wait(timeout=1)
            self.assertEqual(guard.finish()['reason'], 'CHILD_DEADLINE')
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate(); unrelated.wait()

    def test_low_floor_refuses_before_child(self):
        guard=self.guard(free=lambda:0)
        with self.assertRaisesRegex(ValueError,'floor'): self.launch(guard)
        self.assertIsNone(guard.child)

    def test_floor_monitor_failure_fails_closed(self):
        count=[0]
        def free():
            count[0]+=1
            if count[0]>1: raise OSError('unavailable')
            return 10**20
        def slow(args,*a,**kw): return subprocess.Popen([args[0], '2'], *a, **kw)
        guard=self.guard(free=free,popen=slow); self.launch(guard).wait(timeout=1)
        self.assertEqual(guard.finish()['reason'],'FLOOR_MONITOR_FAILED')

    def test_wrong_executable_and_foreign_path(self):
        guard=self.guard(); guard.console_sha='0'*64
        with self.assertRaisesRegex(ValueError,'console'): self.launch(guard)
        with self.assertRaisesRegex(ValueError,'foreign'): guard.launch(['/other/flycast.exe','disc.gdi'])

    def test_no_guest_and_second_guest(self):
        self.assertEqual(self.guard().finish()['reason'],'NO_GUEST')
        guard=self.guard(); p=self.launch(guard)
        try:
            with self.assertRaisesRegex(ValueError,'second'): self.launch(guard)
        finally: p.wait(); guard.finish()

    def test_legacy_profile_and_unplanned_arguments_refused(self):
        cfg=dict(profile=g.PROFILE,source=g.HEAD,status='PENDING')
        with self.assertRaisesRegex(ValueError,'reviewed'): g.validate_request(cfg,['--cap','never','--seconds','53'])
        cfg.update(status='ROOT_REVIEWED_CURRENT_HEAD_INPUTS',console_sha256=g.CONSOLE_SHA,
                   base_cfg_sha256=g.BASE_CFG_SHA,expected_runs={})
        with self.assertRaisesRegex(ValueError,'observation'): g.validate_request(cfg,['--cap','never','--seconds','60'])
        with self.assertRaisesRegex(ValueError,'unplanned'): g.validate_request(cfg,['--cap','never','--seconds','53'])

    def test_only_snapshotted_owned_track_can_be_unlinked(self):
        track=self.cap/'track03.iso'; track.write_bytes(b'HOST ONLY')
        guard=self.guard(); p=self.launch(guard); p.wait(); guard.finish()
        with self.assertRaisesRegex(ValueError,'foreign'): guard.unlink_track(self.cap/'emu.cfg',Path.unlink)
        with self.assertRaisesRegex(ValueError,'foreign'): guard.unlink_track(self.cap.parent/'foreign.iso',Path.unlink)
        old=self.cap/'retained-old.iso'; track.rename(old); track.write_bytes(b'FOREIGN')
        with self.assertRaisesRegex(ValueError,'changed'): guard.unlink_track(track,Path.unlink)
        self.assertTrue(track.exists()); self.assertTrue(old.exists())
        track.unlink(); old.rename(track)
        guard.unlink_track(track,Path.unlink)
        self.assertFalse(track.exists())

    def test_unfinished_child_fails(self):
        def slow(args,*a,**kw): return subprocess.Popen([args[0], '2'], *a, **kw)
        guard=self.guard(popen=slow); self.launch(guard)
        self.assertEqual(guard.finish()['reason'],'HARNESS_LEFT_CHILD')


class CapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='rr-capsule-host-')
        cls.root=Path(cls.tmp.name)
        cls.out=cls.root/'capsule'
        cls.manifest=capsule.prepare(REPO,cls.out)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_exclusive_capsule_and_unchanged_reference(self):
        with self.assertRaises(ValueError): capsule.prepare(REPO,self.out)
        self.assertFalse(self.manifest['automatic_cycle_enabled'])
        for name in ('rr-cycle.sh','rr-judge.py','recipe.conf','rr-qa-tier.sh'):
            self.assertEqual((self.out/'installed-reference'/(name+'.REFERENCE')).read_bytes(),
                             (Path('/root/rr/bin')/name).read_bytes())
        self.assertFalse((self.out/'bin/rr-cycle.sh').exists())

    def test_shape_drift_and_full_tier_refused(self):
        with self.assertRaises(ValueError): capsule.patch_kos('changed source')
        with self.assertRaises(ValueError): capsule.patch_gd('changed source')
        self.assertIn('[ "$TIER" = quick ] || [ "$TIER" = qa ] || exit 2',
                      (self.out/'bin/rr-jobs.sh').read_text())

    def test_live_lease_requires_real_canonical_lock(self):
        cfg=self.root/'cfg'; cfg.write_text('{}')
        lease=self.root/'fake-lease'
        st=capsule.RR_LOCK.stat()
        lease.write_text(json.dumps(dict(pid=os.getpid(),fd=999,start_ticks=capsule.start_ticks(os.getpid()),
                                  config_sha256=g.sha(cfg),lock_identity=[st.st_dev,st.st_ino])))
        with self.assertRaises((ValueError,OSError)): capsule.live_lease(lease,cfg)

    def test_incomplete_whole_cycle_phase_refuses_before_lock(self):
        cfg=self.root/'whole-cycle-refuse.json'
        cfg.write_text(json.dumps(dict(profile=g.PROFILE,source=g.HEAD,status='ROOT_REVIEWED_CURRENT_HEAD_INPUTS',
                       admission=dict(release_priority_granted=True,phase='PREPARED_QUICK_QA_ONLY'))))
        with self.assertRaisesRegex(ValueError,'whole-cycle'): capsule.hold(cfg,[])

    def test_real_tiny_flock_receipt_and_stale_config(self):
        import fcntl
        cfg=self.root/'lease-cfg'; cfg.write_text('{}')
        lockpath=self.root/'tiny-test.lock'
        with lockpath.open('a') as fd, mock.patch.object(capsule,'RR_LOCK',lockpath):
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            st=os.fstat(fd.fileno())
            receipt=self.root/'tiny-live.json'
            receipt.write_text(json.dumps(dict(pid=os.getpid(),fd=fd.fileno(),start_ticks=capsule.start_ticks(os.getpid()),
                  config_sha256=g.sha(cfg),lock_identity=[st.st_dev,st.st_ino])))
            self.assertEqual(capsule.live_lease(receipt,cfg)['pid'],os.getpid())
            cfg.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'changed'): capsule.live_lease(receipt,cfg)

    def test_duplicate_json_and_incomplete_audit_refuse(self):
        p=self.root/'duplicate.json'; p.write_text('{"status":"PASS","status":"FAIL"}')
        with self.assertRaisesRegex(ValueError,'duplicate'): g.load_json(p)
        with self.assertRaisesRegex(ValueError,'incomplete'):
            capsule.audit(dict(expected_runs={'cap':[]},capture_paths_wsl={}))
        with self.assertRaisesRegex(ValueError,'no expected'):
            capsule.audit(dict(expected_runs={},capture_paths_wsl={}))

    def test_all_actual_nested_shell_calls_route_to_private_reader(self):
        # Execute both actual current-head nested shell bodies with a fake Python
        # recorder, NOT Flycast. No real harness, large media or SDK is launched.
        stub=self.root/'stub'; stub.mkdir(exist_ok=True)
        calls=self.root/'nested.jsonl'
        python_stub='''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
if sys.argv[1:2]==['-c']:
 os.execv('/usr/bin/python3',['python3',*sys.argv[1:]])
a=sys.argv[1:]
with open(os.environ['HOST_CALLS'],'a') as f: f.write(json.dumps(a)+'\\n')
cap=Path(a[a.index('--cap')+1].replace('\\\\','/'));cap.mkdir(parents=True,exist_ok=True)
(cap/'run-output.txt').write_text('HOST-ONLY FAKE INPUT - NOT RUNTIME ACCEPTANCE\\nkos watch: headroom=8192 top=8192\\nkos squeeze: held=49152\\nwarp: alert at room frame\\nphase=enter room=103\\n')
(cap/'run-result.json').write_text('{}')
'''
        (stub/'python').write_text(python_stub); (stub/'python').chmod(0o700)
        (stub/'cygpath').write_text('#!/bin/bash\nprintf "%s\\n" "$2"\n'); (stub/'cygpath').chmod(0o700)
        (stub/'sleep').write_text('#!/bin/bash\nexit 0\n'); (stub/'sleep').chmod(0o700)
        (stub/'cat').write_text('#!/bin/bash\ncase "$1" in //wsl.localhost/*/syms.txt) echo "1 2 3";; *) exec /bin/cat "$@";; esac\n')
        (stub/'cat').chmod(0o700)
        env=dict(os.environ,PATH=str(stub)+':'+os.environ['PATH'],HOST_CALLS=str(calls),MAXP='1',SECS='999')
        f=self.out/'fullplay'
        for command in ([str(f/'kos_squeeze.sh'),'host-no-disc','host-no-twin',str(self.root/'kos'),'49152:0 49152:1','fight'],
                        [str(f/'gdemu_gate.sh'),'host',str(self.root/'gd'),'host-no-disc','1 2 3','-', '1']):
            subprocess.run(['bash',*command],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10)
        rows=[json.loads(x) for x in calls.read_text().splitlines()]
        self.assertEqual(len(rows),3)
        for a in rows:
            self.assertEqual(Path(a[0]), f/'fp_run.py')
            self.assertEqual(a[a.index('--seconds')+1],'53')
        self.assertEqual(sum('--stop' in a for a in rows),1)
        # Removing the duration patch is detected on the actual KOS call path.
        original=subprocess.check_output(['git','-C',str(REPO),'show',g.HEAD+':'+capsule.PREFIX+'fullplay/kos_squeeze.sh'],text=True)
        self.assertNotEqual(capsule.patch_kos(original),original)
        self.assertIn("'phase=enter room=103'", (f/'gdemu_gate.sh').read_text())
        # Actual-shell mutants: bypassing the wrapper and omitting the duration
        # refresh both yield an observable bad call, not a source-string oracle.
        mutant=self.root/'mutant'; mutant.mkdir()
        shutil.copytree(f/'segments',mutant/'segments')
        (mutant/'kos_squeeze.sh').write_text(original.replace('$here/fp_run.py','$here/_fp_run_original.py'))
        calls.write_text('')
        subprocess.run(['bash',str(mutant/'kos_squeeze.sh'),'host-no-disc','host-no-twin',str(self.root/'mutant-kos'),
                        '49152:0','fight'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10)
        bad=json.loads(calls.read_text().strip())
        self.assertEqual(bad[bad.index('--seconds')+1],'60')
        self.assertNotEqual(Path(bad[0]).name,'fp_run.py')



if __name__=='__main__': unittest.main()
