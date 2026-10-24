"""Host-compile the exact future helper against actual95 fallback counts; zero rays."""
import argparse,hashlib,json,os,resource,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'eligible';sys.path[:0]=[str(HERE),str(BASE),str(HERE.parent)]
from ledger import Ledger
from capability import EXPECTED_HELPER_SHA256
AUDIT_SHA='0e7544020864e4836c64c31d610ee8ba2047ca3c1816814a708871791476f77c'
MESH_SHA='31ec2e15faca0f171b1ae94290ecc22153eb06d256b6b6ef965bde3315f674b1'
NONEMPTY_SHA='75c7a9a591827257e81e0681ce3a5c1e6947ac9a2657d68deef37f828ad01061'
MACROS=dict(RE4DC_PS2_PVS_EFFECTIVE0_SOURCES=1,RE4DC_PS2_WORLD_NONEMPTY_LOD=1,RE4DC_MESH_LOD=1,RE4DC_PS2_WORLD_MESH=1)

def identity(p):
    p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def checked_rows(audit,mesh):
    if identity(audit)['sha256']!=AUDIT_SHA or identity(mesh)['sha256']!=MESH_SHA:raise ValueError('Exact actual census/mesh pins')
    rows=json.loads(Path(audit).read_text())['physical_clusters'];m=Path(mesh).read_bytes();ncl,nlv,_,ocl,olv=struct.unpack_from('<5I',m,80)
    selected=[]
    for row in rows:
        ci=row['cluster']
        if not 0<=ci<ncl:raise ValueError('Actual cluster range')
        first,count=struct.unpack_from('<II',m,ocl+ci*20+12)
        if first+count>nlv:raise ValueError('Actual level range')
        counts=[struct.unpack_from('<I',m,olv+(first+i)*12+4)[0] for i in range(count)]
        if count!=row['declared_level_count'] or counts!=row['meshlet_counts']:raise ValueError('Actual census count mismatch')
        if row['eligible'] and count>1 and row['effective_levels']==[0] and row['invariant_faces']>0:
            if counts[0]<=0 or any(counts[1:]):raise ValueError('Actual effective0 predicate mismatch')
            selected.append(row)
    if len(rows)!=318 or len(selected)!=95 or sum(x['invariant_faces'] for x in selected)!=8168:raise ValueError('Complete actual95 census required')
    return selected

def extract_helper(path):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_HELPER_SHA256:raise ValueError('Exact frozen future runtime helper pin')
    text=raw.decode();start=text.index('#if defined(RE4DC_PS2_PVS_EFFECTIVE0_SOURCES)');end=text.index('#endif',start)+len('#endif')
    block=text[start:end]
    if text.count('template<class Level> bool effective0_source(')!=1:raise ValueError('Single exact helper occurrence')
    return block

def main():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
    ap=argparse.ArgumentParser();ap.add_argument('--helper',required=True,type=Path);ap.add_argument('--nonempty',required=True,type=Path);ap.add_argument('--audit',required=True,type=Path);ap.add_argument('--mesh',required=True,type=Path);ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False)
    if identity(a.nonempty)['sha256']!=NONEMPTY_SHA:raise ValueError('Actual NONEMPTY helper pin')
    rows=checked_rows(a.audit,a.mesh);block=extract_helper(a.helper);token=Ledger(a.ledger).reserve(1024,'effective0 host compilation controls; zero ray queries; no refund')
    # Snapshots contain code only. Compile those exact pinned bytes; no game/media.
    (a.out/'nonempty_lod.hpp').write_bytes(a.nonempty.read_bytes());(a.out/'future-helper.inc').write_bytes((block+'\n').encode())
    checks=[]
    for row in rows:
        counts=row['meshlet_counts'];body=','.join('{'+str(n)+'}' for n in counts);checks.append(' {Level levels[]={'+body+'}; if(!effective0_source(levels,'+str(len(counts))+'))return 1; for(unsigned raw=0;raw<'+str(len(counts))+';++raw)if(re4dc::room::nonempty_lod(levels,'+str(len(counts))+',raw)!=0)return 2;}')
    checks.extend([' {Level levels[]={{0},{0}};if(effective0_source(levels,2))return 3;}', ' {Level levels[]={{3},{0},{1}};if(effective0_source(levels,3))return 4;}', ' if(effective0_source<Level>(nullptr,2)||effective0_source<Level>(nullptr,0))return 5;', ' {Level levels[]={{3},{0},{0},{0}};if(!effective0_source(levels,4))return 6;for(unsigned raw=0;raw<4;++raw)if(re4dc::room::nonempty_lod(levels,4,raw))return 7;}'])
    text='#include "nonempty_lod.hpp"\nstruct Level{unsigned meshlet_count;};\n#include "future-helper.inc"\nint main(){\n'+'\n'.join(checks)+'\nreturn 0;}\n';(a.out/'check.cpp').write_bytes(text.encode())
    compiler=Path(subprocess.check_output(['which','g++'],text=True).strip()).resolve();common=[str(compiler),'-std=c++11','-O0','-Wall','-Wextra','-Werror',str(a.out/'check.cpp')]
    command=common+['-D'+k+'=1' for k in MACROS]+['-o',str(a.out/'check')];built=subprocess.run(command,capture_output=True,text=True);(a.out/'compile.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('Future effective0/NONEMPTY host compile failed')
    subprocess.run([str(a.out/'check')],check=True);refused=[]
    for missing in MACROS:
        result=subprocess.run(common+['-D'+k+'=1' for k in MACROS if k!=missing]+['-o',str(a.out/'must-not-compile')],capture_output=True,text=True)
        (a.out/('missing-'+missing+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode==0:raise ValueError('Missing compiled capability did not refuse '+missing)
        refused.append(missing)
    nonboolean=[]
    for macro in MACROS:
        for value in (0,2):
            result=subprocess.run(common+['-D'+k+'='+str(value if k==macro else 1) for k in MACROS]+['-o',str(a.out/'must-not-compile')],capture_output=True,text=True)
            (a.out/('invalid-'+macro+'-'+str(value)+'.log')).write_text(result.stdout+result.stderr)
            if result.returncode==0:raise ValueError('Nonboolean/zero compiled capability did not refuse '+macro)
            nonboolean.append([macro,value])
    receipt=dict(status='HOST_COMPILED_CAPABILITY_ONLY',runtime_admitted=False,helper=identity(a.helper),nonempty=identity(a.nonempty),compiled_macros=MACROS,helper_block=identity(a.out/'future-helper.inc'),compiler=identity(compiler),command=command,binary=identity(a.out/'check'),harness=identity(a.out/'check.cpp'),actual_audit=identity(a.audit),actual_mesh=identity(a.mesh),actual_clusters=95,all_valid_raw_lods=sum(x['declared_level_count'] for x in rows),physical_rows=rows,missing_macro_refusals=refused,nonboolean_macro_refusals=nonboolean,negative_controls=['empty base','positive higher','null pointer','zero count'],generic_fourlevel_control=True,ledger_reserved=token.reserved,ray_queries_used=token.used,ledger_after=json.loads(a.ledger.read_text()),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    raw=(json.dumps(receipt,indent=2)+'\n').encode();existing=sum(p.stat().st_size for p in a.out.parent.rglob('*') if p.is_file())
    if existing+len(raw)+65536>16*1024*1024:raise ValueError('Whole evidence unit output cap')
    (a.out/'CAPABILITY.json').write_bytes(raw);print(json.dumps(identity(a.out/'CAPABILITY.json')))
if __name__=='__main__':main()
