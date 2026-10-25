"""Bounded indexed-catalog prototype. This formats reviewed input, not origin proof."""
import hashlib
import struct

MAGIC = b'GCIDX001'
HEADER = struct.Struct('<8s4I104s')
RECORD = struct.Struct('<16s48s32sB15s')
MAX_RECORDS = 16320  # 64 remaining compact-token indices are unknown quarantine
ORIGINS = {'unknown': 0, 'gc': 1, 'ps2': 2, 'authored': 3}


def sha(data):
    return hashlib.sha256(data).digest()


def text(value, limit):
    if not isinstance(value, str) or not value or len(value) >= limit:
        raise ValueError('invalid catalog identity')
    if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789/._:-' for c in value):
        raise ValueError('invalid catalog identity')
    return value.encode('ascii')


def encode(row):
    kind, identity = text(row['kind'], 16), text(row['id'], 48)
    digest = row['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid full payload SHA256')
    origin = ORIGINS[row['provenance']]
    # A nonempty evidence locator is required even for unknown. It does not
    # upgrade the origin or replace separate review of the pinned catalog.
    if not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
        raise ValueError('missing reviewed input evidence')
    return RECORD.pack(kind, identity, bytes.fromhex(digest), origin, bytes(15))


def decode(record):
    if len(record) != RECORD.size:
        raise ValueError('short catalog record')
    kind, identity, digest, origin, reserved = RECORD.unpack(record)
    if reserved != bytes(15) or origin not in ORIGINS.values():
        raise ValueError('invalid catalog record')
    def string(raw):
        at = raw.find(b'\0')
        if at < 0 or any(raw[at:]):
            raise ValueError('invalid catalog string padding')
        value = raw[:at].decode('ascii')
        text(value, len(raw))
        return value
    return string(kind), string(identity), digest, origin


def build(rows):
    records = sorted(encode(row) for row in rows)
    if not records or len(records) > MAX_RECORDS:
        raise ValueError('catalog capacity')
    if any(a[:96] == b[:96] for a, b in zip(records, records[1:])):
        raise ValueError('duplicate kind/id/full-digest identity')
    header = HEADER.pack(MAGIC, 1, len(records), RECORD.size, HEADER.size, bytes(104))
    data = header+b''.join(records)
    return data, sha(data)


class Reader:
    """Pinned read-only CD catalog model; source remains immutable until retire."""
    def __init__(self, read, size, expected_file_sha):
        self.read = read
        if size < HEADER.size or size > HEADER.size+MAX_RECORDS*RECORD.size:
            raise ValueError('invalid catalog bounds/schema')
        actual = hashlib.sha256()
        for offset in range(0, size, 512):
            count = min(512, size-offset);block=read(offset,count)
            if len(block) != count:raise ValueError('short catalog read')
            actual.update(block)
        if len(expected_file_sha) != 32 or actual.digest() != expected_file_sha:
            raise ValueError('catalog generation pin mismatch')
        header = read(0, HEADER.size)
        magic, version, count, record_bytes, offset, reserved = HEADER.unpack(header)
        if (magic != MAGIC or version != 1 or not 0 < count <= MAX_RECORDS or
            record_bytes != RECORD.size or offset != HEADER.size or reserved != bytes(104) or
            size != offset+count*record_bytes):
            raise ValueError('invalid catalog bounds/schema')
        self.count, self.offset = count, offset
        previous = None
        for index in range(count):
            current = self.record(index)[:3]
            if previous is not None and previous >= current:
                raise ValueError('unsorted or duplicate catalog identity')
            previous = current

    def record(self, index):
        if not 0 <= index < self.count:
            raise ValueError('catalog index out of range')
        record = self.read(self.offset+index*RECORD.size, RECORD.size)
        return decode(record)

    def lookup(self, kind, identity, actual_sha):
        key = (kind, identity, actual_sha)
        lower, upper = 0, self.count
        while lower < upper:
            middle = (lower+upper)//2
            row = self.record(middle)
            if row[:3] < key:
                lower = middle+1
            else:
                upper = middle
        if lower < self.count and self.record(lower)[:3] == key:
            return lower
        return None  # explicit unknown quarantine; never a provenance verdict


class Epochs:
    """Compact-token lifecycle model, including exhaustion and quarantine."""
    def __init__(self):
        self.epoch = 0
        self.reader = None
        self.unknown = []

    def install(self, reader):
        if self.epoch >= (1 << 18)-2:
            raise ValueError('catalog epoch exhausted')
        self.epoch += 1
        self.reader, self.unknown = reader, []

    def bind(self, kind, identity, actual_sha):
        if self.reader is None or len(actual_sha) != 32:
            raise ValueError('uninstalled catalog or invalid full payload digest')
        index = self.reader.lookup(kind, identity, actual_sha)
        if index is None:
            row = (kind, identity, actual_sha, ORIGINS['unknown'])
            if row not in self.unknown:
                if len(self.unknown) == 8:
                    raise ValueError('unknown quarantine overflow')
                self.unknown.append(row)
            index = self.reader.count + self.unknown.index(row)
        return self.epoch << 14 | index

    def resolve(self, token):
        index = token & ((1 << 14)-1)
        if not self.epoch or token >> 14 != self.epoch or self.reader is None:
            raise ValueError('stale catalog token')
        if index < self.reader.count:
            return self.reader.record(index)
        at = index-self.reader.count
        if at >= len(self.unknown):
            raise ValueError('invalid unknown token')
        return self.unknown[at]
