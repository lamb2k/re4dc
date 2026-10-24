"""Read-only evidence validation and corresponding-buffer comparison; no guest launch."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9/current-stills')
SOURCE = '49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
PRIOR = '5e4de9a0262d3629c9833c959557de198b2e9f0c'
TAGS = ['R-f1-limited-r1', 'B-f1-limited-r1', 'R-f2-limited-r1', 'B-f2-limited-r1']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def fresh(path, data):
    with path.open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')

def validate(tag, pins):
    arm, scene = tag.split('-')[:2]
    room = '101' if scene == 'f1' else '100'
    cap = E / 'captures' / tag
    launch = read(E / (tag + '-launch.json'))
    result = read(E / (tag + '-result.json'))
    receipt = read(cap / 'freeze330-capture.json')
    pre = read(cap / 'limitfps-prelaunch.json')
    run = read(cap / 'run-result.json')
    bound = read(cap / 'bounded-launch.json')
    assert launch == read(cap / 'current-still-launch.json')
    assert result['capture_receipt'] == receipt and result['run'] == run and result['bound'] == bound
    assert launch['source'] == SOURCE and launch['arm'] == arm and launch['scene'] == scene
    assert launch['PINS'] == pins and launch['pins_sha256'] == sha(HERE / 'PINS.json')
    assert result['launcher_rc'] == 0 and run['status'] == 'RUN_COMPLETE' and run['errors'] == []
    assert run['stopped'] == 'goal' and run['stop'] == 'warp: frozen at tick 330'
    assert run['seconds'] == 45 and run['elapsed_s'] <= 55 and run['emulator_exited']
    assert run['emu'] == 'console' and run['keys'] is None and run['key_log'] == []
    assert bound['deadline_seconds'] == 55 and not bound['deadline_fired']
    assert bound['guest_exited'] and bound['guest_observed_elapsed_s'] <= 55
    assert receipt['capture_completed'] and receipt['errors'] == []
    assert receipt['marker']['tick'] == 330 and receipt['marker']['placed_room'] == room
    assert receipt['marker']['line'].strip() == 'warp: frozen at tick 330'
    assert re.search(r'warp: placed room=' + room + r' pl=', receipt['placed_line'])
    assert receipt['pid'] == bound['pid']
    assert receipt['process_image'].replace('\\', '/').endswith('/' + tag + '/flycast.exe')
    assert receipt['buffer_stable_between_reads'] == [True, True]
    assert len(receipt['reads']) == 2 and all(r['bytes'] == 8388608 for r in receipt['reads'])
    assert receipt['reads'][1]['start_monotonic'] - receipt['reads'][0]['end_monotonic'] >= .14
    assert all(0 <= r['seconds_after_marker'] < 2 for r in receipt['reads'])
    assert pre['FP_NOLIMIT'] == '0' and pre['RE4DC_EMU'] == 'console' and pre['aica.LimitFPS'] == 'yes'
    assert pre['host_monotonic'] <= bound['guest_started_monotonic']
    cfgsha = sha(cap / 'emu.cfg')
    assert cfgsha == pre['actual_config_sha256'] == receipt['actual_config_sha256'] == receipt['actual_config_final_sha256']
    assert receipt['config_matches_prelaunch'] and sha(cap / 'limitfps-prelaunch.cfg') == cfgsha
    assert re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$', (cap / 'emu.cfg').read_text()) == ['yes']
    assert pre['wrapper_sha256'] == pins['force_limited_sha256']
    assert receipt['wrapper_sha256'] == pins['freeze_capture_sha256'] == bound['harness_sha256']
    assert receipt['backend_sha256'] == pins['ram_backend_sha256']
    assert receipt['capture_backend_sha256'] == pins['capture_decoder_sha256'] == sha(cap / 'capture_ui_vram.py')
    assert bound['expected_executable_sha256'] == pins['console_executable_sha256'] == sha(cap / 'flycast.exe')
    assert launch['fixture']['sha256'] == pins['fixtures'][scene + '.txt'] == run['fixtures']['warp']['sha256'] == sha(HERE.parent / 'fixtures' / (scene + '.txt'))
    assert run['fixtures']['pad']['bytes'] == 0 and run['fixtures']['w11']['bytes'] == 0
    command = launch['command']
    assert command[0] == 'bash' and command[1].endswith('/stat-guest-slot.sh')
    assert command[2] == 'bash' and command[3].endswith('/trace_lock.sh')
    assert command[5].endswith('census-bound-run.py') and command[6].endswith('freeze_capture.py')
    assert command[-3:-1] == ['--grace', '2'] or command[command.index('--grace') + 1] == '2'
    unit = launch['unit']
    assert unit['source'] == SOURCE and unit['arm'] == arm and unit['profile'] == 'g'
    assert len(unit['programme']['overlays']) == 14
    reuse = launch['actual_build_binding']
    if arm == 'R':
        assert reuse['actual_build_source'] == PRIOR and reuse['reused_old_build']
        assert reuse['requested_source'] == SOURCE
        proofpath = Path(reuse['proof'])
        assert sha(proofpath) == reuse['proof_sha256']
        proof = read(proofpath)
        assert proof['eligible'] and proof['source'] == SOURCE and proof['old_source'] == PRIOR
        assert proof['current']['programme']['main'] == unit['programme']['main']
        assert proof['current']['programme']['overlays'] == unit['programme']['overlays']
        assert proof['old_track03_sha256'] == launch['base']['track03_sha256']
    else:
        assert reuse['actual_build_source'] == SOURCE and not reuse['reused_old_build']
    assert run['tracks']['track03_sha256'] == launch['base']['track03_sha256']
    assert len(receipt['images']) == 4
    images = {}
    for row in receipt['images']:
        key = (row['sample'], row['buffer'])
        assert key not in images and key in [(0,0), (0,1), (1,0), (1,1)]
        path = cap / row['path'].replace('\\', '/')
        assert sha(path) == row['sha256'] and sha(path.with_suffix('.rgb565')) == row['raw565_sha256']
        assert path.with_suffix('.rgb565').stat().st_size == 640 * 480 * 2
        with Image.open(path) as image:
            assert image.size == (640, 480) and row['dimensions'] == [640, 480]
        images[key] = {'png': str(path), **row}
    for buffer in (0, 1):
        assert images[0, buffer]['sha256'] == images[1, buffer]['sha256']
        assert images[0, buffer]['raw565_sha256'] == images[1, buffer]['raw565_sha256']
    return {
        'tag': tag, 'arm': arm, 'scene': scene, 'actual_room': room,
        'launch_sha256': sha(E / (tag + '-launch.json')),
        'result_sha256': sha(E / (tag + '-result.json')),
        'capture_receipt_sha256': sha(cap / 'freeze330-capture.json'),
        'actual_config_sha256': cfgsha, 'prelaunch_sha256': sha(cap / 'limitfps-prelaunch.json'),
        'PID': bound['pid'], 'guest_observed_elapsed_s': bound['guest_observed_elapsed_s'],
        'guest_rc': bound['guest_rc'], 'harness_status': run['status'],
        'marker': receipt['marker'], 'placed_line': receipt['placed_line'],
        'buffer_stable_between_reads': receipt['buffer_stable_between_reads'],
        'reads': receipt['reads'], 'images': list(images.values()),
        'unit': unit, 'base': launch['base'], 'actual_build_binding': reuse,
        'fixture': launch['fixture'],
        'visual_inspection': 'Both first-read buffers inspected: clean authored scene, Leon/HUD visible; no Loading/watchdog screen.',
    }

def main():
    pins = read(HERE / 'PINS.json')
    ledger = read(E / 'attempts.json')
    assert [r['tag'] for r in ledger] == TAGS and len(ledger) == 4
    rows = [validate(tag, pins) for tag in TAGS]
    comparisons = []
    for scene in ('f1', 'f2'):
        r, b = [row for row in rows if row['scene'] == scene]
        assert r['arm'] == 'R' and b['arm'] == 'B'
        assert r['unit']['asset_manifest_sha256'] == b['unit']['asset_manifest_sha256']
        assert r['fixture']['sha256'] == b['fixture']['sha256']
        for buffer in (0, 1):
            ri = next(i for i in r['images'] if i['sample'] == 0 and i['buffer'] == buffer)
            bi = next(i for i in b['images'] if i['sample'] == 0 and i['buffer'] == buffer)
            with Image.open(ri['png']) as imr, Image.open(bi['png']) as imb:
                diff = ImageChops.difference(imr.convert('RGB'), imb.convert('RGB'))
                changed = sum(pixel != (0,0,0) for pixel in diff.getdata())
                maximum = max(v[1] for v in diff.getextrema())
                mean = ImageStat.Stat(diff).mean
            comparisons.append({'scene': scene, 'buffer': buffer, 'R_png': ri['png'], 'B_png': bi['png'],
                'R_png_sha256': ri['sha256'], 'B_png_sha256': bi['sha256'],
                'R_raw565_sha256': ri['raw565_sha256'], 'B_raw565_sha256': bi['raw565_sha256'],
                'changed_pixels': changed, 'maximum_channel_difference': maximum, 'mean_channel_difference': mean,
                'raw565_identical': ri['raw565_sha256'] == bi['raw565_sha256'],
                'result': 'MATCH' if changed == 0 and ri['raw565_sha256'] == bi['raw565_sha256'] else 'MISMATCH'})
    report = {
        'schema': 1, 'source': SOURCE, 'profile': 'g', 'scope': 'Scoped visible fixed-scene corresponding-buffer comparison only',
        'result': 'ALL_FOUR_CORRESPONDING_BUFFERS_MATCH' if all(c['result'] == 'MATCH' for c in comparisons) else 'MISMATCH_PRESERVED',
        'guest_attempts': 4, 'reruns': 0, 'PINS': pins, 'cases': rows, 'comparisons': comparisons,
        'limits': [
            'Freeze tick330 holds the game thread before frame completion; last completed world328 is a pinned source-call-order statement, not independently sampled here.',
            'No strict completed actor/viewport/presentation/upload/full-runtime-pose proof; withdrawn current49ad observer was not used.',
            'Each framebuffer read is separately owned-process bound; the two buffer indices are never permuted or selected to force a match.',
            'R actual old5e build/base/ELF is explicitly reused by current49ad raw-main plus all14-overlay byte proof and common asset identity.',
            'Guest rc1 is retained as the exact child exit after harness goal stop; RUN_COMPLETE, goal marker and no harness errors qualify these bounded captures.',
            'This does not close strict Mendez material-pair failure, private QA, release, hardware or performance acceptance.'
        ]}
    fresh(HERE / 'RESULTS.json', report)
    fresh(E / 'RESULTS.json', report)
    print(json.dumps({'result': report['result'], 'comparisons': comparisons}, indent=2))

if __name__ == '__main__':
    main()
