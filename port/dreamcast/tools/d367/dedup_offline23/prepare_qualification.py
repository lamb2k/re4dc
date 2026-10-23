#!/usr/bin/env python3
"""Read-only preflight and command plan for the frozen SDO3 Off/On qualification.

This never builds, stages, masters a disc or launches an emulator. It prints a
small JSON plan; --output writes that plan exclusively to an existing directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import struct
import zlib

# Final conservative data at source e66ec61e4. Earlier *-prototype data is rejected.
FILES = (
 ('r100','re4mesh',1537920,'19548f9d6b473b65ff634caefa45cdc907b86ec5a6f767357062c91ff2bd607b'),
 ('r101','re4mesh',1283520,'19c227e5215fcdf8935d24c091c16be4d7767a0b30beaeace2122b04d777bef5'),
 ('r103','re4mesh',1074688,'7785ad48983c33f0da8195453be0ba923acc5a1061036fce2d0bc3d11e241365'),
 ('r101','r4sg',117152,'c9b118b98a6c76fd8164d4b924be091342d4db3dd5ce89ecf30d9ae6cd8ff675'),
)
BASE = {
 'r100':'130bac7969255f0bf31d5f9226cee21a33415103f044f0fdc7dda3607ffc89bb',
 'r101':'500d17dac6279aa1ca71c8698ac31292cb2d3452befacfbef2d25069f9f7bff3',
 'r103':'96d2382299065c6ab48f7696a88e37de7020fd0a21e37507d4bb87a0a739fdd3',
}

# Frozen private compact outputs reviewed at runtime11109 (source metadata only).
STRIP_MANIFEST=Path(__file__).with_name('strip-share-private-pins.json')
STRIP_MANIFEST_SHA256='af246116c7d408c9b44b52a9400e1255122b62502ae0018b2808fcc4d47a5b10'
BASE_BYTES={room:size for room,ext,size,_ in FILES if ext=='re4mesh'}


def alternate_specs(root,strip_share=False):
    if not strip_share:
        return [(room,ext,size,digest,root/(room+'-linear')/('ps2-dd3.'+ext)) for room,ext,size,digest in FILES],None
    raw=STRIP_MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=STRIP_MANIFEST_SHA256:raise ValueError('Frozen strip-share manifest pin mismatch')
    rows=json.loads(raw)['variants'];specs=[]
    for row in rows:
        room=Path(row['input_path']).parent.name.removesuffix('-linear')
        directory=root/(room+'-stripshare-v1')
        if room not in BASE_BYTES or directory!=Path(row['output_directory']):raise ValueError('Frozen strip-share path mismatch')
        if row['source_bytes']!=BASE_BYTES[room] or row['input_bytes']!=BASE_BYTES[room]:raise ValueError('Frozen source extent mismatch')
        for name,info in row['files'].items():
            ext=name.removeprefix('ps2-dd3.')
            specs.append((room,ext,info['bytes'],info['sha256'],directory/name))
    expected={(room,ext) for room,ext,_,_ in FILES}
    if {(r,e) for r,e,_,_,_ in specs}!=expected or len(specs)!=4:raise ValueError('Expected exactly four compact alternates')
    return specs,pin(STRIP_MANIFEST)


def source_identity(original,alternate,strip_share=False):
    if min(len(original),len(alternate))<112:raise ValueError('Short package certificate')
    a=struct.unpack_from('<4s19I',original);b=struct.unpack_from('<4s19I',alternate)
    if a[0]!=b'R4IM' or a[1]!=3 or a[2]!=len(original) or a[16]!=2 or any(a[17:20]):raise ValueError('Original package header mismatch')
    if b[0]!=b'R4IM' or b[1]!=3 or b[2]!=len(alternate) or b[16]!=2 or b[19]!=int.from_bytes(b'SDO3','little'):raise ValueError('Alternate package header mismatch')
    if zlib.crc32(original[80:])!=a[3] or zlib.crc32(alternate[80:])!=b[3]:raise ValueError('Package body CRC mismatch')
    if b[18]!=a[3]:raise ValueError('Source certificate mismatch')
    extent=b[17] or len(alternate)
    if extent!=len(original):raise ValueError('Source extent mismatch')
    if strip_share and (b[17]!=len(original) or len(alternate)>=len(original)):raise ValueError('Compact source/physical extent mismatch')
    if not strip_share and (b[17] or len(alternate)!=len(original)):raise ValueError('Legacy byte-neutral extent mismatch')
    return dict(original_bytes=len(original),original_body_crc=a[3],alternate_physical_bytes=len(alternate),
                alternate_body_crc=b[3],declared_source_bytes=b[17],resolved_source_bytes=extent,meshlets=b[6])


def pin(path):
    path=Path(path)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def tool(root,name):
    p=root/name
    if not p.is_file():raise ValueError('Missing existing tool/fixture: '+str(p))
    return str(p)

def program(out,source,mode,label):
    if out is None:return dict(status='PENDING',reason='No program output directory supplied; no program pin claimed')
    if out.name!='out-'+label:raise ValueError('Program output does not match stage label: '+str(out))
    names=('re4dc-game.elf','candidate.txt','stack.txt','resolved-knobs.txt','syms.txt')
    missing=[n for n in names if not (out/n).is_file()]
    if missing:return dict(status='PENDING',path=str(out),missing=missing)
    stack=(out/'stack.txt').read_text().splitlines()
    if stack!=[source]:raise ValueError('Program is not from the exact clean source: '+str(out))
    knobs=dict(line.split('=',1) for line in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in line)
    if knobs.get('SCENERY_DEDUP')!=str(mode):raise ValueError('Program mode is not verified: '+str(out))
    if (out/'missing.txt').is_file() and (out/'missing.txt').stat().st_size:raise ValueError('Nonempty missing.txt: '+str(out))
    return dict(status='PINNED; target gates still pending',resolved={k:knobs.get(k,'not recorded') for k in ('SCENERY_DEDUP','TEX_CHECK','MCHECK_LEONGC','NATIVE_MODEL_REGISTRY_CENSUS','VRAM_ROOM_LOG','KOS_WATCH','KOS_SQUEEZE','W11_FIXTURE','QA_MENU')},files={n:pin(out/n) for n in names})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--source',required=True)
    ap.add_argument('--alternates',type=Path,required=True)
    ap.add_argument('--strip-share',action='store_true',help='Use the frozen compact strip-share-v1 manifest; legacy byte-neutral files remain the default')
    ap.add_argument('--baseline-native',type=Path,default=Path('/root/re4payload/t164-20261018/tree/dc/native'))
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--off-label',required=True);ap.add_argument('--on-label',required=True)
    ap.add_argument('--off-out',type=Path);ap.add_argument('--on-out',type=Path)
    ap.add_argument('--s30-fixture',type=Path,help='Exact existing world-scratch23 bounded post-ambush fixture; no copy or edit')
    ap.add_argument('--output',type=Path)
    a=ap.parse_args()
    for label in (a.off_label,a.on_label):
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{2,70}',label):raise ValueError('Unsafe/nonunique route label')
    if a.off_label==a.on_label:raise ValueError('Off and On labels must differ')
    source=subprocess.check_output(['git','-C',str(a.tree),'rev-parse','HEAD'],text=True).strip()
    if source!=a.source or not re.fullmatch('[0-9a-f]{40}',source):raise ValueError('Source HEAD mismatch')
    if subprocess.check_output(['git','-C',str(a.tree),'status','--porcelain','--untracked-files=no'],text=True):raise ValueError('Tracked source tree is dirty')
    d=a.tree/'port/dreamcast/tools/d367';recipe=d/'rr/recipe.conf'
    text=recipe.read_text();match=re.search(r'^DATA="([^"]+)"$',text,re.M)
    if not match:raise ValueError('No exact DATA assignment')
    data=match[1];chapter=re.search(r'^CH2="([^"]*)"$',text,re.M)
    if not chapter:raise ValueError('No exact CH2 assignment')
    ch2=chapter[1];exports={}
    for name,value in re.findall(r'^export ([A-Z][A-Z0-9_]*)=(.+)$',text,re.M):
        words=shlex.split(value,comments=True)
        if len(words)!=1 or any(c in words[0] for c in '$`'):raise ValueError('Recipe export requires explicit handling: '+name)
        exports[name]=words[0]
    alternates=[];sets=[];base_pins={};identities={}
    specs,strip_manifest=alternate_specs(a.alternates,a.strip_share)
    for room,ext,size,digest,p in specs:
        actual=pin(p)
        if actual['bytes']!=size or actual['sha256']!=digest:raise ValueError('Frozen alternate pin mismatch: '+str(p))
        dest=f'dc/native/{room}/ps2-dd3.{ext}'
        alternates.append(dict(destination=dest,**actual));sets.extend(['--set',dest+'='+str(p)])
        if ext=='re4mesh':
            base=a.baseline_native/room/'ps2-world.re4mesh';bp=pin(base)
            if bp['sha256']!=BASE[room] or bp['bytes']!=BASE_BYTES[room]:raise ValueError('Base package changed: '+str(base))
            old,new=base.read_bytes(),p.read_bytes()
            identities[room]=source_identity(old,new,a.strip_share)
            base_pins[room]=bp
    sg=next(Path(x['path']).read_bytes() for x in alternates if x['destination'].endswith('.r4sg'))
    w=struct.unpack_from('<4s7I',sg);mi=identities['r101']
    if w[:3]!=(b'R4SG',1,mi['meshlets']) or w[4]!=mi['alternate_body_crc'] or w[5]!=mi['alternate_physical_bytes'] or zlib.crc32(sg[32:])!=w[7]:raise ValueError('SG physical package binding mismatch')
    existing=('ch2/ch2-build.sh','test11/t11-fix.py','test8/t8-pkgtree.py',
              'stage_route.py','qa20/mkqa.py','mkgdi.sh','disc_lint.py','trace_lock.sh',
              'fullplay/fp_run.py','fullplay/kos_squeeze.sh','fullplay/gdemu_gate.sh',
              'fullplay/segments/h2-warp.txt','fullplay/segments/h2-pad.txt',
              'fullplay/segments/door103-warp.txt','scenery19/pix.py',
              'scenery19/k/still-r101-warp.txt','scenery19/k/still-r103-warp.txt',
              'castgc/warps/r100.txt','castgc/warps/r101.txt','castgc/warps/r103.txt')
    tools={name:tool(d,name) for name in existing}
    arms={}
    for name,label,out,mode in [('off',a.off_label,a.off_out,0),('on',a.on_label,a.on_out,3)]:
        fixture=a.work/'fix'/('pkg-'+label+'.json')
        argv=['python3',tools['test11/t11-fix.py'],label,str(fixture),'--base','payload','--data',data,*sets]
        arms[name]=dict(label=label,expected_knob=f'SCENERY_DEDUP={mode}',program=program(out,source,mode,label),
                        stage=dict(environment={**exports,'RE4DC_RESIDENT_STRICT':'1'},argv=argv),fixture=str(fixture),
                        pkgtree=dict(environment={'PKG_K':str(a.work/name)},argv=['python3',tools['test8/t8-pkgtree.py'],label,str(fixture)]))
    fragment=dict(status='PENDING: supply --s30-fixture to pin the existing bounded fragment')
    if a.s30_fixture:
        fragment=pin(a.s30_fixture);raw=a.s30_fixture.read_bytes();wire=raw.replace(b'\r',b'')
        if fragment['sha256']!='9883b78b34beed91ea6fe03a19e3e79cbb5e903dd173d1fb13c83a2e9534d110':raise ValueError('Not the authenticated existing s30 fragment')
        fragment.update(status='FIXTURE PINNED; new target result PENDING',wire_bytes=len(wire),
                        wire_sha256=hashlib.sha256(wire).hexdigest(),transformation='stock fp_run CR removal only',
                        scope='Declared post-ambush original-area callback fragment; not full H2 or its tight heap floor')
    gates=[
      dict(name='r100 s30 movie loan/reload fragment',fixture=fragment,tool=tools['fullplay/fp_run.py'],
           environment={'RE4DC_EMU':'console','FP_NOLIMIT':'1','RE4DC_MAX_FLYCASTS':'3'},
           arguments=['--seconds','54','--period','0','--stop',r'(?m)^route movie retired: id=10030\b[^\r\n]*\r?$','--grace','2'],
           accept='340/340 uploaded/presented; MOVIEARENA borrow and return restored1; no faults; matched Off fragment heap_before; On SDO3 adopted again after loan and world draw resumes',
           prior_scope='The existing source2158baff run took37.0s with full11.922s movie. This is historical fixture evidence, not a new target PASS. A54s timeout remains INCOMPLETE; no extension or movie shortening.'),
      dict(name='knob0 image identity',accept='objcopy -R .stack SHA256 equals same-recipe pre-change control; ordinary ELF/file SHA is insufficient'),
      dict(name='KOS48KiB',requires_resolved_knobs={'KOS_WATCH':'1','KOS_SQUEEZE':'1','W11_FIXTURE':'1'},tool=tools['fullplay/kos_squeeze.sh'],levels='49152:0 49152:1',scenes='fight call leave100 leave103',accept='0 OOM/HALT/MISSING; held49152; headroom>=4096; every scene endpoint',seconds=60),
      dict(name='r100 fullH2 s30 memory floor',fixture=tools['fullplay/segments/h2-warp.txt'],pad=tools['fullplay/segments/h2-pad.txt'],accept='340/340 plus heap_before >= matched Off; no allocation faults',seconds=60,note='Existing rr h2 uses300s and named full gate420s. Do not silently invoke those under a60s contract. Main must supply a qualified bounded s30 fixture or deliberately use its already authorized named exception; a60s timeout is INCOMPLETE.'),
      dict(name='census',requires_resolved_knobs={'TEX_CHECK':'1 or2','MCHECK_LEONGC':'1','NATIVE_MODEL_REGISTRY_CENSUS':'1','VRAM_ROOM_LOG':'1'},note='A TEX_CHECK0/MCHECK0/census0 rW program cannot establish these gates; require a diagnostic build/twin and pin it separately.',rooms=['r100','r101','r103'],accept='TEXCHK fails0; VRAM no-contiguous/refusals/rereads0; CAST-GC/LEON-GC unlisted0; alive characters still drawn',seconds=60),
      dict(name='look pairs',fixtures={'cross':pin(d/'scenery19/k/still-r101-warp.txt'),'farm':pin(d/'scenery19/k/still-r103-warp.txt')},tool=tools['fullplay/fp_run.py'],arguments=['--seconds','60','--period','5'],compare_tool=tools['scenery19/pix.py'],accept='Off/On share source/fixture/data and logged freeze700; compare only matched post-freeze captures. Use cross-k/cross-p and farm-k/farm-p names for existing pix.py.'),
      dict(name='GDEMU race',tool=tools['fullplay/gdemu_gate.sh'],fixture=tools['fullplay/segments/door103-warp.txt'],environment={'MAXP':'1','SECS':'60','RE4DC_EMU':'console','RE4DC_GD_PROFILE':'gdemu'},seeds=list(range(1,11)),accept='Every seed reaches r103; bad reads0 and stop faults0; proxy correctness, not console timing'),
    ]
    qa_arms={}
    for name,mode in [('off',0),('on',3)]:
        prefix='dd23'+source[:8]+name+'q';label=prefix+'rW';work=a.work/'qa'/name
        elf='/root/probe/lanes/route/out-'+label+'/re4dc-game.elf';fixture=work/'fix'/('pkg-'+label+'.json')
        qa_arms[name]=dict(status='PENDING: program/data/disc pins and safety gates',label=label,
            build=dict(environment={**exports,'T':str(a.tree),'K':str(work/'logs'),'LP':prefix,'CH2':ch2,
                                     'XON':f'SCENERY_DEDUP={mode} PC_SAMPLER=0 QA_MENU=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23 QA_SRC='+source[:8]},
                       argv=['bash',tools['ch2/ch2-build.sh'],'rW']),
            stage=dict(environment={**exports,'RE4DC_RESIDENT_STRICT':'1'},argv=['python3',tools['test11/t11-fix.py'],label,str(fixture),'--base','payload','--data',data,*sets]),
            pkgtree=dict(environment={'PKG_K':str(work)},argv=['python3',tools['test8/t8-pkgtree.py'],label,str(fixture)]),
            presets=[['python3',tools['stage_route.py'],'--stage','1','--json',str(work/'sr1.json')],
                     ['python3',tools['qa20/mkqa.py'],str(work/'presets'),'--sr1',str(work/'sr1.json')]],
            preset_copy=dict(source=str(work/'presets'),destination=str(work/'pkgtree/dc/qa')),
            master=dict(cwd=str(d),environment={'LAYOUT':'standard'},argv=['bash',tools['mkgdi.sh'],elf,str(work/'pkgtree'),str(work/'gdemu')]),
            lint=[['python3',tools['disc_lint.py'],'--profile',profile,str(work/'gdemu/disc.gdi')] for profile in ('loader','standard')])
    plan=dict(kind='PREFLIGHT ONLY; this tool executes no build, staging or guest',source=source,tree=str(a.tree),recipe=pin(recipe),
              data_sets=data,recipe_exports=exports,alternates=alternates,baseline_packages=base_pins,
              alternate_variant='strip-share-v1' if a.strip_share else 'legacy-byte-neutral',strip_share_manifest=strip_manifest,
              source_identities=identities,arms=arms,tools=tools,gates=gates,
              execution=dict(owner='main lane',trace_lock=tools['trace_lock.sh'],max_lane_flycasts=3,normal_run_seconds=60,layout='standard',global_input=False),
              qa=dict(status='PENDING: separate QA_MENU=1 Off/On programs and their pins required',arms=qa_arms,
                      steps=['Build each arm through ch2-build.sh with unique LP and exact recipe; SCENERY_DEDUP0/3 plus QA_MENU1, WARP_AFTER_RESET1 and matching QA_SRC.',
                             'Apply the same four --set alternates to both QA fixtures; keep standard files. Use t8-pkgtree with separate PKG_K per arm.',
                             'Run existing stage_route.py --stage 1 -> mkqa.py; copy generated QA assets into that arm pkgtree/dc/qa.',
                             'Use LAYOUT=standard mkgdi.sh with that arm pinned ELF, then disc_lint loader and standard. Keep private Off/On packages and README after safety gates pass.'],
                      warning='Unmodified rr-qa.sh hardcodes rr<sha7>qrW and cannot distinguish same-source Off/On outputs. rr-cycle/rr-jobs also assume shared rr labels; do not invoke them for these custom arms.'))
    value=json.dumps(plan,indent=2)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(value)
    else:print(value,end='')

if __name__=='__main__':main()