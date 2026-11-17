#!/usr/bin/env python3
"""pcs_from_log.py: PCS SNAP parts from the QA link -> read_pcs.py dumps (lane perf30, 2026-11-10).

The console answers `PCS SNAP` with P datagrams ("P <id> <part>/<parts>" then one hex line: header[32 words] + ring).
They land in the Pi log (qalink_pi.py: "<utc> P <text line>") and in `qalink.py send PCS SNAP` output. This tool
reassembles every complete snapshot it finds and writes, per snapshot, <out>-<id>.pcs in read_pcs.py's format
(the 128-byte header, then the records the ring still held, oldest first) plus a .json side file, so the existing
Flycast symbolizing steps work on console samples unchanged.

  python pcs_from_log.py <log or send output> <out prefix>
"""
import json, re, struct, sys

MAGIC = 0x31534350
HEADER_WORDS = 32
H = dict(MAGIC=0, VERSION=1, HEADER_WORDS=2, CAPACITY=3, HZ=4, PERIOD_TICKS=5, JITTER_MASK=6, STATE=7, HEAD=8,
         SAMPLES=9, MARKERS=10, LAT_SUM_LO=11, LAT_SUM_HI=12, LAT_MAX=13, LATE=14, LATE_TICKS=15, LAST_FRAME=16,
         STAGE_SOURCE=17, START_SECS=18, START_TICKS=19)
HEAD_RE = re.compile(r'^P (\S+) (\d+)/(\d+)$')
PFX_RE = re.compile(r'^\S+ P (.*)$')   # Pi log: "<utc stamp> P <line>"


def lines_of(path):
    for raw in open(path, encoding='latin-1'):
        line = raw.rstrip('\r\n')
        m = PFX_RE.match(line)
        if m and (HEAD_RE.match(m.group(1)) or re.fullmatch(r'[0-9a-f]+', m.group(1))):
            line = m.group(1)
        yield line


def main():
    src, out = sys.argv[1], sys.argv[2]
    snaps = {}   # id -> {part: bytes}, parts
    cur = None
    for line in lines_of(src):
        m = HEAD_RE.match(line)
        if m:
            cur = (m.group(1), int(m.group(2)), int(m.group(3)))
            continue
        if cur and re.fullmatch(r'[0-9a-f]*', line):
            sid, part, parts = cur
            d = snaps.setdefault(sid, {'parts': parts, 'data': {}})
            d['data'][part] = bytes.fromhex(line)
        cur = None
    done = 0
    for sid, d in snaps.items():
        missing = [p for p in range(1, d['parts'] + 1) if p not in d['data']]
        if missing:
            print('%s: incomplete, missing parts %s' % (sid, missing[:10]))
            continue
        blob = b''.join(d['data'][p] for p in range(1, d['parts'] + 1))
        hdr = struct.unpack_from('<%dI' % HEADER_WORDS, blob, 0)
        if hdr[H['MAGIC']] != MAGIC:
            print('%s: bad magic %08x' % (sid, hdr[H['MAGIC']]))
            continue
        cap, head = hdr[H['CAPACITY']], hdr[H['HEAD']]
        ring = blob[HEADER_WORDS * 4:HEADER_WORDS * 4 + cap * 8]
        first = head - min(head, cap)   # the guest was stopped: every slot from first to head is intact
        recs = bytearray()
        markers = 0
        for seq in range(first, head):
            i = (seq % cap) * 8
            recs += ring[i:i + 8]
            if struct.unpack_from('<I', ring, i + 4)[0] & 0x80000000:
                markers += 1
        path = '%s-%s.pcs' % (out, sid)
        with open(path, 'wb') as f:
            f.write(blob[:HEADER_WORDS * 4])
            f.write(recs)
        side = {'source': 'qalink PCS SNAP', 'id': sid, 'records_written': head - first, 'records_lost': 0,
                'markers_seen': markers, 'first_header': {k: hdr[v] for k, v in H.items()},
                'final_header': {k: hdr[v] for k, v in H.items()}}
        with open(path + '.json', 'w', encoding='utf-8') as f:
            json.dump(side, f, indent=2)
        print('%s: %d records (%d markers) hz=%d -> %s' % (sid, head - first, markers, hdr[H['HZ']], path))
        done += 1
    return 0 if done else 1


if __name__ == '__main__':
    sys.exit(main())
