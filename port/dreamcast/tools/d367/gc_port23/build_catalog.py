#!/usr/bin/env python3
"""Diagnostic GC-ASSET disc catalog builder (gc-catalog24b).

Walks an extracted release disc (fullplay/fp_iso.py extract) and emits one
catalog row per immutable payload the current gate binds, using the exact
kind/id/full-SHA256 rules of the runtime callers:

  texture      tex.pak members and loose dc/tex*/**/<crc>-<fnv>.re4tex files;
               id "<crc>-<fnv>", digest of the whole member/file
               (native_ui.cpp gcasset_texture_fingerprint)
  movie        dc/movie/rRRRsEE[c].seq; id "%05x" of the movie id, whole file
               (native_movie.cpp path_for / bind_checked("movie"))
  sound-stream one row per bgm/aica_str.dat AIS1 entry: SHA256 of its 32-byte
               record + intro groups + loop groups; id = first 20 digest bytes
               as hex (audio_aica.cpp gcasset_stream_entry)
  model        BIN members (direct or inside an ETM) of every file that parses
               as the runtime's archive table, recursively into members that
               parse as archives; id = first 20 digest bytes as hex
               (gc_asset_members.cpp entry/named/member_capture)
               .drs files are walked from their body at 0x400 (drs.py layout)
  geometry     every dc/native/** file, whole file; id = first 20 digest
               bytes as hex (gc_asset_payloads.cpp capture)

Not derivable from the disc (runtime-built bytes): font-glyph/font-palette
cells, sound-mram/sound-aram bank parts (no current bank_begin caller), layout
sidecars. Those binds stay explicit unknown quarantine at runtime.

Provenance is 'unknown' for every row unless --proofs supplies an exact
(kind,id,sha256) row with provenance and evidence. This is a DIAGNOSTIC catalog:
it formats reviewed input; it never proves origin and is never a gate pass.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_index  # noqa: E402

TEX = re.compile(r'^([0-9a-f]{8})-([0-9a-f]{8})\.re4tex$')
MOVIE = re.compile(r'^r([0-9a-f]{3})s([0-9a-f]{2})(c?)\.seq$')
DRS_TABLE = 0x400
VALID_NAME = re.compile(r'^[A-Za-z0-9._-]{1,31}$')
HARVEST_KINDS = ('font-glyph', 'font-palette', 'sound-mram', 'sound-aram', 'layout')
HARVEST_LINE = re.compile(r'GC-ASSET-HARVEST v=1 kind=([a-z0-9-]+) id=([0-9a-z._:/-]+) sha256=([0-9a-f]{64})')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(b, o):
    return struct.unpack_from('<I', b, o)[0]


def archive_spans(b):
    """Port of gc_asset_members.cpp table/entry: yield (index, tag, start, end)."""
    if len(b) < 16:
        return []
    count = word(b, 0)
    if count == 0 or count > 4096 or 16 + count * 8 > len(b):
        return []
    tags, directory = 16 + count * 4, 16 + count * 8
    out = []
    for index in range(count):
        at = word(b, 16 + index * 4)
        if at < directory or at >= len(b):
            continue
        empty_first = index
        while empty_first and word(b, 16 + (empty_first - 1) * 4) == at and not word(b, tags + (empty_first - 1) * 4):
            empty_first -= 1
        end, rel = len(b), word(b, 4)
        if at < rel < end:
            end = rel
        bad = False
        for i in range(count):
            if i == index:
                continue
            off = word(b, 16 + i * 4)
            if off == at and (i < empty_first or i >= index):
                bad = True
                break
            if at < off < end:
                end = off
        if not bad:
            out.append((index, bytes(b[tags + 4 * index:tags + 4 * index + 4]), at, end))
    return out


def etm_members(b):
    """Port of gc_asset_members.cpp named(): every .bin member payload of an ETM."""
    if len(b) < 32:
        return []
    count = word(b, 0)
    if count > 4096:
        return []
    cursor, seen, out = 32, set(), []
    for _ in range(count):
        if cursor > len(b) or len(b) - cursor < 64:
            return []
        size = word(b, cursor)
        raw = b[cursor + 32:cursor + 64]
        name = raw.split(b'\0', 1)[0].decode('latin-1')
        if size < 64 or size > len(b) - cursor or not VALID_NAME.match(name) or name.lower() in seen:
            return []
        seen.add(name.lower())
        if name.lower().endswith('.bin') and len(name) > 4:
            out.append(b[cursor + 64:cursor + size])
        cursor += size
    return out


def model_payloads(b, depth=0):
    for _index, tag, start, end in archive_spans(b):
        span = b[start:end]
        if tag[:3] == b'BIN':
            if len(span) >= 64:
                yield span
        elif tag[:3] == b'ETM':
            for member in etm_members(span):
                if len(member) >= 64:
                    yield member
        elif depth < 3:
            yield from model_payloads(span, depth + 1)


def stream_entries(b):
    """AIS1 entries as audio_aica.cpp hashes them: record, then the groups str_fill reads."""
    if len(b) < 16 or word(b, 0) != 0x31534941:
        raise ValueError('aica_str.dat header')
    for k in range(word(b, 4)):
        rec = b[16 + 32 * k:48 + 32 * k]
        _sbb, _rate, _flags, nch, a_samples, b_samples, a_ofs, b_ofs = struct.unpack('<8I', rec)
        grp = nch * 2048
        data = rec + b[a_ofs:a_ofs + (a_samples // 2 + 2047) // 2048 * grp]
        if b_samples:
            data += b[b_ofs:b_ofs + (b_samples // 2 + 2047) // 2048 * grp]
        yield k, data


def texpak_members(b):
    if len(b) < 24 or b[:8] != b'RE4PAK1\0':
        raise ValueError('tex.pak header')
    version, count, index, _data = struct.unpack_from('<4I', b, 8)
    if version != 1:
        raise ValueError('tex.pak version')
    for i in range(count):
        crc, fnv, off, size = struct.unpack_from('<4I', b, index + 16 * i)
        yield '%08x-%08x' % (crc, fnv), b[off:off + size], off, size


def collect(disc):
    rows = {}

    def add(kind, ident, data, source):
        digest = sha(data)
        key = (kind, ident, digest)
        if key not in rows:
            rows[key] = dict(kind=kind, id=ident, sha256=digest, source=source)

    files = sorted(p for p in disc.rglob('*') if p.is_file())
    for p in files:
        rel = p.relative_to(disc).as_posix()
        low = rel.lower()
        name = p.name.lower()
        if low == 'dc/tex.pak':
            b = p.read_bytes()
            for ident, data, off, size in texpak_members(b):
                add('texture', ident, data, '%s#offset=%d&bytes=%d' % (rel, off, size))
            continue
        m = TEX.match(name)
        if m and low.startswith(('dc/tex', 'texlow', 'dc/texlow')):
            add('texture', '%s-%s' % m.groups(), p.read_bytes(), rel)
            continue
        m = MOVIE.match(name)
        if m and low.startswith('dc/movie/'):
            mid = (int(m.group(1), 16) << 8) | int(m.group(2), 16) | (0x1000000 if m.group(3) else 0)
            add('movie', '%05x' % mid, p.read_bytes(), rel)
            continue
        if low == 'bgm/aica_str.dat':
            for k, data in stream_entries(p.read_bytes()):
                add('sound-stream', sha(data)[:40], data, '%s#entry=%d' % (rel, k))
            continue
        if low.startswith('dc/native/'):
            # Whole-file geometry: every dc/native payload a capture hashes as
            # loaded (registry/partner .re4nmr, pl08 .re4cp, hands .re4hp,
            # cells, low/index.txt, trclass.idx); harvest r100/r101/r11f/h2.
            b = p.read_bytes()
            add('geometry', sha(b)[:40], b, rel)
            if name == 'registry.re4nmr' or 'pl08' in low:
                continue
        if p.stat().st_size >= 16:
            b = p.read_bytes()
            for payload in model_payloads(b):
                add('model', sha(payload)[:40], payload, rel)
            # em/*.drs: the runtime adopts the body after the 0x400-byte record
            # table (drs.py), not the file start (em12/wepNN harvest misses).
            if name.endswith('.drs') and len(b) > DRS_TABLE:
                for payload in model_payloads(b[DRS_TABLE:]):
                    add('model', sha(payload)[:40], payload, rel + '#body')
    return rows


def extract_harvest(logs, out):
    """GC_ASSET_HARVEST=1 run logs -> harvest TSV (kind, id, sha256, evidence), sorted, deduplicated.

    Only runtime-built kinds (HARVEST_KINDS) are kept; other misses are disc-rule
    gaps and are printed, never added. Review the TSV, then pin it with --harvest."""
    rows, other = {}, {}
    for log in logs:
        label = Path(log).parent.name + '/' + Path(log).name
        for line in Path(log).read_text(errors='replace').splitlines():
            m = HARVEST_LINE.search(line)
            if not m:
                continue
            key = m.groups()
            (rows if key[0] in HARVEST_KINDS else other).setdefault(key, label)
    if Path(out).exists():
        sys.exit('harvest output exists')
    with open(out, 'w') as f:
        for key in sorted(rows):
            f.write('%s\t%s\t%s\tharvest-log=%s\n' % (key + (rows[key],)))
    for key in sorted(other):
        print('not-harvested %s %s %s (%s)' % (key + (other[key],)))
    print('harvest rows %d, other misses %d' % (len(rows), len(other)))


def read_harvest(raw):
    out = {}
    for n, line in enumerate(raw.decode('ascii').splitlines(), 1):
        kind, ident, digest, evidence = line.split('\t')
        if kind not in HARVEST_KINDS or not re.fullmatch(r'[0-9a-f]{64}', digest) or not evidence.strip():
            sys.exit('invalid harvest row %d' % n)
        if ident != digest[:40]:
            sys.exit('harvest id is not the digest prefix, row %d' % n)
        out[(kind, ident, digest)] = evidence
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--disc-dir', required=True, type=Path, help='fp_iso.py extract output')
    ap.add_argument('--manifest', required=True, type=Path, help='fp_iso.py extract --manifest output')
    ap.add_argument('--manifest-sha256', required=True)
    ap.add_argument('--proofs', type=Path, help='{"schema":1,"entries":[{kind,id,sha256,provenance,evidence}]}')
    ap.add_argument('--proofs-sha256')
    ap.add_argument('--harvest', type=Path, help='reviewed harvest TSV (extract-harvest output)')
    ap.add_argument('--harvest-sha256')
    ap.add_argument('--out-dir', required=True, type=Path)
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == 'extract-harvest':
        if len(argv) < 3:
            sys.exit('usage: build_catalog.py extract-harvest OUT.tsv LOG...')
        return extract_harvest(argv[2:], argv[1])
    a = ap.parse_args(argv)
    raw = a.manifest.read_bytes()
    if sha(raw) != a.manifest_sha256:
        sys.exit('manifest pin mismatch')
    manifest = json.loads(raw)
    disc = a.disc_dir.resolve(strict=True)
    on_disc = {p.relative_to(disc).as_posix(): p for p in disc.rglob('*') if p.is_file()}
    if set(on_disc) != set(manifest):
        sys.exit('extracted tree does not match manifest file set')
    for rel, rec in manifest.items():
        if on_disc[rel].stat().st_size != rec['size']:
            sys.exit('size mismatch %s' % rel)
    proofs, proofs_sha = {}, None
    if a.proofs:
        praw = a.proofs.read_bytes()
        proofs_sha = sha(praw)
        if proofs_sha != a.proofs_sha256:
            sys.exit('proofs pin mismatch')
        for r in json.loads(praw)['entries']:
            if r['provenance'] not in ('ps2', 'authored', 'gc') or not r['evidence'].strip():
                sys.exit('invalid proof row')
            proofs[(r['kind'], r['id'], r['sha256'])] = r
    rows = collect(disc)
    harvest_sha = None
    if a.harvest:
        hraw = a.harvest.read_bytes()
        harvest_sha = sha(hraw)
        if harvest_sha != a.harvest_sha256:
            sys.exit('harvest pin mismatch')
        for (kind, ident, digest), evidence in read_harvest(hraw).items():
            rows.setdefault((kind, ident, digest), dict(kind=kind, id=ident, sha256=digest,
                            source='runtime-harvest:' + evidence))
    if not set(proofs) <= set(rows):
        sys.exit('proof row matches no disc payload')
    out = []
    for key in sorted(rows):
        r = rows[key]
        p = proofs.get(key)
        ev = 'diagnostic-catalog; manifest_sha256=%s; source=%s' % (a.manifest_sha256, r['source'])
        if p:
            ev += '; proofs_sha256=%s; proof=%s' % (proofs_sha, p['evidence'])
        out.append(dict(kind=r['kind'], id=r['id'], sha256=r['sha256'],
                        provenance=p['provenance'] if p else 'unknown', evidence=ev, source=r['source']))
    blob, pin = catalog_index.build(out)
    a.out_dir.mkdir(parents=True, exist_ok=False)
    (a.out_dir / 'gc-assets.idx').write_bytes(blob)
    counts = {}
    for r in out:
        c = counts.setdefault(r['kind'], {})
        c[r['provenance']] = c.get(r['provenance'], 0) + 1
    report = dict(schema=1, label='DIAGNOSTIC catalog: not a gate pass, origin unproven unless proofs',
                  manifest_sha256=a.manifest_sha256, proofs_sha256=proofs_sha, harvest_sha256=harvest_sha, rows=len(out), counts=counts,
                  pin=pin.hex(), runtime_harvest_kinds=list(HARVEST_KINDS))
    (a.out_dir / 'catalog.json').write_text(json.dumps(dict(schema=1, entries=out), indent=1, sort_keys=True) + '\n')
    (a.out_dir / 'catalog-report.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(counts, sort_keys=True))
    print('rows %d' % len(out))
    print(pin.hex())


if __name__ == '__main__':
    main()
