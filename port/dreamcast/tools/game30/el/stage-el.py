# lane el 2026-10-05: copy of lane fm's stage-f.py, staging to D:/_el-stage
"""Stream a new test image; verify every payload and both ISO namespaces."""
from pathlib import Path
import argparse,ast,hashlib,io,json,shutil,struct
import pycdlib
HERE=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1');ROOT=HERE.parent
BASE=Path('/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/disc.bin')
# 2026-10-03: the base image was rebuilt from its original inputs after an accidental delete (disc-ig27rc1-kite7/
# RESTORED-20261003.txt): identical payload manifest, new genisoimage metadata. Original sha ad795a67...6e2a.
BASE_SHA=open('/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/disc.sha256').read().split()[0]
utility=ROOT/'renderer/inventory-uiorder-r1/stage-iso.py';text=utility.read_text()
assert hashlib.sha256(text.encode()).hexdigest()=='f95bfad4b2d1a1be0dfbb3bf99331841ddaeaa739435f3f89df614a10d50d9d6'
ns=dict(Path=Path,hashlib=hashlib,io=io,pycdlib=pycdlib)
defs=ast.parse(text)
exec(compile(ast.Module(body=[n for n in defs.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'sha','HashSink','manifest','primary_path','replace'}],type_ignores=[]),str(utility),'exec'),ns)
sha,manifest,primary_path,replace=(ns[k] for k in ('sha','manifest','primary_path','replace'))
def ensure_dir(iso,parent):
    # Lane route (2026-10-01): a file in a directory the base disc lacks (dc/native/r106) gets its parents
    # created in all three namespaces; existing directories are untouched.
    done=''
    for name in [p for p in parent.split('/') if p]:
        path=done+'/'+name
        try:iso.get_record(rr_path=path)
        except Exception:
            base=primary_path(iso.get_record(rr_path=done or '/')).rstrip('/')
            iso.add_directory(iso_path=base+'/'+name.upper().replace('-','_'),rr_name=name,joliet_path=path)
        done=path
def add(iso,files):
    streams=[]
    for path,source in files.items():
        parent,name=path.rsplit('/',1) if '/' in path else ('',path)
        ensure_dir(iso,parent)
        ip=primary_path(iso.get_record(rr_path='/'+parent)).rstrip('/')+'/'+name.upper().replace('-','_')+';1'
        stream=source.open('rb');streams.append(stream)
        iso.add_fp(stream,source.stat().st_size,iso_path=ip,rr_name=name,joliet_path='/'+path)
    return streams
def remove(iso,path):
    r=iso.get_record(joliet_path='/'+path)
    prim=[x for x,is_pvd in r.inode.linked_records if is_pvd];assert len(prim)==1
    iso.rm_file(iso_path=primary_path(prim[0]))
def diff(a,b):return dict(removed=sorted(a.keys()-b.keys()),added=sorted(b.keys()-a.keys()),changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]))
p=argparse.ArgumentParser();p.add_argument('scenario');p.add_argument('--arm',required=True)
p.add_argument('--programs',type=Path,default=HERE/'programs.json')
p.add_argument('--overlay',type=Path,required=True);p.add_argument('--fixture',type=Path)
p.add_argument('--capture-reserve-mib',type=int,choices=(128,256,512),default=256)
# lane el 2026-10-05: --stage-root (default D:/_el-stage); C:/_el-cstage/stage when D: is below the 8 GiB floor
p.add_argument('--stage-root',type=Path,default=Path('/mnt/d/Flycast-Evidence/re4-dreamcast/_el-stage'))
a=p.parse_args()
out=a.stage_root/a.scenario;assert not out.exists(),'Preserve earlier scenario'
assert sha(BASE)==BASE_SHA
media=json.loads((ROOT/'integration-source-r11/MEDIA.json').read_text())['assets']
changes={}
for entry in media:
    dest=entry['eventual_disc_destination'];src=a.overlay/dest
    assert src.is_file() and sha(src)==entry['sha256'] and src.stat().st_size==entry['bytes'],dest
    assert dest not in changes;changes[dest]=src
