#!/usr/bin/env python3
"""Pin current room assets and continuous eye domains; no runtime gain claim.

Runs on Windows (numpy) or Linux. All generated assets and coordinates belong
under --private, outside Git. Retained PCCULL integer eyes can seed domains;
PS2CAM provides exact matrices for later selection replay. Neither is a proof
of visibility: the separate continuous geometry certifier supplies that proof.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

PROOF_REV = 'fcf49c1dc788734799baadfe4147005f8d3338ff'
PREFIX = 'port/dreamcast/tools/d367/ps2world/'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob(repo, name):
    if sys.platform == 'win32':
        command = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--',
                   'git', '-C', repo, 'show', f'{PROOF_REV}:{PREFIX}{name}']
    else:
        command = ['git', '-C', repo, 'show', f'{PROOF_REV}:{PREFIX}{name}']
    return subprocess.run(command, check=True, stdout=subprocess.PIPE).stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default='/root/work/lanes/interior-vis23')
    ap.add_argument('--private', required=True, type=Path)
    ap.add_argument('--mesh', required=True, type=Path)
    ap.add_argument('--policy', required=True, type=Path)
    ap.add_argument('--original-policy', required=True, type=Path)
    ap.add_argument('--ids', required=True, type=Path)
    ap.add_argument('--base-report', required=True, type=Path)
    ap.add_argument('--log', action='append', type=Path, required=True)
    ap.add_argument('--strip-groups',type=Path,help='bind the actual staged optional r4sg; required before SG-aware pricing')
    ap.add_argument('--policy-migration-iso-receipt',type=Path,help='reverify the one independently reviewed exact r111 policy migration')
    ap.add_argument('--room', default='10d')
    ap.add_argument('--cell', type=float, default=2000)
    ap.add_argument('--vertical-pad', type=float, default=250)
    a = ap.parse_args()
    assert a.cell > 0 and a.vertical_pad >= 1
    root = a.private.resolve()
    root.mkdir(parents=True, exist_ok=True)
    pkg, work, helpers = root/'inputs', root/'work', root/'helpers'
    for d in (pkg, work, helpers/'pvs', helpers/'interior'):
        d.mkdir(parents=True, exist_ok=True)
    receipt = {'proof_revision': PROOF_REV, 'room': int(a.room, 16),
               'runtime_admitted': False, 'tool_hashes': {}, 'logs': []}
    for name in ('pvs_prep.py', 'pvs_emit.py', 'pvs_certify.py',
                 'pvs_verify.py', 'pvs_prove.py', 'pvs_cast.cpp'):
        dest = helpers/'pvs'/name
        dest.write_bytes(git_blob(a.repo, 'pvs/'+name))
        receipt['tool_hashes'][name] = sha(dest)
    (helpers/'interior'/'r4im.py').write_bytes(git_blob(a.repo, 'interior/r4im.py'))
    receipt['tool_hashes']['r4im.py'] = sha(helpers/'interior'/'r4im.py')
    for source, name in ((a.mesh, 'ps2-world.re4mesh'), (a.policy, 'ps2-world.r4pw'),
                         (a.original_policy, 'original.r4pw'), (a.ids, 'ps2-world.ids'),
                         (a.base_report, 'base-report.json')):
        shutil.copyfile(source, pkg/name)
    receipt['inputs'] = {f.name: {'source': str(source), 'sha256': sha(f), 'bytes': f.stat().st_size}
                         for source, f in ((a.mesh,pkg/'ps2-world.re4mesh'),
                                           (a.policy,pkg/'ps2-world.r4pw'),
                                           (a.original_policy,pkg/'original.r4pw'),
                                           (a.ids,pkg/'ps2-world.ids'),
                                           (a.base_report,pkg/'base-report.json'))}
    if a.strip_groups:
        target=pkg/'ps2-world.r4sg';shutil.copyfile(a.strip_groups,target)
        receipt['inputs'][target.name]={'source':str(a.strip_groups),'sha256':sha(target),'bytes':target.stat().st_size}
    if a.policy_migration_iso_receipt:
        from policy_migration import verify,EXPECTED
        # Re-read final copied inputs, not an externally supplied attestation.
        assert int(a.room,16)==0x111,'policy migration is r111 only'
        assert not (pkg/'append.json').exists(),'policy migration refuses stale append metadata'
        assert sha(pkg/'base-report.json')==EXPECTED['report'],'unreviewed copied conversion report'
        assert sha(pkg/'original.r4pw')==EXPECTED['original_policy'],'unreviewed copied original policy'
        migration=verify(a.base_report.parent,a.original_policy.parent,pkg,a.policy_migration_iso_receipt)
        migration_path=pkg/'policy-migration.json'
        migration_path.write_text(json.dumps(migration,indent=2)+'\n')
        receipt['inputs'][migration_path.name]={'source':'fresh exact verification of preserved inputs',
            'sha256':sha(migration_path),'bytes':migration_path.stat().st_size}
        prep=helpers/'pvs'/'pvs_prep.py';text=prep.read_text()
        before="assert report['re4mesh_sha256']==hashlib.sha256(p.m).hexdigest() and report['r4pw_sha256']==state_policy_sha, 'base report package mismatch'"
        after="assert report['re4mesh_sha256']==hashlib.sha256(p.m).hexdigest() and report['r4pw_sha256']=="+repr(EXPECTED['old_policy'])+" and state_policy_sha=="+repr(EXPECTED['original_policy'])+", 'base report migration mismatch'"
        assert text.count(before)==1;text=text.replace(before,after)
        before="static_provenance=dict(kind='base-conversion-report',name='base-report.json',base_placements=base_places)"
        after="static_provenance=dict(kind='exact-reviewed-policy-migration',name='base-report.json',base_placements=base_places,migration='policy-migration.json',raw_iso_reread=False)"
        assert text.count(before)==1;text=text.replace(before,after)
        before="('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','append.json','base-report.json')"
        after="('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','append.json','base-report.json','policy-migration.json')"
        assert text.count(before)==1;text=text.replace(before,after)
        receipt['pinned_tool_hashes']={'pvs_prep.py':sha(prep)}
        prep.write_text(text);receipt['tool_hashes']['pvs_prep.py']=sha(prep)
        receipt['policy_migration']={'verifier_sha256':sha(Path(__file__).with_name('policy_migration.py')),
            'attestation_sha256':sha(migration_path),'historical_iso_receipt_sha256':sha(a.policy_migration_iso_receipt),
            'old_report_unchanged':sha(pkg/'base-report.json')==EXPECTED['report'],'raw_iso_reread':False}
    subprocess.run([sys.executable, str(helpers/'pvs'/'pvs_prep.py'), str(pkg),
                    a.room, str(work), '--original-policy', str(pkg/'original.r4pw')], check=True)
    meta = json.loads((work/'meta.json').read_text())
    assert meta['static_qualified'], 'current input provenance did not qualify'
    samples, cams = [], []
    for log in a.log:
        text = log.read_text(errors='replace')
        receipt['logs'].append({'path': str(log), 'sha256': sha(log)})
        for m in re.finditer(r'PCCULL frame=(\d+).*?eye=(-?\d+),(-?\d+),(-?\d+)', text):
            samples.append({'frame': int(m[1]), 'eye': list(map(int,m.group(2,3,4))),
                            'kind': 'PCCULL integer camera eye', 'log': str(log)})
        pattern = r'PS2CAM f=(\d+) cf=([0-9a-fA-F]{8}) c=((?:[0-9a-fA-F]{8} ){11}[0-9a-fA-F]{8}) p=((?:[0-9a-fA-F]{8} ){6}[0-9a-fA-F]{8})'
        for m in re.finditer(pattern, text):
            vals = [struct.unpack('<f', bytes.fromhex(x)[::-1])[0] for x in (m[3]+' '+m[4]+' '+m[2]).split()]
            v = np.array(vals[:12]).reshape(3,4)
            if not np.isfinite(vals).all():
                continue
            eye = -np.linalg.solve(v[:,:3], v[:,3])
            samples.append({'frame':int(m[1]), 'eye':eye.tolist(), 'kind':'PS2CAM exact matrix', 'log':str(log)})
            cams.append(vals)
    assert samples, 'no actual camera eye samples found'
    x0 = math.floor(meta['world_lo'][0]/a.cell)*a.cell
    z0 = math.floor(meta['world_lo'][2]/a.cell)*a.cell
    nx = math.ceil((meta['world_hi'][0]-x0)/a.cell)
    nz = math.ceil((meta['world_hi'][2]-z0)/a.cell)
    nb = (meta['instances']+7)//8
    cells = {}
    for s in samples:
        x,y,z = s['eye']; ix,iz = math.floor((x-x0)/a.cell),math.floor((z-z0)/a.cell)
        if not(0 <= ix < nx and 0 <= iz < nz):
            s['domain']='outside room grid; draw all';continue
        c = iz*nx+ix
        lo,hi = cells.get(c,(float('inf'),-float('inf')))
        cells[c]=(min(lo,y-a.vertical_pad),max(hi,y+a.vertical_pad))
        s['cell']=[ix,iz]
    blob = bytearray(struct.pack('<3I3f',nx,nz,meta['instances'],x0,z0,a.cell))
    for c in range(nx*nz):
        if c in cells:
            lo,hi=cells[c]
            # Emitter adds +/-1000 mm and outward decimetre rounding. Store
            # pre-expansion values so the final interval is exactly our desired
            # sampled-height domain. The raw precursor bounds may be reversed;
            # the emitted/proven y interval is always ordered.
            blob += struct.pack('<ffB3x',lo+1000,hi-1000,1)+bytes(nb)
        else:
            blob += struct.pack('<ffB3x',0,0,0)+bytes(nb)
    (work/'cells.bin').write_bytes(blob)
    (root/'camera-samples.json').write_text(json.dumps(samples,indent=1)+'\n')
    (root/'cameras.txt').write_text(''.join(' '.join(format(v,'.9g') for v in c)+'\n' for c in cams))
    receipt.update(camera_eyes=len(samples), exact_cameras=len(cams), cells_with_domain=len(cells),
                   total_grid_cells=nx*nz, cell_mm=a.cell, vertical_pad_mm=a.vertical_pad,
                   unsampled='0xffff cell index; out-of-grid/out-of-y or missing receipt draws all',
                   selection_replay='pending exact PS2CAM' if not cams else 'exact matrices available',
                   temporary_bytes=sum(f.stat().st_size for f in root.rglob('*') if f.is_file()))
    (root/'prepare-receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps({k:receipt[k] for k in ('camera_eyes','exact_cameras','cells_with_domain','total_grid_cells','temporary_bytes')}))


if __name__ == '__main__':
    main()
