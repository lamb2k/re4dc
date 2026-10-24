"""Independent V2 controls. Tiny owned files/fake handles only; no real guest."""
import ast, copy, hashlib, io, json, os
from pathlib import Path
import subprocess, sys, tempfile, time, types, unittest
from unittest import mock

SRC=Path('/root/probe/rr-safe-cycle23/port/dreamcast/tools/d367/rr_safe_cycle23')
sys.path.insert(0,str(SRC))
import console_guard as g
import capsule as c
OUT=Path(__file__).resolve().parent
BOOT=OUT.parent/'boot-cand-fb254e82-v2'
TEMPLATE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par/emu.cfg')
COMMIT='34a5c48bfe22c3d9718810166407048a906b8bcc'

def actual_reader_cfg(text, port):
    """Execute only exact cfg construction statements from pinned stock source."""
    stock=(BOOT/'capsule/fullplay/_fp_run_original.py').read_text()
    lines=stock.splitlines(True)
    tree=ast.parse(stock)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    begin=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='cfg')
    end=next(i for i in range(begin,len(main.body)) if isinstance(main.body[i],ast.Expr) and ast.unparse(main.body[i].value).startswith("(cap / 'emu.cfg').write_text(cfg)"))
    fragment=ast.Module(body=main.body[begin:end+1],type_ignores=[])
    with tempfile.TemporaryDirectory() as t:
        cap=Path(t); (cap/'emu.cfg').write_text(text)
        env={'FP_NOLIMIT':'0','RE4DC_EMU':'console'}
        namespace=dict(cap=cap,port=port,a=types.SimpleNamespace(align=False),re=__import__('re'),
                       os=types.SimpleNamespace(environ=env),Path=Path)
        exec(compile(fragment,'<exact stock cfg statements>','exec'),namespace)
        return (cap/'emu.cfg').read_text()

