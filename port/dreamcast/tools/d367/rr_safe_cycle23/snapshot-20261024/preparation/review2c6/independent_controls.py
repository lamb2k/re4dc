"""Read-only source review controls: fake handles, tiny temporary files, no guest."""
import copy, fcntl, hashlib, io, json, os
from pathlib import Path
import subprocess, sys, tempfile, time, unittest
from unittest import mock

SRC=Path('/root/probe/rr-safe-cycle23/port/dreamcast/tools/d367/rr_safe_cycle23')
sys.path.insert(0,str(SRC))
import capsule as c
import console_guard as g
import test_adapter as supplied
REVIEW=Path(__file__).resolve().parent

class Controls(unittest.TestCase):
    def test_sealed_source_and_receipt(self):
        lane=REVIEW.parent
        seal=g.load_json(lane/'SOURCE-SEAL.json')
        self.assertEqual(seal['source_commit'],'2c6c62b483553c0788e9d12a15048b2c85ce7b34')
        for name,row in seal['files'].items():
            self.assertEqual(g.sha(SRC/name),row['sha256'])
            self.assertEqual((SRC/name).stat().st_size,row['bytes'])
        self.assertEqual(g.sha(lane/'HOST-RESULTS.json'),seal['host_receipt_sha256'])

    def test_actual_tiny_flock_missing_stale_and_wrong_inode(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); cfg=p/'cfg'; cfg.write_text('{}'); lock=p/'lock'; lease=p/'lease'
            with lock.open('a') as fd, mock.patch.object(c,'RR_LOCK',lock):
                st=os.fstat(fd.fileno())
                d=dict(pid=os.getpid(),fd=fd.fileno(),start_ticks=c.start_ticks(os.getpid()),
                       lock_identity=[st.st_dev,st.st_ino],config_sha256=g.sha(cfg))
                lease.write_text(json.dumps(d))
                with self.assertRaisesRegex(ValueError,'does not hold'): c.live_lease(lease,cfg)
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(c.live_lease(lease,cfg)['pid'],os.getpid())
                for key,bad in [('start_ticks','0'),('lock_identity',[st.st_dev,st.st_ino+1]),('config_sha256','0'*64)]:
                    broken=dict(d); broken[key]=bad; lease.write_text(json.dumps(broken))
                    with self.assertRaises(ValueError): c.live_lease(lease,cfg)

    def test_whole_cycle_refused_even_with_bypass_environment(self):
        with tempfile.TemporaryDirectory() as t:
            cfg=Path(t)/'cfg'
            cfg.write_text(json.dumps(dict(profile=g.PROFILE,source=g.HEAD,status='ROOT_REVIEWED_CURRENT_HEAD_INPUTS',
                       admission=dict(release_priority_granted=True,phase='PREPARED_QUICK_QA_ONLY'))))
            with mock.patch.dict(os.environ,RR_LOCKED='1'), mock.patch.object(c,'verify_capsule') as verify:
                with self.assertRaisesRegex(ValueError,'whole-cycle'): c.hold(cfg,[])
                verify.assert_not_called()

    def test_manual_boot_mutations_refuse_before_any_lock(self):
        good=['--disc','C:/candidate/gdemu','--cap','C:/new','--syms','1 2 3','--seconds','45','--stop','state title=','--grace','5']
        variants=[good+['--warp','x'],good+['--pad','x'],good+['--base','x']]
        for key,bad in [('--seconds','53'),('--stop','different'),('--grace','15')]:
            a=list(good); a[a.index(key)+1]=bad; variants.append(a)
        for argv in variants:
            cfg=dict(profile=g.PROFILE,source=g.HEAD,status='ROOT_REVIEWED_CURRENT_HEAD_INPUTS',
                     admission=dict(release_priority_granted=True,phase='FINAL_GDI_BOOT_ONLY'),expected_runs={'cap':argv})
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/'cfg'; p.write_text(json.dumps(cfg))
                with mock.patch.object(c,'verify_capsule') as verify:
                    with self.assertRaises(ValueError): c.hold(p,[])
                    verify.assert_not_called()

    def test_no_guest_and_bad_launches_no_process(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'flycast.exe').write_bytes(b'FAKE NOT EXECUTABLE'); (p/'emu.cfg').write_text('tiny')
            spawn=mock.Mock(side_effect=AssertionError('no process allowed'))
            guard=g.ChildGuard(p,g.sha(p/'flycast.exe'),lambda:0,popen=spawn)
            self.assertEqual(guard.finish()['reason'],'NO_GUEST')
            for args,cwd in [([str(p/'flycast.exe'),'disc.gdi'],p),(['/other/flycast.exe','disc.gdi'],p),
                             ([str(p/'flycast.exe'),'wrong.gdi'],p),([str(p/'flycast.exe'),'disc.gdi'],p.parent)]:
                with self.assertRaises(ValueError): guard.launch(args,cwd=cwd)
            spawn.assert_not_called()

    def test_deadline_floor_monitor_exact_mock_handle(self):
        for why,clock,free in [('CHILD_DEADLINE',56,lambda:100*g.GIB),('C_ABSOLUTE_FLOOR',1,lambda:0),
                              ('FLOOR_MONITOR_FAILED',1,mock.Mock(side_effect=OSError('unavailable')))]:
            child=mock.Mock(); child.poll.return_value=None
            foreign=mock.Mock()
            guard=g.ChildGuard('/not-used','0'*64,free); guard.child=child; guard.started=0
            guard.stop=mock.Mock(); guard.stop.wait.return_value=False
            with mock.patch.object(g.time,'monotonic',return_value=clock): guard._watch()
            self.assertEqual(guard.reason,why); child.terminate.assert_called_once_with()
            child.kill.assert_not_called(); foreign.terminate.assert_not_called()

    def test_floor_and_console_hash_checked_before_spawn(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'flycast.exe').write_bytes(b'FAKE'); (p/'emu.cfg').write_text('tiny')
            spawn=mock.Mock()
            guard=g.ChildGuard(p,'0'*64,lambda:100*g.GIB,popen=spawn)
            with self.assertRaisesRegex(ValueError,'pinned console'): guard.launch([str(p/'flycast.exe'),'disc.gdi'],cwd=p)
            spawn.assert_not_called()

    def test_owned_link_manifest_and_foreign_identity_refusal(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'flycast.exe').write_bytes(b'FAKE'); (p/'emu.cfg').write_text('tiny')
            track=p/'track03.iso'; track.write_bytes(b'TINY HOST BYTES')
            child=mock.Mock(); child.poll.return_value=0
            guard=g.ChildGuard(p,g.sha(p/'flycast.exe'),lambda:100*g.GIB,popen=mock.Mock(return_value=child))
            with mock.patch.object(g.threading,'Thread'):
                guard.launch([str(p/'flycast.exe'),'disc.gdi'],cwd=p)
            d=g.load_json(p/'owned-capture-tracks.json')
            self.assertEqual(d['tracks']['track03.iso'],guard.owned_tracks['track03.iso'])
            callback=mock.Mock()
            for target in [p/'emu.cfg',p.parent/'track03.iso']:
                with self.assertRaises(ValueError): guard.unlink_track(target,callback)
            track.write_bytes(b'CHANGED LENGTH')
            with self.assertRaises(ValueError): guard.unlink_track(track,callback)
            callback.assert_not_called()

    def test_child_order_root3_then_trace16_then_revalidated_launch(self):
        cfg={'windows_python':'win','windows_python_wsl':'linux','input_pins':{'win':'0'*64},'guard_windows':'guard','config_windows':'cfgwin'}
        with mock.patch.object(c,'load_json',return_value=cfg),mock.patch.object(c,'live_lease'),mock.patch.object(c,'verify_capsule'),mock.patch.object(c,'verify_files'),mock.patch.object(c.subprocess,'call',return_value=0) as call:
            c.child('cfg','lease','payload')
            argv=call.call_args.args[0]
            self.assertTrue(argv[1].endswith('/stat-guest-slot.sh')); self.assertTrue(argv[3].endswith('/trace_lock.sh'))
            self.assertEqual(call.call_args.kwargs['env']['TRACE_SLOTS'],'16')
            self.assertEqual(call.call_args.kwargs['env']['RE4DC_MAX_FLYCASTS'],'16')
            call.reset_mock(); c.launch('cfg','lease','payload')
            self.assertEqual(call.call_args.args[0],['linux','guard','--config','cfgwin','--request','payload'])

    def test_actual_nested_shells_and_bad_duration_reader_mutant(self):
        # Reuse supplied behavioral route oracle without its prepare() fixture:
        # copy ONLY git source text and segments; do not hash console/data/executables.
        repo=SRC.parents[4]
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); out=root/'capsule'; f=out/'fullplay'; f.mkdir(parents=True)
            for name,patch in [('kos_squeeze.sh',c.patch_kos),('gdemu_gate.sh',c.patch_gd)]:
                body=subprocess.check_output(['git','-C',str(repo),'show',g.HEAD+':'+c.PREFIX+'fullplay/'+name],text=True)
                (f/name).write_text(patch(body))
            (f/'segments').mkdir()
            for name in ['kos-fight-warp.txt','door103-warp.txt']:
                data=subprocess.check_output(['git','-C',str(repo),'show',g.HEAD+':'+c.PREFIX+'fullplay/segments/'+name])
                (f/'segments'/name).write_bytes(data)
            case=supplied.CapsuleTests('test_all_actual_nested_shell_calls_route_to_private_reader')
            case.root=root; case.out=out
            case.test_all_actual_nested_shell_calls_route_to_private_reader()

    def test_duplicate_partial_over_deadline_receipts_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); bad=p/'dup'; bad.write_text('{"status":"PASS","status":"FAIL"}')
            with self.assertRaises(ValueError): g.load_json(bad)
            with self.assertRaises(ValueError): c.audit(dict(expected_runs={},capture_paths_wsl={}))
            with self.assertRaises(ValueError): c.audit(dict(expected_runs={'a':[]},capture_paths_wsl={}))
            argv=['--seconds','45']
            cfg=dict(expected_runs={'cap':argv},capture_paths_wsl={'cap':str(p)},input_pins={},harness_sha256='h',console_sha256='c')
            r=dict(status='PROCESS_GUARD_PASS',harness_rc=0,error=None,argv=argv,input_pins={},source=g.HEAD,profile=g.PROFILE,
                   runtime_qualified=False,harness_sha256='h',actual_console_sha256='c',child_limit_s=55,observed_child_elapsed_upper_s=55.001)
            (p/'bounded-console.json').write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'over bound'): c.audit(cfg)

if __name__=='__main__':
    stream=io.StringIO(); start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    print(stream.getvalue())
    receipt=dict(status='PASS' if result.wasSuccessful() else 'FAIL',source_commit='2c6c62b483553c0788e9d12a15048b2c85ce7b34',
                 methods=result.testsRun,elapsed_s=time.monotonic()-start,actual_guest=False,actual_process_kill=False,SDK=False,
                 console_or_image_read=False,controls_sha256=g.sha(__file__),transcript=stream.getvalue())
    with open(REVIEW/'HOST-RESULTS.json','x') as out: json.dump(receipt,out,indent=2); out.write('\n')
    raise SystemExit(not result.wasSuccessful())
