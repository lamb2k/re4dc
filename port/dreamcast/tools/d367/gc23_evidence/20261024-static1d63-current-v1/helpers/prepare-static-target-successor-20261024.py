from pathlib import Path
import hashlib,json
own=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-port23')
old='77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22'
new='1d63cffe3a232c402418f2f2d919e7abae476957'
prior='/dev/shm/gc-port23-current-77d8a20b2-jx_x05a2/report.json'
s=(own/'static-target-current-20261024.py').read_text()
s=s.replace("if expected != '"+old+"'", "if expected != '"+new+"'")
s=s.replace("    if os.environ.get('GCGATE_PRIOR_REPORT'):raise RuntimeError('Fresh baseline required; no prior-object reuse')", "    if os.environ.get('GCGATE_PRIOR_REPORT') != '"+prior+"':raise RuntimeError('Only exact failed current-profile receipt allowed')")
s=s.replace("        prior = json.loads(prior_path.read_text())", "        if sha(prior_path) != '666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979':raise RuntimeError('Prior receipt changed')\n        prior = json.loads(prior_path.read_text())\n        if prior['source'] != '"+old+"' or prior.get('complete') or prior['harness_source_sha256'] != '6f8f984ed689ee8c0c0701d054f15c7a276b0f8d9d59c475cf3f15e4322935ba':raise RuntimeError('Unrecognized prior attempt')\n        if len(prior['objects']) != 51 or len(prior['off_identity']) != 12 or not all(prior['off_identity'].values()):raise RuntimeError('Prior attempt not expected partial matrix')")
s=s.replace("scope_version='STATIC77_CURRENT_FB_NO_REUSE'", "scope_version='STATIC1D63_CURRENT_FB_PINNED_CONTINUATION'")
s=s.replace("            used=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file())", "            used=sum(p.stat().st_size for root in [scratch,Path('"+prior+"').parent] for p in root.rglob('*') if p.is_file())")
s=s.replace("    report['complete'] = True", "    if len(report.get('off_identity',{})) !=14 or not all(report['off_identity'].values()):raise RuntimeError('OFF target mismatch')\n    report['prior_report_sha256']='666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979'\n    report['complete'] = True")
compile(s,'static-target-successor-20261024.py','exec')
(own/'static-target-successor-20261024.py').write_text(s,newline='\n')
sh=(own/'static-target-current-20261024.sh').read_text().replace(old,new).replace('static-target-current-20261024','static-target-successor-20261024')
sh=sh.replace('unset GCGATE_PRIOR_REPORT', "export GCGATE_PRIOR_REPORT='"+prior+"'")
(own/'static-target-successor-20261024.sh').write_text(sh,newline='\n')
receipt=dict(source=new,prior_source=old,prior_report_sha256='666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979',harness_sha256=hashlib.sha256(s.encode()).hexdigest(),wrapper_sha256=hashlib.sha256(sh.encode()).hexdigest(),scope='Same14units/fivehelpers/67arms. Reuse only exact current-profile failed-attempt objects with immutable report, SDK/profile, ALL input, object/stripped and normalized actual compiler command pins. Changed native_static inputs recompile. Combined RAM scratch256MiB, C floor24GiB. No link/guest.',status='PREPARED_ONLY')
(own/'STATIC-TARGET-SUCCESSOR-PREPARATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))