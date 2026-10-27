"""Negative checks: missing/tampered source companions and altered baked geometry."""
import argparse,json,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
for name in ('helper-dir','source','c9','bake','work'):ap.add_argument('--'+name,type=Path,required=True)
a=ap.parse_args();assert not a.work.exists();a.work.mkdir(parents=True)
packer=Path(__file__).resolve().parents[1]/'world_rebuild27_bake_pack.py'
names=('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc');results=[]
for case in ('missing-r4tc','tampered-r4tc','altered-baked-position'):
    root=a.work/case;root.mkdir();source=a.source;atlas=None
    if case!='altered-baked-position':
        source=root/'r101';source.mkdir()
        for name in names:
            if name=='ps2-world.r4tc':
                if case=='tampered-r4tc':
                    data=bytearray((a.source/name).read_bytes());data[-1]^=1;(source/name).write_bytes(data)
            else:(source/name).symlink_to(a.source/name)
    else:
        doc=json.loads((a.bake/'ATLAS-EXCHANGE.json').read_text());doc['wall']['target_triangles'][0]['baked_corners_existing_part_basis'][0][0]+=1
        atlas=root/'invalid-atlas.json';atlas.write_text(json.dumps(doc))
    output=root/'candidate'
    cmd=[sys.executable,str(packer),'--helper-dir',str(a.helper_dir),'--source',str(source),'--c9',str(a.c9),'--bake',str(a.bake),'--out',str(output)]
    if atlas:cmd+=['--atlas',str(atlas)]
    run=subprocess.run(cmd,capture_output=True,text=True);(root/'rejection.log').write_text(run.stdout+run.stderr)
    assert run.returncode!=0 and not output.exists(),case+' did not reject before output'
    results.append(dict(case=case,rejected=True,no_output_created=True,last_error=(run.stderr.strip().splitlines() or [''])[ -1]))
(a.work/'RESULT.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
