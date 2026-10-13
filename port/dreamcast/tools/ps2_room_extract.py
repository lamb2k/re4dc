#!/usr/bin/env python3
"""Reproducible PS2 room scenario extraction for ps2_room_r4im.py (WSL, mono).

PS2 disc (USA) -> AFS member <room>.dat -> JADERLINK DATUDAS_TOOL (dat.exe, V1.0.4) -> <room>_NNN.* ->
JADERLINK RE4_PS2_SCENARIO_SMD_TOOL (V1.3.0) on the room's scenario SMD -> the converter's input set:

    <room>_004.SMD, <room>_004.TPL, <room>_004.scenario.{obj,mtl,idxmaterial,idx_ps2_scenario,idx_ps2_smd},
    <room>_004_BIN/*.BIN, <room>_005.SMX

(the scenario SMD is the dat's first .SMD entry and the SMX the dat's first .SMX entry; both have been 004/005 in
every room so far, and the script refuses a room where they are not, so the converter's fixed names stay valid).
This is the pipeline that made the committed r100/r101/r103 inputs (w9/ps2/{dat,smd}-r103.log, mono under WSL);
`--compare <dir>` checks an extraction against committed inputs byte-for-byte.

Tools are pinned by sha256 and run with -bat (no key prompt), stdin from /dev/null, in a fresh work directory per
room. Nothing in the tools' output depends on time or the host; the manifest records every member, tool and file
hash so a rerun can be checked with --compare against the previous output.

usage: ps2_room_extract.py [--out DIR] [--inputs DIR] [--compare REFROOT] [--keep-work] room [room ...]
       ps2_room_extract.py --list          (the AFS members that look like stage rooms)
"""
import argparse, hashlib, json, os, re, shutil, struct, subprocess, sys
from pathlib import Path

ISO = Path('/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso')
AFS_SECTOR = 446273
DAT_EXE = Path('/root/probe/ps2-asset-experiment/dat.exe')
SMD_EXE = Path('/root/probe/ps2-asset-complete/tools/smd/RE4_PS2_SCENARIO_SMD_TOOL.exe')
PINS = {
    'dat': 'ed7f6fd4ff7cc8d1c93b27458db44c730d15c66e846beacc236ae3dfc3a0982e',
    'smd': '9fc3d21b164b2e7930eab4ec7e2eb93752758b811314c3c194101cfd7e19b610',
}
# route order after r103 (R4_FIRST_STAGE_GAP_AUDIT.md "Full stage-1 route"), then the alternatives / optional ones
STAGE1_REMAINING = ['r106', 'r104', 'r107', 'r105', 'r102', 'r108', 'r109', 'r10a', 'r10b', 'r11b', 'r11a',
                    'r10c', 'r10e', 'r119', 'r118', 'r117', 'r112', 'r111', 'r113', 'r11c', 'r11d', 'r11e',
                    'r10f', 'r11f', 'r10d', 'r120']
SCENARIO_SUFFIXES = ['.scenario.obj', '.scenario.mtl', '.scenario.idxmaterial', '.scenario.idx_ps2_scenario',
                     '.scenario.idx_ps2_smd']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def afs_index(f, sector=AFS_SECTOR):
    base = sector * 2048
    f.seek(base)
    magic, n = struct.unpack('<4sI', f.read(8))
    assert magic == b'AFS\0', magic
    table = f.read(n * 8)
    entries = list(struct.iter_unpack('<II', table))
    no, ns = struct.unpack('<II', f.read(8))
    f.seek(base + no)
    names = f.read(ns)
    rows = {}
    for i, (off, size) in enumerate(entries):
        name = names[i * 48:i * 48 + 32].split(b'\0')[0].decode('ascii', 'replace')
        rows[name.lower()] = dict(index=i, name=name, offset=base + off, size=size)
    return rows, hashlib.sha256(table + names).hexdigest()


