#!/usr/bin/env python3
"""Exercise actual texture incarnation boundaries with controlled Package/PVR edges.

Entry layout, close_entry, successful publication, Ps2HdrSlot and the exact
ordinary-hit, SCPS and readiness predicates/fill are compiled from native_ui.cpp.
This is a cache/lifecycle boundary fixture, not a full loader/renderer replay,
GPU fence, real movie playback, visual/STRICT or hardware timing result.
"""
import argparse, hashlib, importlib.util, json, os, re, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1]
UI=DC/'game/platform/native_ui.cpp'
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)
def between(s,a,b):
    at=s.index(a)+len(a);return s[at:s.index(b,at)]
def through(s,a,b):
    at=s.index(a);return s[at:s.index(b,at)+len(b)]
def fragments(s):
    return dict(ENTRY=through(s,'struct Entry {','\n};'),
        ADVANCE=between(s,'// PS2_UPLOAD_ADVANCE_BEGIN','// PS2_UPLOAD_ADVANCE_END'),
        CLOSE=extract.function(s,'void close_entry(Entry& entry) {'),
        SLOT=between(s,'// PS2_UPLOAD_SLOT_BEGIN','// PS2_UPLOAD_SLOT_END'),
        MATCH=through(s,'#if RE4DC_PS2_UPLOAD_INCARNATION\nbool ps2_hdr_upload_current','\n#endif'),
        PUBLICATION=between(s,'// PS2_UPLOAD_PUBLICATION_BEGIN','// PS2_UPLOAD_PUBLICATION_END'),
        FILL=through(s,'        slot.crc=k[0];','        for(unsigned i=0;i<4;++i)slot.words[i]=hw[i];'),
        HIT=between(s,'// PS2_UPLOAD_HIT_BEGIN','// PS2_UPLOAD_HIT_END'),
        PIECE=between(s,'// PS2_UPLOAD_PIECE_BEGIN','// PS2_UPLOAD_PIECE_END'),
        READY=between(s,'// PS2_UPLOAD_READY_BEGIN','// PS2_UPLOAD_READY_END').replace('&expected','expected'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);source=UI.read_text();values=fragments(source)
    text=(HERE/'upload_fixture.cpp.in').read_text()
    for k,v in values.items():text=text.replace('@'+k+'@',v)
    assert not re.search(r'@[A-Z]+@',text)
    cpp=a.output/'upload.cpp';cpp.write_text(text);rows=[]
    for mode in (0,1):
        for handles in (0,1):
            name=f'incarnation{mode}-handles{handles}';binary=a.output/name
            flags=['-std=c++20','-O2','-Wall','-Wextra','-Wno-unused-variable',f'-DRE4DC_PS2_UPLOAD_INCARNATION={mode}',f'-DCHECK_HANDLES={handles}']
            if a.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
            run=subprocess.run(['g++',*flags,str(cpp),'-o',str(binary)],capture_output=True)
            (a.output/(name+'-compile.log')).write_bytes(run.stdout+run.stderr)
            assert run.returncode==0,run.stderr.decode()
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            run=subprocess.run([str(binary)],capture_output=True,env=env)
            (a.output/(name+'-run.log')).write_bytes(run.stdout+run.stderr)
            assert run.returncode==0,run.stderr.decode()
            row=json.loads(run.stdout);assert row['stale_counterexamples']==(0 if mode else 6)
            rows.append(dict(name=name,**row))
    paths=[UI,HERE/'upload_fixture.cpp.in',Path(__file__)]
    assert source==UI.read_text()
    report=dict(status='PASS',scope=__doc__,sanitize=a.sanitize,rows=rows,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in values.items()})
    receipt=a.output/'upload-host.json';receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',rows=rows,receipt=str(receipt))))
if __name__=='__main__':main()
