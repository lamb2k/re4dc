"""Independent read-only current4be final-media review. Writes only this directory."""
from pathlib import Path
import hashlib, importlib.util, json, re, subprocess, time

HERE = Path(__file__).resolve().parent
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
TREE = Path('/root/work/lanes/dedup-offline23-qa-4be08e01')
SOURCE = '4be08e0110592510e3630c01fa9f49b3ac2fed3d'
TOOLS = TREE / 'port/dreamcast/tools/d367'

def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(p):
    return json.loads(p.read_text())

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def source_tool(relative):
    path = TREE / relative
    assert path.read_bytes() == git('show', SOURCE + ':' + relative), relative
    return sha(path)

def streamed_manifest(path, iso):
    # The frozen source parser supplies directory names/extents. This independent
    # reader hashes every actual member in <=602112-byte raw-sector batches;
    # it never extracts payloads or invokes any patch/master command.
    tr = iso.Track(path, 45000)
    assert tr.raw and tr.ss == 2352
    result = {}
    for name, lba, length in sorted(iso.files(tr)):
        name = name.lstrip('/')
        assert name not in result and name and '..' not in Path(name).parts
        assert lba >= tr.base and lba + (length + 2047) // 2048 <= tr.base + tr.count
        digest = hashlib.sha256()
        remaining = length
        with path.open('rb') as stream:
            stream.seek((lba - tr.base) * 2352)
            while remaining:
                count = min(256, (remaining + 2047) // 2048)
                raw = stream.read(count * 2352)
                assert len(raw) == count * 2352
                for offset in range(0, len(raw), 2352):
                    take = min(2048, remaining)
                    digest.update(raw[offset + 16:offset + 16 + take])
                    remaining -= take
        result[name] = {'size': length, 'sha256': digest.hexdigest()}
    tr.f.close()
    return result

def validate_gate(arm, kind, media, pins, parser_sha):
    cap = E / f'qa-{arm}-{kind}-console-r1'
    gate = read(cap / 'qa-gate.json')
    run = read(cap / 'run-result.json')
    bound = read(cap / 'bounded-launch.json')
    output = (cap / 'run-output.txt').read_text(errors='replace')
    assert gate['status'] == 'PASS' and gate['source'] == SOURCE
    for name, expected in gate['sha256'].items():
        assert sha(cap / name) == expected, (arm, kind, name)
    assert run['status'] == 'RUN_COMPLETE' and run['stopped'] == 'goal'
    assert run['errors'] == [] and run['emu'] == 'console' and run['emulator_exited']
    assert run['seconds'] == 50 and run['elapsed_s'] <= 55
    assert bound['deadline_seconds'] == 55 and not bound['deadline_fired']
    assert bound['guest_exited'] and bound['guest_observed_elapsed_s'] <= 55
    assert int((cap / 'flycast.pid').read_text()) == bound['pid']
    assert sha(cap / 'flycast.exe') == bound['expected_executable_sha256']
    assert bound['harness_sha256'] == parser_sha
    assert gate['programme_elf_sha256'] == pins['elf_sha256']
    assert gate['final_track03_sha256'] == media['tracks']['track03.bin']['sha256']
    assert re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$', (cap / 'emu.cfg').read_text()) == ['no']
    faults = [line for line in output.splitlines() if re.search(r'\b(?:HALT|FAULT|FATAL|ASSERT)\b|MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))', line)]
    assert faults == [], (arm, kind, faults)
    witness = []
    if kind == 'boot':
        assert gate['media'] == 'FINAL_STANDARD_GDI' and run['fixtures'] == {}
        assert (cap / 'disc.gdi').read_bytes() == (Path(media['path']) / 'gdemu/disc.gdi').read_bytes()
        assert run['disc'].replace('\\', '/') == 'C:/' + str(Path(media['path']) / 'gdemu').removeprefix('/mnt/c/')
        assert run['tracks'] == {n: media['tracks'][n]['bytes'] for n in ['disc.gdi', 'track01.bin', 'track02.raw', 'track03.bin']}
        keys = run['key_log']
        assert len(keys) == 4 and all(row['windows'] > 0 for row in keys)
        assert [row['keys'] for row in keys] == [['down'], ['a'], ['a'], ['a']]
        assert not run.get('keys_pending')
        for marker in ['qa: boot choice /cd/dc/qa/r100.txt', 'phase=enter room=100']:
            assert marker in output
            witness.extend(line for line in output.splitlines() if marker in line)
    else:
        assert gate['media'] == 'SEPARATE_FIXTURE_PROXY_EXACT_FINAL_PROGRAMME_ALL14_DATA'
        proxy = read(E / f'qa-proxy-{arm}-identity-r1.json')
        assert run['tracks']['track03_sha256'] == proxy['track03_sha256']
        assert proxy['final_track03_sha256'] == media['tracks']['track03.bin']['sha256']
        assert gate['proxy_identity_sha256'] == sha(E / f'qa-proxy-{arm}-identity-r1.json')
        assert run['tracks']['kind'] == 'twin' and not run['key_log']
        for name, record in run['fixtures'].items():
            fixture = cap / ('fixture-' + name + '.txt')
            if record['bytes']:
                assert fixture.stat().st_size == record['bytes'] and sha(fixture) == record['sha256']
        if kind == 'warp':
            for marker in ['qa: auto teleport /cd/dc/qa/r103.txt', 'warp: qa: preset armed at soft reset', 'phase=enter room=101', 'phase=enter room=103']:
                assert marker in output
                witness.extend(line for line in output.splitlines() if marker in line)
        else:
            for movie, count in [('10003', 1465), ('10020', 571), ('10030', 340)]:
                lines = [line for line in output.splitlines() if 'route movie terminal=1 id=' + movie + ' ' in line]
                assert any(f'frames={count}/{count} uploaded={count} presented={count}' in line for line in lines)
                witness.extend(lines)
            last_borrow = output.rfind('MOVIEARENA borrow id=10030')
            assert last_borrow >= 0 and re.search(r'MOVIEARENA return[^\n]*restored=1', output[last_borrow:])
            heap = int(re.findall(r'heap_before=(\d+)', '\n'.join(witness))[-1])
            assert heap == gate['heap_before'] == (48768 if arm == 'off' else 98496)
    return {'kind': kind, 'media': gate['media'], 'gate_sha256': sha(cap / 'qa-gate.json'),
        'capture': str(cap), 'elapsed_s': bound['guest_observed_elapsed_s'], 'pid': bound['pid'],
        'harness_sha256': parser_sha, 'config_sha256': sha(cap / 'emu.cfg'),
        'actual_LimitFPS': 'no', 'fault_rows': faults, 'witness_rows': witness,
        'heap_before': gate.get('heap_before'), 'status': 'PASS'}

def main():
    # Seal is mandatory. The reviewer never creates or repairs package outputs.
    seal_path = E / 'private-qa-pair-seal-r1.json'
    seal = read(seal_path)
    assert seal['source'] == SOURCE and seal['status'] == 'LOCAL_NORMAL_QA_PAIR_PASS_ROOT_REVIEW_PENDING'
    media = read(E / 'qa-media-r1/pair-media-identity.json')
    plan = read(E / 'private-qa-plan-prelink.json')
    pins = read(E / 'qa-programme-pins-r1.json')
    assert media['source'] == pins['source'] == plan['source'] == SOURCE
    assert pins['plan_sha256'] == sha(E / 'private-qa-plan-prelink.json')
    assert git('rev-parse', 'HEAD').decode().strip() == SOURCE
    assert git('status', '--porcelain', '--untracked-files=no') == b''
    tools = {path: source_tool(path) for path in plan['tool_source_sha256']}
    assert tools == plan['tool_source_sha256']
    recipe = git('show', SOURCE + ':port/dreamcast/tools/d367/rr/recipe.conf')
    assert hashlib.sha256(recipe).hexdigest() == '92e2322daecde3e50699bd28303d177379418d8c3ba3b76ab7260836777ae898'
    assert len(re.search(rb'^DATA="([^"]+)"$', recipe, re.M)[1].split(b',')) == 29
    iso_relative = 'port/dreamcast/tools/d367/fullplay/fp_iso.py'
    iso_sha = source_tool(iso_relative)
    spec = importlib.util.spec_from_file_location('frozen_iso_reader', TREE / iso_relative)
    iso = importlib.util.module_from_spec(spec); spec.loader.exec_module(iso)
    fp_run_sha = source_tool('port/dreamcast/tools/d367/fullplay/fp_run.py')
    fp_run = (TOOLS / 'fullplay/fp_run.py').read_text()
    assert 'if p.value == pid:' in fp_run and 'press(proc.pid,' in fp_run and 'PostMessageW' in fp_run
    original = read(Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard/off/manifest.json'))
    original_sha = sha(Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard/off/manifest.json'))
    report = {'schema': 1, 'status': 'INDEPENDENT_FINAL_MEDIA_READBACK_AND_QA_RECEIPTS_CLEAR',
        'source': SOURCE, 'reviewer': '/root/gc_gate_seed_sol61', 'guest_runs': 0, 'builds': 0,
        'review_script_sha256': sha(Path(__file__)), 'seal_sha256': sha(seal_path),
        'pair_media_identity_sha256': sha(E / 'qa-media-r1/pair-media-identity.json'),
        'programme_pins_sha256': sha(E / 'qa-programme-pins-r1.json'),
        'original_standard_off_manifest_sha256': original_sha, 'source_tool_hashes': tools,
        'iso_directory_parser_sha256': iso_sha, 'arms': {}}
    manifests = {}
    for arm, mode in [('off', '0'), ('on', '3')]:
        x = media['arms'][arm]; p = pins['arms'][arm]; d = Path(x['path'])
        identity = read(d / 'IDENTITY.json')
        assert identity['source'] == SOURCE and identity['scenery_dedup'] == int(mode)
        assert sha(d / 'IDENTITY.json') == seal['arms'][arm]['identity_sha256']
        assert sha(d / 'SHA256SUMS.txt') == seal['arms'][arm]['sha256sums_sha256']
        checksums = {}
        for line in (d / 'SHA256SUMS.txt').read_text().splitlines():
            expected, relative = line.split('  ', 1)
            assert relative not in checksums and '..' not in Path(relative).parts and not Path(relative).is_absolute()
            path = d / relative
            before = path.stat(); actual = sha(path); after = path.stat()
            assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
            assert actual == expected, (arm, relative)
            checksums[relative] = {'sha256': actual, 'bytes': before.st_size}
        assert set(checksums) == {str(f.relative_to(d)) for f in d.rglob('*') if f.is_file() and f.name != 'SHA256SUMS.txt'}
        for name, record in x['tracks'].items():
            assert checksums['gdemu/' + name] == record
        assert (d / 'gdemu/disc.gdi').read_text().splitlines() == ['3', '1 0 4 2352 track01.bin 0', '2 600 0 2352 track02.raw 0', '3 45000 4 2352 track03.bin 0']
        for profile in ['standard', 'loader']:
            checked = subprocess.run(['python3', '-B', str(TOOLS / 'disc_lint.py'), '--profile', profile, str(d / 'gdemu/disc.gdi')], capture_output=True, text=True)
            assert checked.returncode == 0, (arm, profile, checked.stdout, checked.stderr)
            with (HERE / (arm + '-lint-' + profile + '.txt')).open('x') as log:
                log.write(checked.stdout + checked.stderr)
        manifest = streamed_manifest(d / 'gdemu/track03.bin', iso)
        manifests[arm] = manifest
        assert manifest == read(Path(x['manifest']))
        assert sha(Path(x['manifest'])) == x['manifest_sha256']
        assert manifest == read(E / f'qa-media-r1/{arm}-final-post-manifest.json')
        assert manifest['1ST_READ.BIN'] == {'sha256': p['raw_sha256'], 'size': p['raw_bytes']}
        out = Path(p['path'])
        assert sha(out / 're4dc-game.elf') == p['elf_sha256']
        assert sha(out / 'resolved-knobs.txt') == p['resolved_sha256']
        assert (out / 'stack.txt').read_text() == SOURCE + '\n' and not (out / 'missing.txt').read_bytes()
        k = dict(line.split('=', 1) for line in (out / 'resolved-knobs.txt').read_text().splitlines() if '=' in line)
        for name, value in plan['arms'][arm]['required_resolved_knobs'].items():
            assert k[name] == value
        required = {'SCENERY_DEDUP': mode, 'SCENERY_EMIT_PREFETCH': '0', 'SCENERY_SELECT_LEAN2': '0',
            'QA_MENU': '1', 'QA_TEST': '23', 'QA_SRC': '4be08e01', 'PC_SAMPLER': '0',
            'WORLD_METER': '0', 'STAT_DIAG': '0', 'KOS_CACHE_P2_DIAG': '0', 'VRAM_ROOM_ARENA': '0',
            'KOS_WATCH': '0', 'KOS_SQUEEZE': '0', 'NATIVE_MODEL_REGISTRY_CENSUS': '0',
            'SCENERY_SELECT_ONLY': '1', 'SCENERY_REPLAY_LEAN': '1', 'SCENERY_SUBMIT_BATCH': '1',
            'STAT_ROUTINE_BYTES': '1', 'ESP_POOL_RECYCLE': '1', 'R117_EFFECT_FAILURE_SAFE': '1',
            'KOS_CACHE_P2': '1', 'R10C_SPAWN_LIVE_GUARD': '1', 'EM_READ_RETRY': '1'}
        for name, value in required.items(): assert k[name] == value, (arm, name)
        assert len(p['overlays']) == 14
        programme = {'1ST_READ.BIN'} | {'dc/' + name for name in p['overlays']}
        for name, expected in p['overlays'].items():
            assert sha(out / name) == expected == manifest['dc/' + name]['sha256']
        for name, record in original.items():
            if name not in programme: assert manifest[name] == record, ('original changed', arm, name)
        alternates = {a['destination'] for a in plan['alternates']}
        assert len(alternates) == 4
        for alternate in plan['alternates']:
            assert manifest[alternate['destination']] == {'sha256': alternate['sha256'], 'size': alternate['bytes']}
            assert sha(Path(alternate['path'])) == alternate['sha256']
        assert set(manifest) - set(original) - alternates <= {n for n in manifest if n.startswith('dc/qa/')}
        for room, base in plan['baseline_packages'].items():
            assert manifest[f'dc/native/{room}/ps2-world.re4mesh'] == {'sha256': base['sha256'], 'size': base['bytes']}
        assert not any(n in manifest for n in ['dc/warp.txt', 'dc/padscript.txt', 'dc/w11.txt', 'dc/crashtest.txt'])
        proxy = read(E / f'qa-proxy-{arm}-identity-r1.json')
        proxy_manifest = read(E / f'qa-proxy-{arm}-r1/base-manifest.json')
        assert sha(E / f'qa-proxy-{arm}-r1/base-manifest.json') == proxy['proxy_manifest_sha256']
        changed = {n for n in manifest.keys() | proxy_manifest.keys() if manifest.get(n) != proxy_manifest.get(n)}
        assert changed == {'dc/warp.txt', 'dc/padscript.txt', 'dc/w11.txt'} == set(proxy['only_differences'])
        retired = read(E / f'qa-{arm}-proxy-retirement-r1.json')
        assert retired['status'] == 'REMOVED_ONLY_EXACT_AUTHORIZED_NEW_PROXY_BACKING'
        assert retired['source'] == SOURCE and retired['arm'] == arm
        assert retired['sha256'] == proxy['track03_sha256']
        assert Path(retired['resolved_target']) == E / f'qa-proxy-{arm}-r1/track03.iso'
        assert not Path(retired['resolved_target']).exists() and retired['target_absent']
        assert retired['nlink'] == 1 and retired['all_final_tracks_full_readback_equal']
        for name, record in retired['proxy_metadata_retained'].items():
            file = E / f'qa-proxy-{arm}-r1' / name
            assert sha(file) == record['sha256'] and file.stat().st_size == record['bytes']
        gates = [validate_gate(arm, kind, x, p, fp_run_sha) for kind in ['boot', 'warp', 'h2']]
        for gate in gates: assert retired['arm_gates'][gate['kind']] == gate['gate_sha256']
        for name in ['README.txt', 'STEPS.txt', 'QUALIFICATION-PENDING.txt']:
            assert (d / name).is_file()
        text = (d / 'README.txt').read_text()
        assert 'Mendez late-pair' in text and 'separate' in text and 'proxies' in text
        assert 'two minutes' in (d / 'STEPS.txt').read_text()
        report['arms'][arm] = {'path': str(d), 'all_folder_files': checksums, 'all_folder_file_count': len(checksums),
            'iso_file_count': len(manifest), 'iso_payload_bytes': sum(r['size'] for r in manifest.values()),
            'all_actual_iso_members_equal_sealed_manifest': True, 'original_nonprogramme_files_preserved': True,
            'exact4_common_alternates': plan['alternates'], 'programme': p, 'resolved_required': required,
            'gates': gates, 'proxy_retirement_sha256': sha(E / f'qa-{arm}-proxy-retirement-r1.json'),
            'identity_sha256': sha(d / 'IDENTITY.json'), 'sha256sums_sha256': sha(d / 'SHA256SUMS.txt')}
        print('ARM_INDEPENDENT_READBACK_CLEAR', arm, len(manifest), flush=True)
    differences = sorted(n for n in manifests['off'].keys() | manifests['on'].keys() if manifests['off'].get(n) != manifests['on'].get(n))
    assert set(differences) == set(media['only_programme_differences'])
    assert len(differences) == 15
    report['actual_only_arm_differences'] = differences
    report['qa_heap_gain'] = 98496 - 48768
    report['limits'] = ['Review starts from final sealed bytes; no guests, SDK, builds, source/runtime/recipe/media edits.',
        'Direct final-GDI boot proof is separate from fixture-proxy menu warp/H2; retired proxy payloads cannot be independently rehashed now. Preserved proxy manifests, identities and captures are verified.',
        'Normal QA heap is separate from standard non-QA memory gates; no hardware speed or physical acceptance.',
        'Known baseline Mendez material failure remains; common original assets prove no separate root private repair was substituted.',
        'Root owns integration, recipe and private/physical acceptance; no SD/publication.']
    target = HERE / 'RESULTS.json'
    with target.open('x') as stream: stream.write(json.dumps(report, indent=2) + '\n')
    print('REVIEW_CLEAR', sha(target), flush=True)

if __name__ == '__main__':
    main()
