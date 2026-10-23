from pathlib import Path
import hashlib, json, re
ROOT = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023')
SOURCE = '5be38f009f9ae4d42daff69dacc537e8230bcfca'
def pin(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': h.hexdigest()}
rows = {}
for arm in ('off','on'):
    cap = ROOT / ('full-h2-standard-repair5be-' + arm + '-console-r1')
    run = json.loads((cap / 'run-result.json').read_text())
    assert run['status'] == 'RUN_COMPLETE' and run['stopped'] == 'goal'
    assert run['emu'] == 'console' and run['seconds'] == 60 and not run['errors']
    text = (cap / 'run-output.txt').read_text(errors='replace')
    movies = {}
    for movie, frames in (('10003',1465), ('10020',571), ('10030',340)):
        m = re.search(r'route movie terminal=1 id='+movie+r' frames=(\d+)/(\d+) uploaded=(\d+) presented=(\d+)[^\r\n]*?heap_before=(\d+)', text)
        assert m and all(int(m[i]) == frames for i in range(1,5)), (arm,movie)
        movies[movie] = {'frames': frames, 'heap_before': int(m[5])}
    assert re.search(r'MOVIEARENA return[^\r\n]*restored=1', text)
    if arm == 'on':
        assert text.count('SCNDEDUP3 room=100') >= 2
    arena = re.search(r'arena fit (\d+) bytes \((\d+) left to KOS\)', text)
    assert arena
    out = Path('/root/probe/lanes/route/out-fpdd23std'+arm+'5be3gW')
    assert (out / 'stack.txt').read_text().strip() == SOURCE
    rows[arm] = {'source': SOURCE, 'run': pin(cap / 'run-result.json'), 'log': pin(cap / 'run-output.txt'), 'elf': pin(out / 're4dc-game.elf'), 'knobs': pin(out / 'resolved-knobs.txt'), 'track03_sha256': run['tracks']['track03_sha256'], 'movies': movies, 'arena_bytes': int(arena[1]), 'kos_left': int(arena[2]), 'room_at_init': int(arena[1])+int(arena[2]), 'restored': True, 'elapsed_s': run['elapsed_s']}
loss = rows['off']['movies']['10030']['heap_before'] - rows['on']['movies']['10030']['heap_before']
assert loss == 4096
reserve = 196608 + 64
slack = rows['off']['room_at_init'] - reserve - rows['off']['arena_bytes']
assert slack == 568
result = {'source': SOURCE, 'arms': rows, 'verdict': 'FAIL_NO_LOSS_REQUIREMENT', 'heap_loss_bytes': loss, 'off_arena_fit_slack': slack, 'on_added_init_room_bytes': rows['off']['room_at_init'] - rows['on']['room_at_init'], 'minimum_additional_code_saving_before_alignment': rows['off']['arena_bytes'] + reserve - rows['on']['room_at_init'], 'correction': 'Absolute _end page alignment was insufficient. ARENA_FIT rounds the remaining room minus its fixed reserve to 4096 bytes. The reviewed 562-byte unit saving does not restore the required heap floor.', 'next': 'Audit exact offline strip-block sharing or further safe code reduction; preserve both failures and keep QA packaging blocked.', 'limits': 'Console-mode Flycast correctness and measured heap evidence, not hardware performance or a full release pass.'}
dest = ROOT / 'standard-repair5be-matched-h2-fail.json'
assert not dest.exists()
dest.write_text(json.dumps(result, indent=2)+'\n')
print(result['verdict'], 'OFF',rows['off']['movies']['10030']['heap_before'],'ON',rows['on']['movies']['10030']['heap_before'],'additional_code_saving',result['minimum_additional_code_saving_before_alignment'])