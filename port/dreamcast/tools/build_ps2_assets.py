#!/usr/bin/env python3
"""Build the reviewed PS2-world recipe from local discs; see PS2_ASSET_BUILD.md.

No renderer or game-state changes. Never overwrite an existing output tree.
An unchanged completed build is verified and reused; changes need a new output.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
PROFILE = HERE / 'ps2_assets' / 'worlds.json'
from d367.ps2world import world_registry  # existing runtime-derived host checks


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def record(path):
    return dict(bytes=path.stat().st_size, sha256=sha(path))


def host_tools():
    result = {}
    for name in ('mono', 'powerpc-linux-gnu-gcc', 'qemu-ppc', 'g++'):
        exe = shutil.which(name)
        require(exe is not None, f'missing {name}; install the prerequisites in PS2_ASSET_BUILD.md')
        version = subprocess.run([exe, '--version'], capture_output=True, text=True, check=True, timeout=15)
        result[name] = dict(version=version.stdout.splitlines()[0], sha256=sha(Path(exe).resolve()))
    return result


def runtime_checker(scratch):
    # Fresh scratch avoids stale compiler/header/shim binaries in a shared cache.
    world_registry.CACHE = scratch
    return world_registry.checker()[0]


def iso_file(f, name):
    """Find an ISO9660 file from the primary descriptor, without mounting the disc."""
    f.seek(16 * 2048)
    pvd = f.read(2048)
    require(pvd[:7] == b'\x01CD001\x01', 'PS2 source is not an ISO9660 image')
    extent, size = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
    for component in name.strip('/').upper().split('/'):
        f.seek(extent * 2048)
        data = f.read(size)
        offset, found = 0, None
        while offset < len(data):
            length = data[offset]
            if not length:
                offset = (offset // 2048 + 1) * 2048
                continue
            require(length >= 34 and offset + length <= len(data), 'invalid ISO directory record')
            row = data[offset:offset + length]
            label = row[33:33 + row[32]].decode('ascii', 'replace').split(';')[0]
            if label == component:
                found = struct.unpack_from('<I', row, 2)[0], struct.unpack_from('<I', row, 10)[0]
                break
            offset += length
        require(found is not None, 'PS2 disc missing ' + name)
        extent, size = found
    return extent * 2048, size


def check_ps2(path, pin):
    require(path.is_file(), 'PS2_ISO must point to a local USA PS2 ISO')
    require(path.stat().st_size == pin['bytes'], 'unsupported PS2 ISO size; see PS2_ASSET_BUILD.md')
    with path.open('rb') as f:
        off, size = iso_file(f, 'SYSTEM.CNF')
        f.seek(off)
        system = f.read(size)
        require(hashlib.sha256(system).hexdigest() == pin['system_cnf_sha256'],
                'unsupported PS2 SYSTEM.CNF (expected SLUS_211.34, VER=1.01)')
        off, size = iso_file(f, 'SLUS_211.34')
        f.seek(off)
        require(hashlib.sha256(f.read(size)).hexdigest() == pin['executable_sha256'],
                'unsupported PS2 executable revision')
        afs_offset, afs_size = iso_file(f, 'DATA/BIO4DAT.AFS')
    require(afs_offset == pin['afs_sector'] * 2048 and afs_size == pin['afs_bytes'],
            'unexpected BIO4DAT.AFS location or size')
    print('Checking PS2 disc SHA-256...', flush=True)
    digest = sha(path)
    require(digest == pin['sha256'], 'PS2 ISO SHA-256 differs from the supported source')
    return dict(path=str(path), sha256=digest, bytes=path.stat().st_size)


def check_gc(path, pin):
    require(path.is_file(), 'GC_ISO must point to the G4BE08 debug Disc 1 (lighting calibration)')
    with path.open('rb') as f:
        header = f.read(32)
    require(header[:7] == b'G4BE08\0' and header[28:32] == b'\xc2\x33\x9f\x3d',
            'GC_ISO is not G4BE08 GameCube Disc 1')
    result = record(path)
    require(result == pin, 'GC Disc 1 hash differs from the supported lighting source')
    return dict(path=str(path), **result)


def fetch_tool(cache, name, pin):
    """Pinned release ZIP, extracted under an exclusively created directory."""
    root = cache / (name + '-' + pin['archive_sha256'][:12])
    exe = root / pin['exe']
    if root.exists():
        require(exe.is_file() and sha(exe) == pin['exe_sha256'],
                f'incomplete or changed tool cache: {root}; choose a new ASSET_TOOLS directory')
        return exe
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / (pin['archive_sha256'] + '.zip')
    if not archive.exists():
        print('Downloading pinned ' + name + ' tool...', flush=True)
        request = urllib.request.Request(pin['url'], headers={'User-Agent': 're4dc-asset-build'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(16 * 1024 * 1024 + 1)
        require(hashlib.sha256(data).hexdigest() == pin['archive_sha256'], name + ' ZIP hash mismatch')
        with archive.open('xb') as f:
            f.write(data)
    require(sha(archive) == pin['archive_sha256'], name + ' cached ZIP hash mismatch')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            path = Path(member.filename.replace('\\', '/'))
            require(not path.is_absolute() and '..' not in path.parts and ':' not in str(path),
                    'unsafe tool ZIP member: ' + member.filename)
            require((member.external_attr >> 16) & 0o170000 != 0o120000, 'tool ZIP contains a symlink')
        root.mkdir()
        z.extractall(root)
    require(exe.is_file() and sha(exe) == pin['exe_sha256'], name + ' executable hash mismatch')
    return exe


def source_hashes():
    names = ['build_ps2_assets.py', 'ps2_room_extract.py', 'ps2_room_r4im.py', 'ps2_room_ids.py',
             'gc_room_lit.py', 'room_smd.py', 'decode_yz2.py', 'convert_room_bins.py', 'mesh_lod.py', 'ps2src.py',
             'assetpipe/rooms.py', 'assetpipe/config.py', 'assetpipe/util.py',
             'd367/ps2world/world_registry.py', 'd367/ps2world/ps2_world_check.cpp',
             'd367/ps2world/hostinc/kos/fs.h', '../room/instanced_mesh.hpp', '../room/room_package.hpp',
             '../../../src/game/yz2asm.cpp', '../../../src/game/yz2code.cpp']
    files = [HERE / name for name in names]
    files += sorted(p for p in (HERE / 'ps2_assets').glob('*.py') if not p.name.startswith('test_'))
    files += [PROFILE, HERE / 'ps2_assets/requirements.txt']
    return {str(p.relative_to(HERE)): sha(p) for p in files}


def runtime_files(root):
    return sorted([root / ('ps2-world.' + suffix) for suffix in ('re4mesh', 'r4pw', 'ids')] +
                  list((root / 'tex').glob('*.re4tex')))


def validate_runtime(root, checker):
    """Check file integrity, IDs, and every texture binding before staging anything."""
    import ps2_room_ids
    mesh = (root / 'ps2-world.re4mesh').read_bytes()
    require(len(mesh) >= 112, 'short R4IM')
    magic, version, total, crc = struct.unpack_from('<4s3I', mesh)
    require(magic == b'R4IM' and version in (2, 3) and total == len(mesh), 'invalid R4IM header')
    require(crc == zlib.crc32(mesh[80:]), 'R4IM CRC mismatch')
    accepted = world_registry.run_check(checker, root / 'ps2-world.re4mesh', root / 'ps2-world.r4pw')
    require(accepted['ok'], 'runtime world open rejected: ' + str(accepted['why']))
    side = (root / 'ps2-world.r4pw').read_bytes()
    require(len(side) >= 32, 'short R4PW')
    magic, version, npl, nparts, nmesh, crc, _, _ = struct.unpack_from('<4s7I', side)
    require(magic == b'R4PW' and version == 1 and len(side) == 32 + nparts * 16 + npl * 52,
            'invalid R4PW shape')
    require(zlib.crc32(side[32:]) == crc, 'R4PW CRC mismatch')
    require((nmesh, nparts) == struct.unpack_from('<2I', mesh, 16), 'mesh/sidecar counts differ')
    _, fields = ps2_room_ids.r4pw(root / 'ps2-world.r4pw')
    ids = (root / 'ps2-world.ids').read_bytes()
    require(len(ids) >= 16, 'short R4ID')
    im, iv, count, icrc = struct.unpack_from('<4s3I', ids)
    require(im == b'R4ID' and iv == 1 and icrc == crc and count == max(fields) + 1 and
            len(ids) == (16 + count + 31) // 32 * 32, 'R4ID does not match its sidecar')
    required = {}
    for i in range(nparts):
        tex, tex2, width, height, *_ = struct.unpack_from('<IIHHBBBB', side, 32 + i * 16)
        required.setdefault(f'{tex:08x}-{tex2:08x}.re4tex', set()).add((width, height))
    found = {p.name for p in (root / 'tex').glob('*.re4tex')}
    require(set(required) == found, 'missing or unused texture bindings: ' + str(set(required) ^ found))
    vram = 0
    for name in sorted(required):
        data = (root / 'tex' / name).read_bytes()
        require(len(data) >= 144, 'short RE4DCTX: ' + name)
        h = struct.unpack_from('<8s10I', data)
        require(h[:7] == (b'RE4DCTX\0', 2, 48, 96, 1, 48, 144) and
                len(data) == 144 + h[7] and zlib.crc32(data[48:]) == h[8], 'invalid RE4DCTX: ' + name)
        for width, height in required[name]:
            why, rule = world_registry.tex_package_error(data, width, height)
            require(why is None and rule == 'header', f'runtime texture rejected: {name}: {why}')
        desc = struct.unpack_from('<64s8I', data, 48)
        _, w, height, fmt, off, size, flags, payload, _ = desc
        expected = 2048 + w * height // 4 if payload == 2 else w * height * 2
        require(w > 0 and height > 0 and not w & (w - 1) and not height & (height - 1) and
                fmt in (0, 1, 2) and payload in (1, 2) and off == 144 and size == h[7] == expected,
                'invalid texture descriptor: ' + name)
        texels = data[144:]
        fnv = 2166136261
        for byte in texels:
            fnv = ((fnv ^ byte) * 16777619) & 0xffffffff
        require(name == f'{zlib.crc32(texels):08x}-{fnv:08x}.re4tex', 'texture identity mismatch: ' + name)
        vram += size
    return dict(placements=npl, parts=nparts, meshes=nmesh, textures=len(required), texture_vram_bytes=vram,
                runtime_open='accepted', heap_bytes=accepted['heap_bytes'])


def verify_overlay(out, rooms, checker):
    """Derive the complete inventory from checked room outputs, never from a manifest."""
    expected, staged = {}, {}
    for room in rooms:
        root = out / 'rooms' / room
        validate_runtime(root, checker)
        for path in runtime_files(root):
            value = record(path)
            expected[str(path.relative_to(out))] = value
            target = ('stage/tex/' if path.suffix == '.re4tex' else 'stage/rooms/' + room + '/') + path.name
            if target in staged:
                # Same key in two rooms may have different descriptor labels only.
                require(staged[target].read_bytes()[112:] == path.read_bytes()[112:],
                        'texture identity collision: ' + path.name)
            else:
                staged[target] = path
                expected[target] = value
    actual = {str(p.relative_to(out)) for p in (out / 'stage').rglob('*') if p.is_file()}
    require(actual == set(staged), 'staged inventory differs: ' + str(actual ^ set(staged)))
    for target in staged:
        require(record(out / target) == expected[target], 'staged bytes differ from room output: ' + target)
    return expected


def run(script, args, log):
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    env.pop('RE4_WORLD_AGENT', None)
    env.pop('RE4_TOOLS', None)
    with log.open('w') as f:
        process = subprocess.run([sys.executable, str(HERE / script), *map(str, args)],
                                 env=env, stdout=f, stderr=subprocess.STDOUT)
    require(process.returncode == 0, f'{script} failed; see {log}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ps2-iso', default=os.environ.get('PS2_ISO', ''))
    ap.add_argument('--gc-iso', default=os.environ.get('GC_ISO', ''))
    ap.add_argument('--out', type=Path, default=Path(os.environ.get('ASSETS_OUT') or '.assets/worlds'))
    ap.add_argument('--tools', type=Path, default=Path(os.environ.get('ASSET_TOOLS') or '.assets/tools'))
    ap.add_argument('--rooms', nargs='+', default=(os.environ.get('ROOMS') or 'r102 r106').split())
    a = ap.parse_args()
    profile = json.loads(PROFILE.read_text())
    rooms = list(dict.fromkeys(a.rooms))
    require(rooms and all(re.fullmatch('r[0-9a-f]{3}', room) for room in rooms), 'invalid room names')
    require(all(room in profile['rooms'] for room in rooms),
            'room not in the reviewed profile; r100/r101 and new rooms need their own reviewed recipe')
    toolchain = host_tools()
    versions = {name: importlib.metadata.version(name) for name in profile['python_packages']}
    require(versions == profile['python_packages'], 'install the pinned ps2_assets/requirements.txt')
    ps2, gc = Path(a.ps2_iso).resolve(), Path(a.gc_iso).resolve()
    sources = dict(ps2=check_ps2(ps2, profile['source']), gc=check_gc(gc, profile['gc_source']))
    fingerprint = dict(sources={key: value['sha256'] for key, value in sources.items()},
                       scripts=source_hashes(), packages=versions, rooms=rooms, platform=sys.platform,
                       python=sys.version, recipe=profile, host_tools=toolchain)
    with tempfile.TemporaryDirectory(prefix='re4dc-world-check-') as scratch:
        build(a, profile, sources, fingerprint, runtime_checker(Path(scratch)))


def build(a, profile, sources, fingerprint, checker):
    rooms = fingerprint['rooms']
    ps2, gc = Path(sources['ps2']['path']), Path(sources['gc']['path'])
    out = a.out.resolve()
    if out.exists():
        manifest_path = out / 'manifest.json'
        require(manifest_path.is_file(), f'output already exists without a completed manifest: {out}; use a new ASSETS_OUT')
        old = json.loads(manifest_path.read_text())
        require(old['fingerprint'] == fingerprint, 'inputs or recipe changed; choose a new ASSETS_OUT')
        verified = verify_overlay(out, rooms, checker)
        require(old['runtime_files'] == verified, 'completed output inventory or bytes changed')
        print('Verified existing build: ' + str(out))
        return
    tools = {name: fetch_tool(a.tools.resolve(), name, pin) for name, pin in profile['tools'].items()}
    out.mkdir(parents=True, exist_ok=False)
    (out / 'logs').mkdir()
    import ps2_room_extract as extract
    manifest = dict(fingerprint=fingerprint, sources=sources, rooms={}, runtime_files={})
    with ps2.open('rb') as f:
        index, digest = extract.afs_index(f, profile['source']['afs_sector'])
        require(digest == profile['source']['afs_index_sha256'], 'AFS index differs from supported source')
        for room in rooms:
            print('Extracting and converting ' + room + '...', flush=True)
            inputs = out / 'inputs' / room
            extracted = extract.extract(room, f, index, out / 'work' / room, inputs, tools['dat'], tools['smd'])
            require(extracted['scenario_smd'] is not None, 'room has no scenario SMD: ' + room)
            run('gc_room_lit.py', [room, inputs / 'gc-lit-cut0.json', '--iso', gc], out / 'logs' / (room + '-light.log'))
            result = out / 'rooms' / room
            run('ps2_room_r4im.py', [room, inputs, result, *profile['converter_args']], out / 'logs' / (room + '-convert.log'))
            checked = validate_runtime(result, checker)
            manifest['rooms'][room] = dict(extraction=extracted, lighting=record(inputs / 'gc-lit-cut0.json'), validation=checked)
            for p in runtime_files(result):
                manifest['runtime_files'][str(p.relative_to(out))] = record(p)
    # Stage a candidate overlay; this is not an ISO, release fixture, or an installed game.
    stage = out / 'stage'
    (stage / 'tex').mkdir(parents=True)
    for room in rooms:
        (stage / 'rooms' / room).mkdir(parents=True)
        for src in runtime_files(out / 'rooms' / room):
            dst = stage / ('tex' if src.suffix == '.re4tex' else 'rooms/' + room) / src.name
            if dst.exists():
                # The descriptor label can name a different room; payload identity must be identical.
                require(dst.read_bytes()[112:] == src.read_bytes()[112:], 'texture identity collision: ' + src.name)
            else:
                shutil.copyfile(src, dst)
    manifest['runtime_files'] = verify_overlay(out, rooms, checker)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Validated candidate world overlay: ' + str(stage))
    print('Integration still needs the matching build, texture-pack rebuild, and release gates.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError, importlib.metadata.PackageNotFoundError) as exc:
        raise SystemExit(str(exc))
