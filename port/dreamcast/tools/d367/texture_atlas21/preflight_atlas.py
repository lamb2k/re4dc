"""Run actual unchanged C++ source preflight over each generated private run."""
from pathlib import Path
import argparse,hashlib,json,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate',type=Path);ap.add_argument('--checks',type=Path,required=True)
    a=ap.parse_args();a.checks.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).with_name('preflight.cpp')
    include=source.parents[3]/'game'/'platform'/'include'
    exe=a.checks/'preflight'
    cmd=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer','-I'+str(include),str(source),'-o',str(exe)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    report=json.loads((a.candidate/'report.json').read_text());rows=[]
    for actor in report['textures']:
        folder=a.candidate/actor['actor']/'bindings'
        for run in actor['bindings']['runs']:
            here=folder/f"run-{run['index']:03d}"
            args=[str(exe),str(folder/'source-pos.bin'),str(folder/'source-nrm.bin'),str(here/'uv.bin'),
                  str(here/'stream.meshlets'),str(folder/'source-weights.bin'),str(run['triangles'])]
            result=subprocess.run(args,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(str(args)+'\n'+result.stdout+result.stderr)
            row=json.loads(result.stdout);row.update(actor=actor['actor'],run=run['index']);rows.append(row)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(actual_source_preflight=True,asan_ubsan=True,runs=len(rows),rows=rows,
        source_sha256=sha(include/'coarse_actor_preflight.h'),fixture_sha256=sha(source),
        candidate_manifest_sha256=sha(a.candidate/'SHA256SUMS'),runtime_admission=False)
    (a.checks/'preflight-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(runs=len(rows),actual_source_preflight_pass=True,asan_ubsan=True)))

if __name__=='__main__':main()
