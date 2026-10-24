"""Seal the two actual final GDIs after the six authorized probes; no guest launch."""
from pathlib import Path
import importlib.util,json,re,shutil,subprocess
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('media',HERE/'media.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
 m.sealed();m.check_inputs();gates={};disc={};man={}
 cp=m.read(m.P/'compare-both.json');assert cp['normalized_profile_differences']=={'SCENERY_SELECT_LEAN2':['0','1'],'SCENERY_EMIT_PREFETCH':['0','1']}
 off=m.read(m.P/'compare-off.json');assert off['normalized_profile_differences']=={} and all(off['programme_byte_equal'].values())
 for arm in ['off','both']:
  disc[arm]=m.read(m.E/arm/'FINAL-READBACK.json');man[arm]=m.read(m.E/arm/'final-readback-manifest.json');assert man[arm]==m.read(m.E/(arm+'-expected-manifest.json'))
  for name,pin in disc[arm]['tracks'].items():assert m.row(m.FINAL[arm]/'gdemu'/name)==pin
  assert not (m.E/'probe-bases'/arm/'track03.iso').exists();assert (m.E/arm/'DELETED-PROXY-ISO.json').exists()
  gates[arm]={}
  for gate in ['boot','menu-warp','h2']:
   cap=m.E/'captures'/(arm+'-'+gate);path=cap/('QUALIFIED-AUTOTELEPORT.json' if (cap/'QUALIFIED-AUTOTELEPORT.json').exists() else 'QUALIFIED.json');q=m.read(path);assert q['pass']
   assert m.row(cap/'run-output.txt')==q['run_output'];b=m.read(cap/'bounded-launch.json');r=m.read(cap/'run-result.json')
   assert b['guest_exited'] and not b['deadline_fired'] and b['deadline_seconds']==55 and b['guest_observed_elapsed_s']<55
   assert r['emu']=='console' and r['status']=='RUN_COMPLETE' and not r['errors']
   gates[arm][gate]=dict(receipt=str(path),identity=m.row(path),observed=q['observed'],guest_seconds=b['guest_observed_elapsed_s'],mode=q['mode'])
  assert disc[arm]['candidate']==dict(size=32912,sha256=m.CSHA)
  assert disc[arm]['tex_pak']==m.read(m.E/'original-manifest.json')['dc/tex.pak']
 diff={k for k in set(man['off'])|set(man['both']) if man['off'].get(k)!=man['both'].get(k)}
 assert diff=={'1ST_READ.BIN'}|{k for k in man['off'] if re.fullmatch(r'dc/[^/]+\.ovl',k)} and len(diff)==15
 assets={a:{k:v for k,v in man[a].items() if k not in diff} for a in man};assert assets['off']==assets['both']
 commonhash=m.hashlib.sha256(json.dumps(assets['off'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
 readme='''# Private WorldEmit QA pair — source 49ad20f9

This pair is prepared for private console performance and look feedback, pending root review. It is not production ready. Neither experimental switch has a hardware speed gain established by these QA checks. Both switches remain off outside this private profile.

Off uses SCENERY_SELECT_LEAN2=0 and SCENERY_EMIT_PREFETCH=0. Both uses 1 and 1. The complete resolved comparison differs in exactly those two switches. OFF reproduces the fresh, unmodified source-49ad QA reference main and all 14 overlays; QA changes code, so this is not a production-main identity claim.

Both discs contain the same original release assets, all 41 existing Ganado textures without pruning, and unchanged dc/tex.pak. The sole private game-asset addition is dc/tex/7/7d4e1e92-052bdc2e.re4tex, 32912 bytes, SHA256 18978dc1b97247dcd5fda5f5f1744b74e9d1b97c34dc5779977525b0a2dc477e. This PS2 candidate is LOAD/UPLOAD REPAIR ONLY. Actual visible use remains unproven; Mendez hair appearance is not production approved. No GameCube pixel or geometry fallback is enabled. The normal QA menu and 33 presets are also included. No injected warp/pad/w11 fixture is present on these final discs.

Source is 49ad20f9932d638ddb7becf5db6f86b92e0a76a2. Current recipe and all four audit fixes are retained, with STAT_ROUTINE_BYTES=1 and EM_READ_RETRY=1. SELECT_ONLY, REPLAY_LEAN and SUBMIT_BATCH remain 1. Arena, CPU/actor backface, dedup, actor setup lean, UV snapshot and PVS remain 0. Quality default 1, QUALITY_LOD_PX=5 and FAR_LOD=4 resolve to threshold 20; cap 4. QA_MENU=1, WARP_AFTER_RESET=1, QA_TEST=23, QA_SRC=49ad20f9; world/phase meters and 60-tick reporting enabled; PC sampler, KOS squeeze and KOS watch disabled.

Each actual standard raw-2352 final GDI passed full file readback, main plus all 14 overlays, menu/33 presets, candidate and tex.pak pins, and standard/loader layout checks. Its read-back raw main also re-scrambles to the sealed QA CD programme. Each actual final GDI booted through ordinary PID-targeted input, with no warp injection. The additional automated QA menu-warp and full H2 movie checks used separately labelled fixture proxy bases with the same programme/all 14 overlays/full assets, differing only in three harness fixture files. They are not manual progression or final-GDI movie tests. All six Flycast console-mode child processes exited before their exact 55-second limit. These results do not establish physical-console acceptance, performance or whole-route correctness.

Root's separate source-profile gates (21 passes and three common Mendez texture failures) and the candidate's separate B-t load/upload repair result do not become QA Mendez acceptance. No Mendez test was run on this pair. Normal QA H2 reports its actual heap and restored loan only; it makes no KOS squeeze/watch or production heap-floor claim.

The new disposable fixture proxy ISOs were removed only after each arm's three checks and a fresh final-media rehash. Programme files, base manifests, SHA/IP receipts, fixtures, logs and captures remain in the evidence folder. No prior evidence/base was deleted. Final disc contents and gate details are in IDENTITY.json and the linked evidence receipt. No ZIP, publication or SD copy was made.
'''
 steps='''# Private console comparison

1. Use the Off and Both folders separately. Record the arm in every photo because the on-screen QA source label is shared. Keep the same console, video mode, controller, VMU, quality, view distance and QA world-cut settings for both.
2. At boot choose TELEPORT, CHAPTER 1-1, then R101 VILLAGE SQUARE, BY THE CROSS. Let the view settle without moving. Keep the source quality defaults: effective LOD threshold 20 and cap 4. Leave opaque/translucent/shell controls at their source defaults and PVS off.
3. Hold L + R + D-pad Down to open the QA menu. Open DIAGNOSTICS. Photograph the visible FPS and world/phase rows; X opens the QR snapshot pages. Photograph each page, with the arm and scene identified. ms10 values are tenths of a millisecond. Resume with B/RESUME, allow a fresh settled interval, and take three samples per arm.
4. Repeat at the same house-wall position and direction on both discs. Include a wide scene photo to make the camera reproducible. Report visual differences, freezes, missing objects or read problems alongside the readings. Do not change quality or culling options between arms.
5. Optional look feedback: compare the same Mendez view if reached. The shared private texture is a load/upload repair candidate only; visible hair use and appearance remain unapproved. Do not treat the supplied H2 or boot checks as a Mendez pass.

These are a request for private physical-console observations. No hardware speed increase is claimed in advance. Use the normal QA menus; no desktop emulator launcher or SD-copy script is supplied.
'''
 for arm in ['off','both']:
  root=m.FINAL[arm]
  with (root/'README.md').open('x') as f:f.write(readme)
  with (root/'STEPS.md').open('x') as f:f.write(steps)
  ident=dict(source=m.SOURCE,arm=arm,experimental_switches={'SCENERY_SELECT_LEAN2':int(arm=='both'),'SCENERY_EMIT_PREFETCH':int(arm=='both')},production_enabled=False,physical_console_acceptance=False,hardware_gain_claim=False,qa_mendez_tested=False,look_approved=False,programme_seal=m.SEAL,plan=m.row(m.E/'PLAN.json'),programme_readback=disc[arm],common_asset_manifest_sha256=commonhash,full_manifest=m.row(m.E/arm/'final-readback-manifest.json'),gates=gates[arm],evidence=str(m.E),root_review='PENDING',readme=m.row(root/'README.md'),steps=m.row(root/'STEPS.md'))
  m.fresh(root/'IDENTITY.json',ident)
  files={str(p.relative_to(root)):m.row(p) for p in root.rglob('*') if p.is_file()}
  with (root/'SHA256SUMS.txt').open('x') as f:
   for k,v in sorted(files.items()):f.write(v['sha256']+'  '+k+'\n')
 final=dict(source=m.SOURCE,status='All allocated staging and six QA probes complete; private pair pending root review',private_only=True,production_ready=False,physical_console_acceptance=False,hardware_gain_claim=False,qa_mendez_tested=False,root_review='PENDING',original_manifest=m.row(m.E/'original-manifest.json'),common_manifest=m.row(m.E/'common-manifest.json'),asset_identity_equal=True,programme_differences=sorted(diff),off_qa_reproduction=m.row(m.P/'compare-off.json'),only_two_switches=m.row(m.P/'compare-both.json'),gates=gates,final_paths={a:str(p) for a,p in m.FINAL.items()},identities={a:m.row(p/'IDENTITY.json') for a,p in m.FINAL.items()},sha256sums={a:m.row(p/'SHA256SUMS.txt') for a,p in m.FINAL.items()},actual_final_bytes=sum(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) for root in m.FINAL.values()),floor=m.floor(),finalizer=m.row(Path(__file__)))
 m.fresh(m.E/'FINAL-PAIR-HANDBACK.json',final)
 files={str(p.relative_to(m.E)):m.row(p) for p in m.E.rglob('*') if p.is_file() and p.name!='own-guest.lock'}
 m.fresh(m.E/'EVIDENCE-SHA256-MANIFEST.json',dict(source=m.SOURCE,files=files))
 print(json.dumps(dict(handback=str(m.E/'FINAL-PAIR-HANDBACK.json'),sha256=m.sha(m.E/'FINAL-PAIR-HANDBACK.json'),evidence_seal=m.sha(m.E/'EVIDENCE-SHA256-MANIFEST.json'),gates={a:{g:x['guest_seconds'] for g,x in rows.items()} for a,rows in gates.items()},floor=final['floor'])))

if __name__=='__main__':main()
