from pathlib import Path
import argparse,importlib.util,json,shutil
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('media',HERE/'media.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s=importlib.util.spec_from_file_location('auto_menu',HERE/'auto_menu.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
p=argparse.ArgumentParser();p.add_argument('action',choices=['correct','finish']);p.add_argument('arm',choices=['off','both']);v=p.parse_args();arm=v.arm
if v.action=='correct':
 cap=m.E/'captures'/(arm+'-menu-warp');old=m.read(cap/'QUALIFIED.json');text=(cap/'run-output.txt').read_text(errors='replace').replace('\0','')
 assert not old['pass'] and old['critical']==[] and old['launcher_rc']==0
 assert old['observed']==dict(menu33=True,room103=True,teleport=False)
 assert m.row(cap/'run-output.txt')==old['run_output']
 obs=a.observe(text);assert obs['ordered_auto_menu_chain'];neg=a.controls(text)
 source=m.TREE/'port/dreamcast/game/qa_menu.cpp';bridge=m.TREE/'port/dreamcast/game/dbgwarp_bridge.cpp'
 assert 're4dc_log("qa: auto teleport %s\\n", g_path);' in source.read_text()
 assert 'stamp(r == 1 ? "qa: teleport: soft reset requested"' in bridge.read_text()
 assert 'stamp("qa: preset armed at soft reset")' in bridge.read_text()
 result=dict(old,observed=obs,**{'pass':True},supersedes=m.row(cap/'QUALIFIED.json'),reason='Original new checker expected manual log wording for authorized automated QA fixture. Exact source auto-menu/reset/new-generation chain now required. No guest rerun.',negative_controls=neg,source_pins={str(x.relative_to(m.TREE)):m.row(x) for x in [source,bridge]},checker=m.row(HERE/'auto_menu.py'))
 m.fresh(cap/'QUALIFIED-AUTOTELEPORT.json',result);print(json.dumps(dict(arm=arm,corrected=True,negative_controls=neg,source_chain=obs)))
else:
 m.sealed();assert (m.E/arm/'FINAL-READBACK.json').exists()
 for gate in ['boot','menu-warp','h2']:
  cap=m.E/'captures'/(arm+'-'+gate);q=cap/'QUALIFIED.json'
  if gate=='menu-warp' and (cap/'QUALIFIED-AUTOTELEPORT.json').exists():
   corrected=m.read(cap/'QUALIFIED-AUTOTELEPORT.json');assert corrected['supersedes']==m.row(q)
   assert corrected['observed']['ordered_auto_menu_chain'] and not any(corrected['negative_controls'].values());q=cap/'QUALIFIED-AUTOTELEPORT.json'
  assert m.read(q)['pass'] is True
 proxy=m.E/'probe-bases'/arm
 shutil.copyfile(m.BASE/'IP.BIN',proxy/'IP-source.BIN');assert m.row(proxy/'IP-source.BIN')==m.row(m.BASE/'IP.BIN')
 # Fresh full final track hashes authenticate the still-present final disc before deleting this new disposable cache.
 saved=m.read(m.E/arm/'FINAL-READBACK.json')
 for name,pin in saved['tracks'].items():assert m.row(m.FINAL[arm]/'gdemu'/name)==pin,name
 p=proxy/'track03.iso';assert p.resolve()==p and p.parent==m.E/'probe-bases'/arm
 assert m.row(p)==m.read(m.E/arm/'PROXY-IDENTITY.json')['track03']
 m.fresh(m.E/arm/'DELETED-PROXY-ISO.json',dict(path=str(p.resolve()),identity=m.row(p),label='Disposable new owned fixture ISO cache only',reason='All three QA arm gates and final independent GDI readback passed. All old evidence and final media preserved.',retained_IP=m.row(proxy/'IP-source.BIN'),qualifications={g:m.row(m.E/'captures'/(arm+'-'+g)/('QUALIFIED-AUTOTELEPORT.json' if g=='menu-warp' and (m.E/'captures'/(arm+'-'+g)/'QUALIFIED-AUTOTELEPORT.json').exists() else 'QUALIFIED.json')) for g in ['boot','menu-warp','h2']}))
 p.unlink();print(json.dumps(dict(arm=arm,deleted=str(p),floor=m.floor())))
