"""Read-only FLYSAVE1/RZIP audit and exact-input checkpoint ancestry.

Never changes serialized state. Four immutable ELF .text anchors locate its
16 MiB RAM image; context offsets come from the matching DWARF receipt.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decode(path):
    blob = Path(path).read_bytes()
    if blob[:8] != b'FLYSAVE1':
        raise ValueError('unsupported checkpoint container')
    name_bytes = struct.unpack_from('<I', blob, 20)[0]
    at = 24 + name_bytes
    if blob[at:at+8] != b'#RZIPv\x01#':
        raise ValueError('unsupported checkpoint compression')
    chunk, total = struct.unpack_from('<IQ', blob, at+8)
    at += 20
    if not 0 < chunk <= 64 * 1024**2 or not 16 * 1024**2 <= total <= 256 * 1024**2:
        raise ValueError('checkpoint size outside expected bounds')
    out = bytearray()
    while len(out) < total:
        size = struct.unpack_from('<I', blob, at)[0]
        at += 4
        if not size:
            continue
        if at + size > len(blob):
            raise ValueError('truncated compressed checkpoint')
        part = zlib.decompress(blob[at:at+size])
        at += size
        if len(part) > chunk or len(out) + len(part) > total:
            raise ValueError('checkpoint chunk exceeds declared size')
        out.extend(part)
    if at != len(blob):
        raise ValueError('trailing checkpoint bytes')
    return bytes(out)


def text_section(elf):
    blob = Path(elf).read_bytes()
    if blob[:6] != b'\x7fELF\x01\x01':
        raise ValueError('expected ELF32 little endian')
    off = struct.unpack_from('<I', blob, 32)[0]
    step, count, names = struct.unpack_from('<HHH', blob, 46)
    headers = [struct.unpack_from('<10I', blob, off+i*step) for i in range(count)]
    table = headers[names]
    strings = blob[table[4]:table[4]+table[5]]
    matches = [h for h in headers if strings[h[0]:].split(b'\0', 1)[0] == b'.text']
    if len(matches) != 1:
        raise ValueError('ELF .text selection ambiguous')
    section = matches[0]
    return section[3], blob[section[4]:section[4]+section[5]]


def audit(state, elf, binding, layout):
    bound = json.loads(Path(binding).read_text(encoding='utf-8-sig'))
    shape = json.loads(Path(layout).read_text(encoding='utf-8-sig'))
    if sha(elf) != bound['elf_sha256'] or shape['elf_sha256'] != bound['elf_sha256']:
        raise ValueError('checkpoint ELF/DWARF binding changed')
    raw = decode(state)
    va, code = text_section(elf)
    offsets = (0x4000, 0x40000, 0x100000, 0x180000)
    if len(code) < offsets[-1] + 256:
        raise ValueError('ELF text too small for pinned anchor scheme')
    sig = code[offsets[0]:offsets[0]+256]
    bases = []
    pos = -1
    while True:
        pos = raw.find(sig, pos+1)
        if pos < 0:
            break
        base = pos - (va+offsets[0]-0x8c000000)
        if base < 0 or base+0x1000000 > len(raw):
            continue
        if all(raw[base+va+n-0x8c000000:base+va+n-0x8c000000+256] == code[n:n+256] for n in offsets):
            bases.append(base)
    if len(bases) != 1:
        raise ValueError(f'checkpoint does not uniquely match immutable ELF code: {bases}')
    base = bases[0]

    def read(addr, fmt):
        size = struct.calcsize('<'+fmt)
        if not 0x8c000000 <= addr <= 0x8d000000-size:
            raise ValueError('checkpoint sample outside main RAM')
        row = struct.unpack_from('<'+fmt, raw, base+addr-0x8c000000)
        return row[0] if len(row) == 1 else list(row)

    def field(addr, kind, name, fmt):
        matches = [m for m in shape['found'][kind]['members'] if m['name'].split('.')[-1] == name]
        if len(matches) != 1:
            raise ValueError('checkpoint DWARF field selection ambiguous')
        return read(addr+matches[0]['offset'], fmt)

    symbols = {k: int(v, 0) for k, v in bound['symbols'].items()}
    pg, pl = read(symbols['pG'], 'I'), read(symbols['pPL'], 'I')
    return dict(state_sha256=sha(state), state_bytes=Path(state).stat().st_size,
        elf_sha256=bound['elf_sha256'], decoded_bytes=len(raw), ram_serialization_offset=base,
        immutable_anchors=[dict(address=hex(va+n), bytes=256, sha256=hashlib.sha256(code[n:n+256]).hexdigest()) for n in offsets],
        log_head=read(symbols['head'], 'I'), room=field(pg, 'GlobalWork', 'room_id', 'H'),
        frame=field(pg, 'GlobalWork', 'Frame_cnt', 'I'), stop=field(pg, 'GlobalWork', 'Stop_flg', 'I'),
        player_life=field(pg, 'GlobalWork', 'pl_life', 'H'),
        player_life_max=field(pg, 'GlobalWork', 'pl_life_max', 'H'),
        player_pos=field(pl, 'cModel', 'pos', '3f'),
        player_rno=field(pl, 'cModel', 'r_no_0', '4B'),
        event_start_cnt=field(symbols['SceSys'], 'cSceSys', 'event_start_cnt', 'B'),
        qa_flags=read(symbols['qa_flags'], 'I'), memory_edits=False)


def files(folder):
    return {str(p.relative_to(folder)).replace('\\', '/'): dict(bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def seal(cap, elf, binding, layout, disc_identity, parent=None):
    cap = Path(cap)
    destination = cap/'checkpoint.json'
    if destination.exists():
        raise ValueError('checkpoint receipt already exists')
    state = cap/'data'/'disc.state'
    row = dict(format_version=1, scope='Unedited ordinary-controller route continuation; not a natural no-warp release route',
        input=disc_identity, emulator_sha256=sha(cap/'flycast.exe'), data=files(cap/'data'),
        audit=audit(state, elf, binding, layout),
        parent=dict(path=str(parent), receipt_sha256=sha(Path(parent)/'checkpoint.json')) if parent else None,
        inputs_sha256=sha(cap/'ownership-resource-guard.json'), state_edits=False)
    destination.write_text(json.dumps(row, indent=2)+'\n')
    return row


def verify(seed, elf, binding, layout, disc_identity, emulator):
    seed = Path(seed)
    row = json.loads((seed/'checkpoint.json').read_text())
    if row['input'] != disc_identity or row['emulator_sha256'] != sha(emulator):
        raise ValueError('checkpoint program/disc/emulator identity differs')
    if row['data'] != files(seed/'data'):
        raise ValueError('checkpoint data or serialized state changed')
    actual = audit(seed/'data'/'disc.state', elf, binding, layout)
    if actual != row['audit'] or actual['qa_flags']:
        raise ValueError('checkpoint audit changed or non-default QA flags')
    return row