program=json.loads(a.programs.read_text())[a.arm]
for dest,name in [('1ST_READ.BIN','1ST_READ.BIN'),('dc/sscrn.ovl','sscrn.ovl')]:
    src=HERE/'programs'/a.arm/name;assert sha(src)==program['files'][name]['sha256'];changes[dest]=src
removals=[]
fixture=json.loads(a.fixture.read_text()) if a.fixture else {}
for dest,source in fixture.get('replace',{}).items():changes[dest]=(a.fixture.parent/source).resolve()
removals=fixture.get('remove',[]);assert not(set(removals)&set(changes))
upper=BASE.stat().st_size+sum(f.stat().st_size for f in changes.values())+1024**2
# The completed 180-900 second runs retain under 32 MiB of capture data.
# Reserve at least 128 MiB beyond the full uncompressed image upper bound; the live
# runner independently enforces the unchanged 16 GiB floor on every poll.
a.stage_root.mkdir(parents=True,exist_ok=True)
stage_capacity=dict(free_before=shutil.disk_usage(str(a.stage_root)).free,
    image_upper_bound=upper,capture_reserve=a.capture_reserve_mib*1024**2,floor=8*1024**3)
assert stage_capacity['free_before']-upper-stage_capacity['capture_reserve']>=stage_capacity['floor']
iso=pycdlib.PyCdlib();iso.open(str(BASE));cache={}
before=manifest(iso,'joliet',cache);before_rr=manifest(iso,'rr',cache)
assert before==json.loads((BASE.parent/'payload-manifest.json').read_text())
removed=[x for x in removals if x in before]
for path in removed:remove(iso,path)
replacements={k:v for k,v in changes.items() if k in before}
additions={k:v for k,v in changes.items() if k not in before}
streams,metadata=replace(iso,replacements);streams+=add(iso,additions)
expected={k:v for k,v in before.items() if k not in removed}
expected_rr={k:v for k,v in before_rr.items() if k not in removed}
for key,src in changes.items():expected[key]=expected_rr[key]=dict(size=src.stat().st_size,sha256=sha(src))
with BASE.open('rb') as f:boot=f.read(32768)
assert boot.startswith(b'SEGA SEGAKATANA')
out.mkdir(parents=True);(out/'disc').mkdir();disc=out/'disc/disc.bin'
with disc.open('x+b') as f:iso.write_fp(f);f.seek(0);f.write(boot)
iso.close()
for f in streams:f.close()
iso=pycdlib.PyCdlib();iso.open(str(disc));cache={}
after=manifest(iso,'joliet',cache);after_rr=manifest(iso,'rr',cache);iso.close()
assert after==expected and after_rr==expected_rr,'Payload/namespace mismatch'
reader=ROOT/'gameplay/verify_cost_inputs.py';rd={'Path':Path,'hashlib':hashlib,'json':json,'struct':struct}
exec(compile(ast.Module(body=[n for n in ast.parse(reader.read_text()).body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(reader),'exec'),rd)
assert rd['disc_manifest'](disc)==after
with disc.open('rb') as f:assert f.read(32768)==boot
assert disc.stat().st_size<=upper
report=dict(status='STAGED_PAYLOAD_IDENTITY_PASS',scenario=a.scenario,arm=a.arm,elf_sha256=program['elf_sha256'],capacity=stage_capacity,
    base=str(BASE),base_sha256=BASE_SHA,disc_sha256=sha(disc),disc_bytes=disc.stat().st_size,
    both_namespaces_verified=True,independent_raw_reader_verified=True,boot_area_preserved=True,
    payload_delta=diff(before,after),fixture=fixture,media_records=len(media),free_d_after=shutil.disk_usage('/mnt/d').free)
(out/'stage.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'payload-manifest.json').write_text(json.dumps(after,indent=2)+'\n')
(out/'disc/disc.cue').write_text('FILE "disc.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')
print(json.dumps(report,indent=2))
