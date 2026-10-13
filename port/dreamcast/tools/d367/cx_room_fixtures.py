#!/usr/bin/env python3
"""Prepare private per-room CX fixtures and source-derived warp views.

Generated fixture JSON and assets stay outside Git. Existing fixture assets are
read only. The output still needs fixture_arm.py against the actual test arm;
texture candidate lists must be applied to a private pack by Claude.
This tool does not run Flycast, alter gameplay, kill actors, or write shared packs.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path[:0] = [str(HERE), str(TOOLS)]
from assetpipe.rooms import GcIso
from assetpipe.discover import stage_module, script_refs
import stage_route
import warp
from prepare_native_ui import ROOM_CONTRACTS


def read(p):
    return json.loads(Path(p).read_text())


def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2) + '\n')


def sha(p):
    digest = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def command(args, log):
    with log.open('w') as f:
        proc = subprocess.run([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT)
    if proc.returncode:
        detail = log.read_text(errors='replace')[-1600:].strip()
        raise RuntimeError('%s exited %s; %s: %s' % (args[1], proc.returncode, log, detail))


def prepare_room(room, iso, out):
    """Existing compact/release recipe, solely in this room's output folder."""
    st = 'st' + room[1]
    src = out / 'source' / st / (room + '.das')
    src.parent.mkdir(parents=True, exist_ok=True)
    raw = iso.read(st + '/' + room + '.das')
    if src.exists() and src.read_bytes() != raw:
        raise ValueError('source changed inside existing output; choose a fresh --out directory')
    if not src.exists():
        src.write_bytes(raw)
    tex = out / 'tex'
    compact = out / 'compact'
    package = out / 'package' / 'MAINSCENARIO.re4mesh'
    package.parent.mkdir(parents=True, exist_ok=True)
    manifest = out / 'textures.manifest'
    manifest.write_text(st + '/' + room + '.arc\n')
    if not (compact / (room + '.dar')).exists():
        command([sys.executable, TOOLS / 'le_mirror.py', src.parents[1], out / 'mirror', '--native-rooms'], out / 'mirror.log')
        if not (tex / 'native-ui-report.json').exists():
            command([sys.executable, TOOLS / 'prepare_native_ui.py', src.parents[1], manifest, tex], out / 'textures.log')
        texture_report = read(tex / 'native-ui-report.json')
        if texture_report.get('errors'):
            raise ValueError('native room dependency conversion rejected: ' + json.dumps(texture_report['errors']))
        if room not in ROOM_CONTRACTS:
            replacements = {st + '/' + room + '.' + ext: str(out / 'mirror' / st / (room + '.' + ext)) for ext in ('arc', 'dar')}
            for p in sorted(tex.glob('*.re4tex')):
                replacements['dc/tex/' + p.name[0] + '/' + p.name] = str(p)
            return replacements
        command([sys.executable, TOOLS / 'prepare_native_ui.py', '--compact-room', src,
                 '--compact-room-mips', '--textures', tex, '--output', compact], out / 'compact.log')
    if not package.exists():
        command([sys.executable, TOOLS / 'convert_room_bins.py', package, '--owner', '0xff', '--smd', src,
                 '--lod', '--lod-min-gain', '0.4', '--lod-max-levels', '4', '--lod-eps', '24,48,96,192,384',
                 '--lod-share', '--class-auto', '--color', 'prelit'], out / 'package.log')
    replacements = {'dc/native/' + room + '/MAINSCENARIO.re4mesh': str(package)}
    for ext in ('arc', 'dar'):
        target = out / 'released' / st / (room + '.' + ext)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            command([sys.executable, TOOLS / 'room_smd.py', 'release', compact / (room + '.' + ext),
                     str(package) + '.json', target], out / ('release-' + ext + '.log'))
        replacements[st + '/' + room + '.' + ext] = str(target)
    for p in sorted(tex.glob('*.re4tex')):
        replacements['dc/tex/' + p.name[0] + '/' + p.name] = str(p)
    return replacements


