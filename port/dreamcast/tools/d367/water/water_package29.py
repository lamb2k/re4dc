#!/usr/bin/env python3
"""Add a versioned W29 member to an existing native room DAR.

The input is unchanged. Without --enable-water29 this command writes nothing.
The selected rows come from the generated source includes, whose comments
identify one PS2 EFF family per room. The runtime rechecks their key and
copies the bounded rows from the actual loaded member.
"""
import argparse
from pathlib import Path
import re
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS / 'd367' / 'graft'))
import dar_graft  # noqa: E402
from water_layer29_source import source_key, table  # noqa: E402

ROOT = HERE.parents[4]
MAIN = ROOT / 'src/game/water_ps2_table.inc'
EXT = ROOT / 'src/game/water_ps2_ext.inc'
MAGIC = 0x50393257  # W29P in the little-endian member
VERSION = 1
HEADER = struct.Struct('<14I')
MAIN_ROW = struct.Struct('<Hh10fI6B2x')
EXT_ROW = struct.Struct('<Hh15fI7Bx')
NUMBER = re.compile(r'(?<![A-Za-z0-9_])(?:-?0x[0-9a-fA-F]+|-?\d+(?:\.\d+)?f?)(?![A-Za-z0-9_])')


def rows(path, kind):
    result = []
    width = 19 if kind == 'main' else 25
    row_format = MAIN_ROW if kind == 'main' else EXT_ROW
    for line in path.read_text().splitlines():
        if not line.lstrip().startswith('{0x'):
            continue
        literals = NUMBER.findall(line.split('//', 1)[0])
        if len(literals) != width or '//' not in line:
            raise ValueError(f'{path}: malformed {kind} source row')
        values = [int(s, 0) if s.startswith('0x') or '.' not in s and not s.endswith('f')
                  else float(s.rstrip('f')) for s in literals]
        room, area = int(values[0]), int(values[1])
        floats = values[2:12] if kind == 'main' else values[2:17]
        argb = int(values[12] if kind == 'main' else values[17])
        tail = values[13:] if kind == 'main' else values[18:]
        if any(int(x) != x or x < 0 or x > 255 for x in tail):
            raise ValueError(f'{path}: out-of-range byte field')
        result.append((room, row_format.pack(room, area, *floats, argb, *map(int, tail))))
    return result


def member(room, main_path=MAIN, ext_path=EXT, no_water=False):
    main_spans = table(main_path, r'\.ps2\.eff[0-9]+')
    ext_spans = table(ext_path, r'\.dat eff[0-9]+')
    if set(main_spans) & set(ext_spans):
        raise ValueError('water source family overlaps main and extension')
    keys = [source_key(span[2]) for span in (*main_spans.values(), *ext_spans.values())]
    if len(set(keys)) != len(keys):
        raise ValueError('water source family key collision')
    if room in main_spans:
        first, count, family = main_spans[room]
        source_rows = rows(main_path, 'main')
        if len(source_rows) != sum(x[1] for x in main_spans.values()):
            raise ValueError('main source count mismatch')
        selected = source_rows[first:first + count]
        if len(selected) != count or any(r != room for r, _ in selected):
            raise ValueError('main source span mismatch')
        main_data = b''.join(data for _, data in selected)
        ext_data = b''
        ext_first = 0
    elif room in ext_spans:
        ext_first, count, family = ext_spans[room]
        source_rows = rows(ext_path, 'extension')
        if len(source_rows) != sum(x[1] for x in ext_spans.values()):
            raise ValueError('extension source count mismatch')
        selected = source_rows[ext_first:ext_first + count]
        if len(selected) != count or any(r != room for r, _ in selected):
            raise ValueError('extension source span mismatch')
        ext_data = b''.join(data for _, data in selected)
        main_data = b''
    else:
        raise ValueError(f'room {room:03x} has no checked source family')
    if no_water:
        main_data = ext_data = b''
        ext_first = 0
    main_count, ext_count = len(main_data) // MAIN_ROW.size, len(ext_data) // EXT_ROW.size
    if (not no_water and not (0 < main_count + ext_count <= 32)) or ext_first > 31 or ext_first + ext_count > 32:
        raise ValueError('water layer count exceeds bounded store')
    main_off = HEADER.size if main_count else 0
    ext_off = HEADER.size + len(main_data) if ext_count else 0
    payload = main_data + ext_data
    head = HEADER.pack(MAGIC, VERSION, HEADER.size + len(payload), room, source_key(family),
                       1 if no_water else 2,
                       main_count, main_off, len(main_data), ext_count, ext_off, len(ext_data),
                       ext_first if ext_count else 0, zlib.crc32(payload) & 0xffffffff)
    return head + payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-water29', action='store_true')
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--room', type=lambda s: int(s.removeprefix('r'), 16), required=True)
    ap.add_argument('--main', type=Path, default=MAIN)
    ap.add_argument('--ext', type=Path, default=EXT)
    ap.add_argument('--intentional-no-water', action='store_true',
                    help='publish an explicit NO_WATER member for the selected source family')
    args = ap.parse_args()
    if not args.enable_water29:
        return
    if args.input.resolve() == args.output.resolve() or (args.output.exists() and
                                                         args.input.samefile(args.output)):
        raise ValueError('W29 producer never overwrites its input')
    body = member(args.room, args.main, args.ext, args.intentional_no_water)
    output, _ = dar_graft.append_water_member(args.input.read_bytes(), body)
    args.output.write_bytes(output)


if __name__ == '__main__':
    main()
