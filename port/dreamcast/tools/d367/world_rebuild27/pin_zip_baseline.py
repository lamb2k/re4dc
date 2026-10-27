#!/usr/bin/env python3
"""Freeze an immutable ZIP control, reusing only hash-identical private files.

The one raw track is held in RAM for ISO reads; no temporary disc is written.
This is source/media identity preparation, not a boot or qualification result.
"""
import argparse,hashlib,importlib.util,io,json,os,shutil,zipfile
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('archive','reference-source','reference-manifest','out'):ap.add_argument('--'+k,type=Path,required=True)
    for k in ('archive-sha256','track-sha256','programme-sha256','reference-manifest-sha256'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();a.out=a.out.resolve();a.reference_source=a.reference_source.resolve()
    if a.out.exists() or a.reference_source in a.out.parents or a.out in a.reference_source.parents:raise ValueError('fresh disjoint output required')
    if digest(a.archive)!=a.archive_sha256 or digest(a.reference_manifest)!=a.reference_manifest_sha256:raise ValueError('input pin mismatch')
    available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    if available<5*1024**3:raise ValueError('need 5GiB host RAM headroom for bounded in-memory track')
    code=Path(__file__).resolve().parents[1]/'fullplay/fp_iso.py'
    spec=importlib.util.spec_from_file_location('fp_iso_control',code);iso=importlib.util.module_from_spec(spec);spec.loader.exec_module(iso)
    old=json.loads(a.reference_manifest.read_text());track_member='gdemu/track03.bin'
    with zipfile.ZipFile(a.archive) as z:
        if z.getinfo(track_member).file_size>1300000000:raise ValueError('track exceeds memory allocation bound')
        gdi=z.read('gdemu/disc.gdi').decode('ascii');raw=z.read(track_member)
    if hashlib.sha256(raw).hexdigest()!=a.track_sha256 or len(raw)%2352 or raw[:12]!=b'\x00'+b'\xff'*10+b'\x00':raise ValueError('raw control track identity')
    if '3 45000 4 2352 track03.bin 0' not in gdi.splitlines():raise ValueError('GDI track geometry')
    tr=iso.Track.__new__(iso.Track);tr.f=io.BytesIO(raw);tr.raw=True;tr.ss=2352;tr.base=45000;tr.count=len(raw)//2352
    entries=iso.files(tr);names=[n.lstrip('/') for n,_,_ in entries]
    if len(names)!=len(set(names)):raise ValueError('duplicate ISO paths')
    tree=a.out/'stage';tree.mkdir(parents=True);full={};linked=written=0;new_bytes=0
    for name,lba,size in sorted(entries,key=lambda r:r[1]):
        rel=Path(name.lstrip('/'))
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe ISO path')
        content=tr.read_bytes(lba,size) if size else b'';identity={'size':size,'sha256':hashlib.sha256(content).hexdigest()}
        dest=tree/rel;dest.parent.mkdir(parents=True,exist_ok=True);key=rel.as_posix()
        if old.get(key)==identity:
            source=a.reference_source/rel
            if digest(source)!=identity['sha256']:raise ValueError('reference source drift '+key)
            os.link(source,dest);linked+=1
        else:
            new_bytes+=size
            if new_bytes>300*1024**2:raise ValueError('new changed files exceed 300MiB allocation')
            dest.write_bytes(content);written+=1
        if digest(dest)!=identity['sha256']:raise ValueError('frozen readback '+key)
        full[key]=identity
    if full['1ST_READ.BIN']['sha256']!=a.programme_sha256:raise ValueError('programme identity')
    required=('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc')
    for name in required:
        key='dc/native/r101/'+name
        if full[key]!=old[key]:raise ValueError('r101 source changed; authoring proof needs refresh '+key)
    (a.out/'IP.BIN').write_bytes(tr.read(tr.base,16))
    (a.out/'disc-files.json').write_text(json.dumps(full,indent=2,sort_keys=True)+'\n')
    baseline=a.out/'baseline';(baseline/'dc/native/r101').mkdir(parents=True)
    for key in full:
        if key.startswith('dc/native/r101/') or key=='1ST_READ.BIN':
            dest=baseline/key;dest.parent.mkdir(parents=True,exist_ok=True);os.link(tree/key,dest)
    shutil.copyfile(a.out/'disc-files.json',baseline/'disc-files.json')
    shutil.copyfile(a.out/'IP.BIN',baseline/'IP.BIN')
    result={'scope':'immutable archive control identity only; no emulator or performance acceptance','archive':str(a.archive),'archive_sha256':a.archive_sha256,
      'track_member':track_member,'track_sha256':a.track_sha256,'programme_sha256':a.programme_sha256,'stage':str(tree),
      'files':len(full),'hash_identical_hardlinks':linked,'changed_files_written':written,'new_file_bytes':new_bytes,
      'changed_paths':[k for k in sorted(set(old)|set(full)) if old.get(k)!=full.get(k)],'r101_five_source_inputs_unchanged':True,
      'manifest_sha256':digest(a.out/'disc-files.json'),'zip_reader_sha256':digest(Path(__file__))}
    (a.out/'BASELINE.json').write_text(json.dumps(result,indent=2)+'\n');tr.f.close()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()