def entry_for(room, doors):
    # These are existing source-annotated presets, checked against fresh AEV data.
    preferred = {'r112': ('r118', 3), 'r111': ('r112', 0), 'r113': ('r111', 2),
                 'r11c': ('r113', 2), 'r200': ('r10f', 2)}
    incoming = [(src, d) for src, rec in doors.items() for d in rec['doors'] if d['dst'] == room and d['part'] == 0]
    choice = next(((src, d) for src, d in incoming if (src, d['no']) == preferred.get(room)), None)
    old = warp.PRESETS.get(room + '-entry')
    if choice is None and old and old.get('pos'):
        choice = next(((src, d) for src, d in incoming if max(abs(x-y) for x, y in zip(d['pos'], old['pos'])) <= 1), None)
    if choice is None and incoming:
        choice = sorted(incoming, key=lambda item: (item[0] >= room, item[0], item[1]['no']))[0]
    if choice:
        src, d = choice
        p = dict(room=int(room[1:], 16), pos=d['pos'], ang=d['angle'],
                 notes='%s from %s AEV door 0x%02x, destination part 0; fresh source extraction' % (room, src, d['no']))
        source = dict(kind='AEV door destination', source_room=src, door_no=d['no'], destination_part=d['part'],
                      source_tool='stage_route.scan', data=d)
    elif room == 'r22b':
        # Zero is source-derived here, not an invented spawn: r221 elevator's actual room jump.
        p = dict(room=0x22b, pos=[0, 0, 0], ang=0.0,
                 notes='r221.cpp SceAtExecRoomJump(0x22B, &vecZero, &vecZero, 0); event-only arrival')
        source = dict(kind='source script room jump', file='src/st2/r221.cpp', line=543,
                      expression='SceAtExecRoomJump(0x22B, (Vec*) &vecZero, (Vec*) &vecZero, 0)')
    else:
        raise ValueError('No source-derived part-0 arrival for ' + room)
    if room in ('r112', 'r111', 'r113', 'r11c'):
        p['find'] = 0x00100000
        p['required_status'] = [3, 0x04000000]
    return p, source


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage1-index', required=True, type=Path)
    ap.add_argument('--castle-index', required=True, type=Path)
    ap.add_argument('--base-fixture', required=True, type=Path)
    ap.add_argument('--room-fixture', action='append', default=[], help='ROOM=existing.json')
    ap.add_argument('--iso', default=stage_route.DEFAULT_ISO)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--rooms', nargs='*')
    ap.add_argument('--texture-index-dir', type=Path, help='Texture-fit lane per-room chosen winners JSON')
    ap.add_argument('--prepare-missing', action='store_true')
    ap.add_argument('--dependency-dir', type=Path, help='cx_room_dependencies.py output root')
    ap.add_argument('--arm-tool', type=Path, help='fixture_arm.py supporting --candidate-dir')
    ap.add_argument('--candidate-dir', type=Path)
    ap.add_argument('--arm-label')
    a = ap.parse_args()
    a.out = a.out.resolve()
    repo = HERE.parents[3]
    if a.out == repo or repo in a.out.parents:
        ap.error('generated fixtures/assets must stay outside the repository')
    if any((a.arm_tool, a.candidate_dir, a.arm_label)) and not all((a.arm_tool, a.candidate_dir, a.arm_label)):
        ap.error('--arm-tool, --candidate-dir and --arm-label must be supplied together')
    a.out.mkdir(parents=True, exist_ok=True)
    base = read(a.base_fixture)
    overrides = {k: Path(v) for k, v in (x.split('=', 1) for x in a.room_fixture)}
    idx = read(a.stage1_index)
    for room, data in read(a.castle_index).items():
        idx[room] = dict(data, output=str(Path(data['manifest']).parent / 'rooms' / room))
    iso = GcIso(a.iso)
    scan_path = a.out / 'source-door-scan.json'
    meta_path = a.out / 'source-door-scan.meta.json'
    scan_meta = {'iso': str(Path(a.iso).resolve()), 'iso_sha256': sha(a.iso),
                 'stage_route_sha256': sha(HERE / 'stage_route.py')}
    if scan_path.exists() and meta_path.exists() and read(meta_path) == scan_meta:
        doors = read(scan_path)
    else:
        doors = {**stage_route.scan(iso, 1), **stage_route.scan(iso, 2)}
        write(scan_path, doors)
        write(meta_path, scan_meta)
    repo = HERE.parents[3]
    summary = read(a.out / 'index.json') if (a.out / 'index.json').exists() else {}
    for room in a.rooms or idx:
        out = a.out / room
        out.mkdir(exist_ok=True)
        fixture_source = overrides.get(room, a.base_fixture)
        fixture = copy.deepcopy(read(fixture_source))
        rep = fixture['replace']
        for k in ('dc/warp.txt', 'dc/padscript.txt', 'dc/crashtest.txt', 'dc/codec_ready.txt'):
            rep.pop(k, None)
        blockers = []
        dependency_manifest = a.dependency_dir / 'rooms' / (room + '.json') if a.dependency_dir else None
        if dependency_manifest:
            extras = read(dependency_manifest)
            for k, v in extras['replace_if_absent'].items():
                rep.setdefault(k, v)
        st = 'st' + room[1]
        keys = [st + '/' + room + '.' + ext for ext in ('arc', 'dar')]
        ancillary_status = 'reused-existing-fixture'
        if any(k not in rep or not Path(rep[k]).exists() for k in keys):
            ancillary_status = 'missing'
            if a.prepare_missing:
                try:
                    tool_version = sha(TOOLS / 'le_mirror.py')[:12]
                    rep.update(prepare_room(room, iso, out / ('ancillary-' + tool_version)))
                    ancillary_status = 'prepared-compact-released-audio-unqualified' if room in ROOM_CONTRACTS else 'prepared-le-mirror-uncompact'
                    if room not in ROOM_CONTRACTS:
                        blockers.append('prepare_native_ui.py ROOM_CONTRACTS has no reviewed consumer contract for ' + room + '; ARC/DAR are native LE but uncompact, native render fallback remains unqualified.')
                    blockers.append('New ancillary DAR has no qualified prebuilt AICA room bank; aica_banks room route is incomplete.')
                except Exception as exc:
                    blockers.append('Ancillary preparation: ' + str(exc))
            else:
                blockers.append('Missing converted room ARC/DAR; run with --prepare-missing.')
        world = Path(idx[room]['output'])
        for f in ('ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids'):
            rep['dc/native/' + room + '/' + f] = str(world / f)
        # Loose keys alone cannot override an existing pak. Claude must apply chosen winners to the authoritative pack.
        for pth in sorted((world / 'tex').glob('*.re4tex')):
            rep['dc/tex/' + pth.name[0] + '/' + pth.name] = str(pth)
        texture_selection = a.texture_index_dir / (room + '.json') if a.texture_index_dir else None
        if texture_selection:
            selected = read(texture_selection)
            for row in selected['textures']:
                k = row['key']
                rep['dc/tex/' + k[0] + '/' + k + '.re4tex'] = row['chosen']['path']
        preset, source = entry_for(room, doors)
        views = []
        for suffix, delta, walk in [('entry', 0, False), ('left', -0.65, False), ('right', 0.65, False), ('walk', 0, True)]:
            p = copy.deepcopy(preset)
            p['ang'] = (p['ang'] + delta + math.pi) % (2 * math.pi) - math.pi
            if walk:
                p['acts'] = [('fwd', 360, 12)]
            name = 'cx-' + room + '-' + suffix
            wpath = out / (name + '.txt')
            text = warp.lines_for(p, dump=True, name=name)
            if p.get('required_status'):
                text += 'status %d 0x%08x\n' % tuple(p['required_status'])
            wpath.write_text(text)
            f = copy.deepcopy(fixture)
            f['replace']['dc/warp.txt'] = str(wpath)
            f['remove'] = sorted(set(f.get('remove', [])) - set(f['replace']))
            f.setdefault('provenance', {})['cx_room'] = dict(room=room, source_fixture=str(fixture_source),
                warp_source=source, camera_delta_radians=delta, unarmed=True,
                note='Must use fixture_arm.py for this arm. No runtime acceptance claimed.')
            fpath = out / (name + '.unarmed.json')
            write(fpath, f)
            armed_path, arm_error = None, None
            if a.arm_tool:
                armed_path = out / (name + '.armed.json')
                try:
                    command([sys.executable, a.arm_tool, fpath, armed_path, a.arm_label,
                             '--candidate-dir', a.candidate_dir], out / (name + '.arm.log'))
                except RuntimeError as exc:
                    arm_error = str(exc)
                    blockers.append('Overlay arming failed: ' + arm_error)
                    armed_path = None
            views.append(dict(name=name, warp=str(wpath), fixture=str(fpath), kind=suffix,
                              armed_fixture=str(armed_path) if armed_path else None, arm_error=arm_error,
                              angle_radians=p['ang'], runtime_status='UNRUN', safety='source arrival; camera/walk unverified'))
        if room[1] == '2':
            blockers += ['test9 ROUTE_CH21=1 excludes WORLD_STAGE_MODULES=1 (Makefile269-271); castle module registration is unavailable.',
                         'Castle events/enemy archives/native model registries and AICA route require gameplay-owner qualification.']
        if preset.get('required_status'):
            blockers.append('Required status 3 0x04000000 is preserved in warp, but 90606dcf dbgwarp_bridge.cpp does not parse status; CH22 runtime required.')
        for k in keys:
            if k not in rep:
                blockers.append('Required room archive absent from fixture: ' + k)
        missing = [dict(destination=k, source=v) for k, v in rep.items() if not Path(v).is_file()]
        try:
            mod = stage_module(repo, int(room[1:], 16))
            refs = script_refs(repo, int(room[1:], 16))
        except Exception as exc:
            mod, refs = None, {'error': str(exc)}
        deps = [dict(destination=k, source=v, bytes=Path(v).stat().st_size, sha256=sha(v))
                for k, v in rep.items() if (k in keys or k.startswith('dc/native/' + room + '/')) and Path(v).is_file()]
        result = dict(room=room, world_source=idx[room], fixture_source=str(fixture_source), entry_source=source,
                      texture_selection=str(texture_selection) if texture_selection else None,
                      dependency_manifest=str(dependency_manifest) if dependency_manifest else None,
                      views=views, ancillary_status=ancillary_status, dependencies=deps,
                      stage_module=mod, script_refs=refs, blockers=blockers, missing_sources=missing,
                      pack_precedence='Pack entries win. World texture candidate list must win the Claude-managed pack; loose files are insufficient.',
                      firstpass=dict(status='UNRUN', texture_gate='UNRUN', gc_world_model_fallback_gate='UNRUN'),
                      gc_usage='GC source mechanics/collision/archive identities; PS2 world rendering. Any GC world/model draw is a failed first-pass gate.')
        write(out / 'manifest.json', result)
        summary[room] = dict(manifest=str(out / 'manifest.json'), views=views, ancillary_status=ancillary_status,
                             blockers=blockers, missing_sources=len(missing))
        write(a.out / 'index.json', summary)
        print(room, ancillary_status, 'missing', len(missing), 'blockers', len(blockers), flush=True)


if __name__ == '__main__':
    main()