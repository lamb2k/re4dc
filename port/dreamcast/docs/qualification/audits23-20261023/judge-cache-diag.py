#!/usr/bin/env python3
"""Strict observer-log judge. Validates recorded intervals; never closes capture tail."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

TICK_HZ = 12468720
U32 = 0xffffffff
HEAD = re.compile(r"cachep2diag room=([0-9a-fA-F]{4}) phase=(boot|live|transition) seq=(\d+) frame=(\d+) calls=(\d+) timed=(\d+) rejected=(\d+) unavailable=(\d+) overflow=([0-9a-fA-F]+) hook_reject=(\d+)\s*")
TIME = re.compile(r"cachep2diag time room=([0-9a-fA-F]{4}) seq=(\d+) ticks=([0-9a-fA-F]{8}):([0-9a-fA-F]{8}) max=(\d+) full512=(\d+) ram256=(\d+) capacity=([0-9a-fA-F]{8}):([0-9a-fA-F]{8})\s*")

class Invalid(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise Invalid(message)

def room_id(text):
    value = text.lower().removeprefix('r').removeprefix('0x')
    room = int(value, 16)
    if not 0 <= room < 0xffff:
        raise argparse.ArgumentTypeError('expected a known room, e.g. r117')
    return room

def metrics(rows):
    sums = {k: sum(x[k] for x in rows) for k in ['calls', 'timed', 'rejected', 'unavailable', 'ticks', 'capacity', 'full512', 'ram256']}
    sums['intervals'] = len(rows)
    sums['max_ticks'] = max((x['max_ticks'] for x in rows), default=0)
    sums['clock_coverage'] = sums['timed'] / sums['calls'] if sums['calls'] else None
    sums['timing_status'] = 'MODELLED_VALID_WINDOWS' if sums['timed'] else 'NODATA'
    sums['modelled_nominal_valid_window_us'] = sums['ticks'] * 1e6 / TICK_HZ if sums['timed'] else None
    sums['modelled_mean_valid_window_us'] = sums['ticks'] * 1e6 / (TICK_HZ * sums['timed']) if sums['timed'] else None
    sums['modelled_max_valid_window_us'] = sums['max_ticks'] * 1e6 / TICK_HZ if sums['timed'] else None
    return sums

def judge(text, expected_rooms=()):
    rows, pending, seen = [], None, set()
    for line_number, raw in enumerate(text.splitlines(), 1):
        if 'cachep2diag' not in raw:
            continue
        line = raw[raw.index('cachep2diag'):]
        h, t = HEAD.fullmatch(line), TIME.fullmatch(line)
        if h:
            require(pending is None, f'line {line_number}: missing time row before next primary row')
            room, phase, seq, frame, calls, timed, rejected, unavailable, overflow, bad_hook = h.groups()
            row = dict(room=int(room, 16), phase=phase, seq=int(seq), frame=int(frame), calls=int(calls), timed=int(timed), rejected=int(rejected), unavailable=int(unavailable), overflow=int(overflow, 16), hook_reject=int(bad_hook), line=line_number)
            require(all(0 <= v <= U32 for v in row.values() if isinstance(v, int)), f'line {line_number}: field outside u32')
            require(row['seq'] not in seen, f'line {line_number}: duplicate seq')
            require(row['seq'] == len(rows) + 1, f'line {line_number}: missing/out-of-order seq (capture must start at1)')
            require(row['overflow'] == row['hook_reject'] == 0, f'line {line_number}: overflow or unsafe/mislabeled hook')
            require(row['calls'] == row['timed'] + row['rejected'] + row['unavailable'], f'line {line_number}: C != T+R+U')
            if phase in ['boot', 'transition']:
                require(row['room'] == 0xffff and row['frame'] == 0, f'line {line_number}: unattributed phase must have roomffff/frame0')
            else:
                require(row['room'] != 0xffff, f'line {line_number}: live phase has unknown room')
                require(row['frame'] % 150 == 0, f'line {line_number}: live frame is not a150-frame checkpoint or0 boundary')
            require((phase == 'boot') == (row['seq'] == 1), f'line {line_number}: boot must be first and only first')
            if rows and rows[-1]['phase'] == 'live' and rows[-1]['frame']:
                require(phase == 'live' and row['room'] == rows[-1]['room'], f'line {line_number}: phase/room changed without recorded boundary')
            if phase == 'live' and row['frame']:
                prior = rows[-1] if rows else None
                # A zero-frame row is enter/leave boundary; its next room is not in this protocol.
                if prior and prior['phase'] == 'live' and prior['frame']:
                    require(prior['room'] == row['room'] and row['frame'] == prior['frame'] + 150, f'line {line_number}: missing boundary or frame checkpoint')
                else:
                    require(row['frame'] == 150, f'line {line_number}: first live checkpoint must be150')
            pending = row
        elif t:
            require(pending is not None, f'line {line_number}: time row has no primary row (duplicate or out of order)')
            room, seq, hi, lo, maximum, full, ram, cap_hi, cap_lo = t.groups()
            require(int(room, 16) == pending['room'] and int(seq) == pending['seq'], f'line {line_number}: paired room/seq mismatch')
            pending.update(ticks=(int(hi, 16) << 32) | int(lo, 16), max_ticks=int(maximum), full512=int(full), ram256=int(ram), capacity=(int(cap_hi, 16) << 32) | int(cap_lo, 16), time_line=line_number)
            require(all(pending[k] <= U32 for k in ['max_ticks', 'full512', 'ram256']), f'line {line_number}: time field outside u32')
            require(pending['calls'] == pending['full512'] + pending['ram256'], f'line {line_number}: C != full+ram')
            require(pending['capacity'] == pending['full512'] * 16384 + pending['ram256'] * 8192, f'line {line_number}: capacity mismatch')
            require(pending['max_ticks'] <= TICK_HZ, f'line {line_number}: valid sample exceeds qualified no-wrap window')
            require(pending['max_ticks'] <= pending['ticks'] <= pending['timed'] * pending['max_ticks'], f'line {line_number}: inconsistent max/total/timed')
            if not pending['timed']:
                require(pending['ticks'] == pending['max_ticks'] == 0, f'line {line_number}: Timed0 has timing data')
            seen.add(pending['seq']); rows.append(pending); pending = None
        else:
            raise Invalid(f'line {line_number}: malformed or unknown diagnostic row')
    require(pending is None, 'EOF: missing paired time row; interrupted row is invalid')
    require(rows, 'no diagnostic rows: NODATA, not zero calls')
    require(all(any(x['phase'] == 'live' and x['room'] == room for x in rows) for room in expected_rooms), 'required room has no recorded live interval: NODATA')
    live_rooms = sorted({x['room'] for x in rows if x['phase'] == 'live'})
    report = dict(status='VALID_RECORDED_INTERVALS', scope='Counts for complete paired recorded intervals only; capture tail remains unreported', totals=metrics(rows), rooms={f'{room:04x}': metrics([x for x in rows if x['phase'] == 'live' and x['room'] == room]) for room in live_rooms}, unattributed={phase: metrics([x for x in rows if x['phase'] == phase]) for phase in ['boot', 'transition']}, last_seq=rows[-1]['seq'], capture_ends_with_unreported_interval=True, interrupted_final_interval=dict(status='NODATA', after_seq=rows[-1]['seq'], counts=None, ticks=None, note='No terminal flush/seal exists. Tail duration and helper calls are unknown even after a complete final pair.'), nominal_tick_hz=TICK_HZ, nominal_tick_ns=1e9/TICK_HZ, limits=['MODELLED nominal conversions of valid timer windows; no hardware/guest CPU timing calibration', 'Observed masked subinterval, including observer work; excludes final aggregation/restore tail; not full IRQ-blocked duration', 'Uncalibrated observer overhead. Emitted valid-path model adds91/89 instructions for full/OC-RAM; instruction counts are not cycles', 'Rejected/unavailable calls retain counts/capacity but have no duration estimate. Timed0 means NODATA', 'Capacity is cache-entry capacity, not requested bytes or actual dirty bytes', 'Counts by room are partial observed intervals, not complete room totals, calls/second, or gameplay performance'], intervals=rows)
    return report

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('log', type=Path)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--room', type=room_id, action='append', default=[])
    a = ap.parse_args()
    raw = a.log.read_bytes()
    try:
        report = judge(raw.decode('utf-8', errors='strict'), a.room)
        code = 0
    except (Invalid, UnicodeError) as error:
        report, code = dict(status='INVALID_CAPTURE', reason=str(error), timing_status='NODATA'), 1
    report.update(input=str(a.log), input_sha256=hashlib.sha256(raw).hexdigest(), judge_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    result = json.dumps(report, indent=2) + '\n'
    if a.output:
        a.output.write_text(result)
    else:
        print(result, end='')
    return code

if __name__ == '__main__':
    sys.exit(main())