class Controls(unittest.TestCase):
    def setUp(self): self.template=TEMPLATE.read_text()

    def test_exact_source_and_pending_capsule(self):
        self.assertEqual(subprocess.check_output(['git','-C',str(SRC.parents[4]),'rev-parse','HEAD'],text=True).strip(),COMMIT)
        cfg=g.load_json(BOOT/'ROOT-REVIEW-PENDING.json')
        self.assertEqual(cfg['adapter_source_commit'],COMMIT)
        manifest=g.load_json(BOOT/'capsule/CAPSULE.json')
        self.assertEqual(g.sha(BOOT/'capsule/CAPSULE.json'),cfg['capsule_manifest_sha256'])
        for rel,digest in manifest['files'].items(): self.assertEqual(g.sha(BOOT/'capsule'/rel),digest)
        for name in ['capsule.py','console_guard.py']: self.assertEqual((BOOT/'capsule'/name).read_bytes(),(SRC/name).read_bytes())
        self.assertEqual(g.sha(TEMPLATE),g.BASE_CFG_SHA)
        self.assertEqual(cfg['profile'],g.PROFILE)

    def test_actual_template_and_exact_stock_gdb_vsync_edits(self):
        for port in [3263,3301,3399]:
            before=actual_reader_cfg(self.template,port)
            self.assertEqual(g.config_values(before)['config']['debug.gdbport'],str(port))
            self.assertEqual(g.config_values(before)['config']['rend.vsync'],'no')
            after=g.enforce_limited_text(before,self.template)
            self.assertEqual(after.count('aica.LimitFPS = yes'),1)
            self.assertEqual(g.enforce_limited_text(after,self.template),after)
            self.assertNotIn('aica.LimitFPS',self.template)

    def test_wrong_duplicate_foreign_malformed_and_scope_mutants_refuse(self):
        before=actual_reader_cfg(self.template,3263)
        variants=[before.replace('[config]','[config]\naica.LimitFPS = no'),
                  before.replace('[config]','[config]\naica.LimitFPS = yes\naica.limitfps = yes'),
                  before.replace('[input]','[input]\naica.LimitFPS = yes'),before+'[config]\n',before+'invalid\n',
                  before.replace('rend.EmulateFramebuffer = yes','rend.EmulateFramebuffer = no'),
                  before.replace('width = 640','width = 641'),before.replace('Debug.GDBPort = 3263','Debug.GDBPort = 3400'),
                  before.replace('rend.vsync = no','rend.vsync = yes')]
        for text in variants:
            with self.subTest(text=text[-60:]),self.assertRaises(ValueError): g.enforce_limited_text(text,self.template)
        for value in ['YES','true','1']:
            text=before.replace('[config]','[config]\naica.LimitFPS = '+value)
            self.assertEqual(g.config_values(g.enforce_limited_text(text,self.template))['config']['aica.limitfps'],'yes')

    def test_canonical_cfg_saved_before_mock_popen_and_drift_fails(self):
        with tempfile.TemporaryDirectory() as t:
            cap=Path(t); exe=cap/'flycast.exe'; exe.write_bytes(b'FAKE NOT EXECUTABLE')
            before=actual_reader_cfg(self.template,3301).encode(); (cap/'emu.cfg').write_bytes(before)
            child=mock.Mock(); child.poll.return_value=0
            def launch(*args,**kwargs):
                self.assertEqual(g.config_values((cap/'emu.cfg').read_text())['config']['aica.limitfps'],'yes')
                self.assertEqual((cap/'bounded-prelimit-emu.cfg').read_bytes(),before)
                self.assertEqual((cap/'bounded-launch-emu.cfg').read_bytes(),(cap/'emu.cfg').read_bytes())
                return child
            guard=g.ChildGuard(cap,g.sha(exe),lambda:100*g.GIB,popen=launch,template_text=self.template)
            with mock.patch.object(g.threading,'Thread'): guard.launch([str(exe),'disc.gdi'],cwd=cap)
            receipt=guard.finish(); self.assertEqual(receipt['status'],'PROCESS_GUARD_PASS')
            self.assertEqual(receipt['fps_limit']['before_sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(receipt['fps_limit']['after_sha256'],receipt['saved_launch_cfg_sha256'])
            self.assertEqual(receipt['fps_limit']['template_sha256'],g.BASE_CFG_SHA)
            (cap/'emu.cfg').write_text('foreign after launch')
            self.assertEqual(guard.finish()['reason'],'CONFIG_CHANGED_AFTER_LAUNCH')
            child.terminate.assert_not_called(); child.kill.assert_not_called()

    def test_bad_or_symlink_cfg_never_reaches_mock_popen(self):
        for symlink in [False,True]:
            with tempfile.TemporaryDirectory() as t:
                cap=Path(t); exe=cap/'flycast.exe'; exe.write_bytes(b'FAKE')
                text=actual_reader_cfg(self.template,3263)
                if symlink:
                    (cap/'foreign').write_text(text); (cap/'emu.cfg').symlink_to(cap/'foreign')
                else: (cap/'emu.cfg').write_text(text.replace('[config]','[config]\naica.LimitFPS = no'))
                launch=mock.Mock(side_effect=AssertionError('no real process'))
                guard=g.ChildGuard(cap,g.sha(exe),lambda:100*g.GIB,popen=launch,template_text=self.template)
                with self.assertRaises(ValueError): guard.launch([str(exe),'disc.gdi'],cwd=cap)
                launch.assert_not_called()
                self.assertFalse((cap/'bounded-prelimit-emu.cfg').exists())

    def test_explicit_fp0_required_before_harness(self):
        for requested in [{},{'FP_NOLIMIT':'1'},{'FP_NOLIMIT':'false'}]:
            env={'FP_NOLIMIT':'1','RE4DC_CONSOLE_DYNAREC':'no'}
            cfg=dict(_requested_env=requested,expected_env={'cap':requested})
            with (mock.patch.object(g,'os',types.SimpleNamespace(name='nt',environ=env)),mock.patch.object(g,'validate_request',return_value=Path('/fake')),
                  mock.patch.object(g.shutil,'disk_usage',return_value=types.SimpleNamespace(free=100*g.GIB)),mock.patch.object(g.runpy,'run_path') as run):
                with self.assertRaisesRegex(ValueError,'FP_NOLIMIT0'): g.run(cfg,['--cap','cap'])
                run.assert_not_called()

    def test_fp0_environment_and_pinned_template_reach_guard(self):
        with tempfile.TemporaryDirectory() as t:
            cap=Path(t); env={'FP_NOLIMIT':'1','RE4DC_CONSOLE_DYNAREC':'no','RE4DC_GD_PROFILE':'foreign'}
            cfg=dict(_requested_env={'FP_NOLIMIT':'0'},expected_env={'cap':{'FP_NOLIMIT':'0'}},template_cfg=str(TEMPLATE),
                     console='PINNED-CONSOLE',harness='PINNED-HARNESS',harness_sha256=g.HARNESS_SHA,input_pins={})
            guard=mock.Mock(); guard.finish.return_value=dict(status='PROCESS_GUARD_PASS')
            def harness(*args,**kwargs):
                self.assertEqual(env['FP_NOLIMIT'],'0'); self.assertEqual(env['RE4DC_EMU'],'console')
                self.assertEqual(env['RE4DC_CONSOLE_EXE'],'PINNED-CONSOLE')
                self.assertNotIn('RE4DC_CONSOLE_DYNAREC',env); self.assertNotIn('RE4DC_GD_PROFILE',env)
            with (mock.patch.object(g,'os',types.SimpleNamespace(name='nt',environ=env)),mock.patch.object(g,'validate_request',return_value=cap),
                  mock.patch.object(g.shutil,'disk_usage',return_value=types.SimpleNamespace(free=100*g.GIB)),
                  mock.patch.object(g,'ChildGuard',return_value=guard) as create,mock.patch.object(g.runpy,'run_path',side_effect=harness)):
                self.assertEqual(g.run(cfg,['--cap','cap']),0)
                self.assertEqual(create.call_args.kwargs['template_text'],self.template)
                guard.finish.assert_called_once_with()

    def test_audit_requires_both_fps_receipt_and_exact_launch_hash(self):
        with tempfile.TemporaryDirectory() as t:
            cap=Path(t); before=actual_reader_cfg(self.template,3263); (cap/'emu.cfg').write_text(before)
            fps=g.limit_owned_config(cap,self.template); after=(cap/'emu.cfg').read_bytes()
            (cap/'bounded-launch-emu.cfg').write_bytes(after)
            argv=['--seconds','45']; cfg=dict(expected_runs={'cap':argv},capture_paths_wsl={'cap':str(cap)},input_pins={},harness_sha256=g.HARNESS_SHA,console_sha256=g.CONSOLE_SHA)
            row=dict(status='PROCESS_GUARD_PASS',harness_rc=0,error=None,argv=argv,input_pins={},source=g.HEAD,profile=g.PROFILE,runtime_qualified=False,
                     harness_sha256=g.HARNESS_SHA,actual_console_sha256=g.CONSOLE_SHA,child_limit_s=55,observed_child_elapsed_upper_s=9.1,
                     saved_launch_cfg_sha256=hashlib.sha256(after).hexdigest(),fps_limit=fps)
            (cap/'bounded-console.json').write_text(json.dumps(row))
            (cap/'run-result.json').write_text(json.dumps(dict(emu='console',seconds=45,status='RUN_COMPLETE',errors=[])))
            (cap/'run-output.txt').write_text('host-only receipt control')
            self.assertEqual(c.audit(cfg)['status'],'PLANNED_PROCESS_BOUNDS_COMPLETE')
            broken=dict(fps,aica_LimitFPS='no'); (cap/'bounded-limitfps.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError,'FPS receipt'): c.audit(cfg)
            (cap/'bounded-limitfps.json').write_text(json.dumps(fps))
            (cap/'bounded-launch-emu.cfg').write_bytes(after+b'changed')
            with self.assertRaisesRegex(ValueError,'saved configuration'): c.audit(cfg)

    def test_title_goal_and_independent_negative_semantics(self):
        text='original title control\nstate title=1\n'
        row=dict(status='RUN_COMPLETE',errors=[],emu='console',seconds=45,stop='state title=',stopped='goal',stop_matched_s=4.2,elapsed_s=9.3)
        result=c.boot_semantics(text,row); self.assertEqual(result['status'],'BOOT_TITLE_GOAL_PASS')
        self.assertFalse(result['runtime_qualified']); self.assertTrue(result['process_bound_audit_required_separately'])
        changes=[{'status':'RUN_FAILED'},{'errors':['x']},{'emu':'harness'},{'seconds':53},{'stop':'other'},{'stopped':'reader'},
                 {'stop_matched_s':float('nan')},{'stop_matched_s':True},{'stop_matched_s':46},{'elapsed_s':8},
                 {'elapsed_s':float('inf')},{'early_emulator_exit':0},{'keys_pending':1}]
        for change in changes:
            bad=dict(row,**change); self.assertEqual(c.boot_semantics(text,bad)['status'],'FAIL',change)
        for badtext in ['no title','state title=1\nHALT','state title=1\nread failed','state title=1\nLOG OVERRUN',
                        'state title=1\nBAD-READ', 'state title=1\nDISCNOTE: disc: transfer late',
                        'state title=1\nDISCNOTE: snd: stream table bad']:
            self.assertEqual(c.boot_semantics(badtext,row)['status'],'FAIL')
        self.assertEqual(c.boot_semantics(text+'DISCNOTE: disc: init ok\n',row)['status'],'BOOT_TITLE_GOAL_PASS')

    def test_pending_config_and_whole_cycle_refuse_without_lock(self):
        cfgpath=BOOT/'ROOT-REVIEW-PENDING.json'; cfg=g.load_json(cfgpath)
        self.assertFalse(cfg['admission']['release_priority_granted']); self.assertFalse(cfg['execution_authorized'])
        with self.assertRaisesRegex(ValueError,'execution not admitted'): c.hold(cfgpath,cfg['admission']['command'])
        approved=copy.deepcopy(cfg); approved['status']='ROOT_REVIEWED_CURRENT_HEAD_INPUTS'; approved['admission'].update(release_priority_granted=True,phase='PREPARED_QUICK_QA_ONLY')
        with mock.patch.object(c,'load_json',return_value=approved),mock.patch.dict(os.environ,RR_LOCKED='1'):
            with self.assertRaisesRegex(ValueError,'whole-cycle'): c.hold(cfgpath,approved['admission']['command'])
        self.assertFalse(Path(cfg['lease_path']).exists())
        for path in cfg['capture_paths_wsl'].values(): self.assertFalse(Path(path).exists())

if __name__=='__main__':
    stream=io.StringIO(); start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    print(stream.getvalue())
    row=dict(status='PASS' if result.wasSuccessful() else 'FAIL',source_commit=COMMIT,methods=result.testsRun,elapsed_s=time.monotonic()-start,
             actual_guest=False,actual_process_kill=False,SDK=False,console_or_image_read=False,controls_sha256=g.sha(__file__),transcript=stream.getvalue())
    with open(OUT/'HOST-RESULTS.json','x') as f: json.dump(row,f,indent=2); f.write('\n')
    raise SystemExit(not result.wasSuccessful())
