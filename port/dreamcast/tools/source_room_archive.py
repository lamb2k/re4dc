"""Explicit original room inputs for the existing cast exporter/registry.

Uses room_smd's existing tagged-archive reader. No new binary format, enemy
identity alias, runtime admission or model transformation is introduced.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import re
import struct

KIND = 'gc-room-tagged'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def room_name(room):
    if not isinstance(room, str) or not re.fullmatch(r'r[0-9a-f]{3}', room):
        raise ValueError('explicit canonical room name required')
    return room

def source_pins(pins):
    keys = {'ps2_sha256', 'gc_container_sha256', 'gc_archive_sha256'}
    if not isinstance(pins, dict) or set(pins) != keys or any(
            not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v) for v in pins.values()):
        raise ValueError('complete original PS2/container/decoded-room SHA256 pins required')
    return pins

class TaggedRoomArchive:
    """The source Archive entry API over an unchanged bare original GC room."""
    def __init__(self, path, room):
        import room_smd
        self.room = room_name(room)
        self.path = str(path)
        self.name = Path(path).name
        data = Path(path).read_bytes()
        if room_smd.archive_endian(data) != '>':
            raise ValueError('original GC room archive must be big endian')
        count = struct.unpack_from('>I', data)[0]
        header_end = 16 + 8 * count
        entries = room_smd.tagged_entries(data, '>')
        # Do not reinterpret a container, truncated table or overlapping header
        # as source models. Preserve duplicate/empty source entries by ordinal.
        if len(entries) != count or any(start < header_end or end < start or end > len(data)
                                        for _, start, end in entries):
            raise ValueError('room entry bounds escape the original tagged archive')
        self.drs = SimpleNamespace(entries=[(tag, data[start:end]) for tag, start, end in entries])

    def entry(self, index):
        if type(index) is not int or not 0 <= index < len(self.drs.entries):
            raise ValueError('room source entry ordinal out of bounds')
        from motion.archive import Entry
        tag, data = self.drs.entries[index]
        return Entry(self.name, index, tag.rstrip(b'\0').decode('ascii'), data)

    def entries(self, tag=None):
        for i in range(len(self.drs.entries)):
            entry = self.entry(i)
            if tag is None or entry.tag == tag:
                yield entry


def room_inputs(room, cache, ps2_iso, gc_iso, pins):
    """Read pinned original DAT/DAS, preserving compressed and decoded identities."""
    import ps2_bin
    import room_smd
    from assetpipe.rooms import GcIso
    room = room_name(room)
    source_pins(pins)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    p, g, a = cache / (room + '.dat'), cache / (room + '.das'), cache / (room + '.arc')
    source_file = 'St' + room[1] + '/' + room + '.das'
    if not p.exists():
        data = ps2_bin.afs_read(ps2_iso, room + '.dat')
        if digest(data) != pins['ps2_sha256']:
            raise ValueError('original PS2 room DAT pin differs')
        p.write_bytes(data)
    if not g.exists():
        data = GcIso(gc_iso).read(source_file)
        if digest(data) != pins['gc_container_sha256']:
            raise ValueError('original GC room DAS pin differs')
        g.write_bytes(data)
    pd, gd = p.read_bytes(), g.read_bytes()
    if digest(pd) != pins['ps2_sha256'] or digest(gd) != pins['gc_container_sha256']:
        raise ValueError('cached original room source changed')
    # The retained decoded source may be read on Windows, where the existing
    # PPC/qemu source decoder is unavailable. Its explicit original hash is
    # mandatory; registry generation independently replays DAS decoding in WSL.
    decoded = a.read_bytes() if a.exists() else room_smd.decode_das(gd)
    if digest(decoded) != pins['gc_archive_sha256']:
        raise ValueError('decoded original GC room pin differs')
    if not a.exists():
        a.write_bytes(decoded)
    gc = TaggedRoomArchive(a, room)
    ps2 = {i: (tag, data) for i, tag, data in ps2_bin.dat_entries(pd)}
    rec = dict(ps2=dict(iso=str(ps2_iso), afs_entry=room + '.dat', bytes=len(pd),
                       sha256=digest(pd), cache=str(p)),
               gc=dict(iso=str(gc_iso), file=source_file, bytes=len(decoded),
                       sha256=digest(decoded), cache=str(a), source_archive_kind=KIND,
                       source_room=room, container=dict(cache=str(g), bytes=len(gd),
                       sha256=digest(gd), decoding='room_smd.decode_das')))
    return ps2, gc.drs, rec


def room_origin(audit, source, archive_name):
    """Require the same explicit original-container identity on every descriptor."""
    room = room_name(audit.get('source_room'))
    if audit.get('source_archive_kind') != KIND or source.get('source_archive_kind') != KIND or \
            source.get('source_room') != room or archive_name != room or source.get('source_archive') != room:
        raise ValueError('explicit room source identity differs from archive audit')
    c = audit.get('source_container')
    if not isinstance(c, dict) or set(c) != {'cache', 'bytes', 'sha256', 'decoding'} or \
            source.get('source_container') != c or not isinstance(c['cache'], str) or not c['cache'] or \
            type(c['bytes']) is not int or c['bytes'] <= 0 or not isinstance(c['sha256'], str) or \
            not re.fullmatch(r'[0-9a-f]{64}', c['sha256']) or c['decoding'] != 'room_smd.decode_das':
        raise ValueError('original room container identity missing or inconsistent')
    return room, c


def prove_room_decoding(container_path, archive_path, container):
    import room_smd
    data = Path(container_path).read_bytes()
    if len(data) != container['bytes'] or digest(data) != container['sha256']:
        raise ValueError('original room container bytes differ')
    if room_smd.decode_das(data) != Path(archive_path).read_bytes():
        raise ValueError('tagged room is not the exact original DAS decoding')