def run_tool(exe, args, cwd, log):
    p = subprocess.run(['mono', str(exe), '-bat'] + args, cwd=cwd, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    text = p.stdout.decode('utf-8', 'replace')
    Path(log).write_text(text)
    if p.returncode != 0 or 'Error' in text or 'Finished!!!' not in text:
        raise SystemExit('%s failed (rc %d), see %s' % (exe.name, p.returncode, log))
    return text


def tree_hashes(root):
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_file():
            out[str(p.relative_to(root)).replace(os.sep, '/')] = dict(bytes=p.stat().st_size, sha256=sha(p))
    return out


def compare(a, b):
    ha, hb = tree_hashes(a), tree_hashes(b)
    diff = dict(only_new=sorted(set(ha) - set(hb)), only_ref=sorted(set(hb) - set(ha)),
                changed=sorted(k for k in set(ha) & set(hb) if ha[k]['sha256'] != hb[k]['sha256']))
    diff['identical'] = not any(diff.values())
    diff['files'] = len(ha)
    return diff


def extract(room, iso_f, index, work, inputs, dat_exe=DAT_EXE, smd_exe=SMD_EXE):
    member = index.get(room + '.dat')
    if member is None:
        raise SystemExit('%s.dat not in the AFS' % room)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    iso_f.seek(member['offset'])
    data = iso_f.read(member['size'])
    assert len(data) == member['size']
    (work / (room + '.dat')).write_bytes(data)
    member = dict(member, sha256=hashlib.sha256(data).hexdigest())
    run_tool(dat_exe, [room + '.dat'], work, work / 'dat.log')
    idxj = (work / (room + '.idxJ')).read_text(encoding='utf-8-sig')
    entries = re.findall(r'^DAT_(\d+):(.+)$', idxj, re.M)
    names = [Path(e[1].strip().replace('\\', '/')).name for e in entries]
    smds = [n for n in names if n.upper().endswith('.SMD')]
    smxs = [n for n in names if n.upper().endswith('.SMX')]
    if not smds:
        # r120 (the intro cinematic room) has no scenario model: nothing to convert
        return dict(room=room, member=member, dat_entries=names, scenario_smd=None, smx=None, other_smds=[],
                    obj_group_kinds={}, bins=0, files={}, status='no scenario SMD in the dat')
    if not smxs:
        raise SystemExit('%s: no SMX in the dat (%s)' % (room, names))
    if smds[0] != room + '_004.SMD' or smxs[0] != room + '_005.SMX':
        raise SystemExit('%s: scenario SMD/SMX are %s/%s, not _004/_005 (converter names)' % (room, smds[0], smxs[0]))
    sub = work / room
    run_tool(smd_exe, [smds[0]], sub, work / 'smd.log')
    stem = room + '_004'
    if inputs.exists():
        shutil.rmtree(inputs)
    inputs.mkdir(parents=True)
    for n in [stem + '.SMD', stem + '.TPL', room + '_005.SMX'] + [stem + s for s in SCENARIO_SUFFIXES]:
        shutil.copy2(sub / n, inputs / n)
    shutil.copytree(sub / (stem + '_BIN'), inputs / (stem + '_BIN'))
    # small room files the look sheet and the colour study read (route graph, events, lights, cameras):
    # <inputs root>/../aux/<room>, outside the converter's input set
    aux = inputs.parent.parent / 'aux' / room
    if aux.exists():
        shutil.rmtree(aux)
    aux.mkdir(parents=True)
    for n in names:
        if n.upper().endswith(('.RTP', '.AEV', '.LIT', '.CAM')):
            shutil.copy2(sub / n, aux / n)
    obj =(inputs / (stem + '.scenario.obj')).read_text(errors='replace')
    kinds = {}
    for g in re.findall(r'^g (\S+)', obj, re.M):
        k = 'NORMAL' if 'NORMAL' in g.upper() else ('COLOR' if 'COLOR' in g.upper() else 'OTHER')
        kinds[k] = kinds.get(k, 0) + 1
    return dict(room=room, member=member, dat_entries=names, scenario_smd=smds[0], smx=smxs[0],
                other_smds=smds[1:], obj_group_kinds=kinds,
                bins=len(list((inputs / (stem + '_BIN')).glob('*.BIN'))), files=tree_hashes(inputs),
                aux=tree_hashes(aux))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rooms', nargs='*')
    ap.add_argument('--out', type=Path, default=Path('/root/probe/lanes/ps2rooms/extract'),
                    help='work root: <out>/work/<room> (full dat extraction), <out>/inputs/<room>, manifest')
    ap.add_argument('--inputs', type=Path, help='inputs root (default <out>/inputs)')
    ap.add_argument('--compare', type=Path, help='reference inputs root (<ref>/<room>/...) for a byte compare')
    ap.add_argument('--remaining', action='store_true', help='all remaining stage-1 rooms in route order')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    for k, p in (('dat', DAT_EXE), ('smd', SMD_EXE)):
        if sha(p) != PINS[k]:
            raise SystemExit('%s: sha256 differs from the pin' % p)
    with ISO.open('rb') as f:
        index, index_sha = afs_index(f)
        if a.list:
            print(' '.join(sorted(n[:-4] for n in index if re.fullmatch(r'r[0-9a-f]{3}\.dat', n))))
            return
        rooms = a.rooms + (STAGE1_REMAINING if a.remaining else [])
        inputs_root = a.inputs or a.out / 'inputs'
        manifest_path = a.out / 'extract-manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        manifest.update(iso=dict(path=str(ISO), bytes=ISO.stat().st_size, afs_sector=AFS_SECTOR,
                                 afs_index_sha256=index_sha),
                        tools={k: dict(path=str(p), sha256=PINS[k]) for k, p in (('dat', DAT_EXE), ('smd', SMD_EXE))},
                        tool=dict(path='port/dreamcast/tools/ps2_room_extract.py', sha256=sha(__file__)))
        manifest.setdefault('rooms', {})
        for room in rooms:
            r = extract(room, f, index, a.out / 'work' / room, inputs_root / room)
            if a.compare and r['scenario_smd']:
                r['compare'] = dict(ref=str(a.compare / room), **compare(inputs_root / room, a.compare / room))
            manifest['rooms'][room] = r
            print(json.dumps({k: r[k] for k in ('room', 'scenario_smd', 'other_smds', 'bins', 'obj_group_kinds')} |
                             ({'compare': {k: v for k, v in r['compare'].items() if k != 'ref'}} if 'compare' in r else {}) |
                             ({'status': r['status']} if 'status' in r else {})))
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')


if __name__ == '__main__':
    main()
