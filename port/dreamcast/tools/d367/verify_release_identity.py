#!/usr/bin/env python3
"""Bind a retained release ELF and optional pre-strip ELF to public disc bytes.

The disc selection directory contains 1ST_READ.BIN and dc/*.ovl. This checks
executable identity only; an overlay's runtime load address needs separate proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sections(tool, elf):
    result = subprocess.check_output([tool + 'objdump', '-h', str(elf)], text=True)
    return [line.split()[1] for line in result.splitlines()
            if len(line.split()) > 1 and line.split()[1].startswith('.ovl_')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--overlays', type=Path, required=True)
    parser.add_argument('--disc-selection', type=Path, required=True)
    parser.add_argument('--prestrip-elf', type=Path)
    parser.add_argument('--tool-prefix', default='sh-elf-')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('report already exists; retain old results and select a new path')
    public = args.disc_selection
    published = {p.name: p for p in (public / 'dc').glob('*.ovl')}
    rebuilt = {p.name: p for p in args.overlays.glob('*.ovl')}
    rows = []
    with tempfile.TemporaryDirectory(prefix='re4-release-identity-') as temporary:
        temporary = Path(temporary)
        raw = temporary / 'program.bin'
        drop = ['-R', '.stack']
        for section in sections(args.tool_prefix, args.elf):
            drop += ['-R', section]
        subprocess.run([args.tool_prefix + 'objcopy', *drop, '-O', 'binary',
                        str(args.elf), str(raw)], check=True)
        pairs = [('1ST_READ.BIN', raw, public / '1ST_READ.BIN')]
        pairs += [(name, rebuilt.get(name), published.get(name))
                  for name in sorted(set(rebuilt) | set(published))]
        for name, candidate, reference in pairs:
            row = {'name': name, 'exact': False}
            if candidate and reference and candidate.is_file() and reference.is_file():
                row.update(candidate_sha256=digest(candidate), public_sha256=digest(reference),
                           bytes=reference.stat().st_size,
                           exact=candidate.read_bytes() == reference.read_bytes())
            rows.append(row)
        prestrip = []
        if args.prestrip_elf:
            import struct
            available = sections(args.tool_prefix, args.prestrip_elf)
            for name, reference in sorted(published.items()):
                match = [s for s in available if s.removeprefix('.ovl_').lower() == name[:-4].lower()]
                row = {'name': name, 'exact': False}
                data = reference.read_bytes()
                if len(match) == 1 and len(data) >= 64:
                    header = struct.unpack('<16I', data[:64])
                    dump = temporary / name
                    subprocess.run([args.tool_prefix + 'objcopy', '-j', match[0], '-O', 'binary',
                                    str(args.prestrip_elf), str(dump)], check=True)
                    row.update(section=match[0], link_base=hex(header[4]),
                               exact=header[0] == 0x4f344552 and header[1] == 1 and
                               dump.read_bytes() == data[64:64 + header[2]])
                prestrip.append(row)
        accepted = bool(published) and all(r['exact'] for r in rows)
        if args.prestrip_elf:
            accepted = accepted and all(r['exact'] for r in prestrip)
        report = dict(accepted=accepted, elf_sha256=digest(args.elf),
                      program_and_overlays=rows, prestrip_sections=prestrip,
                      runtime_relocation_base_verified=False,
                      limits=['No hardware PC symbolization without an independently bound runtime module base',
                              'Public package bytes do not prove the reporter SD card bytes'])
        if args.prestrip_elf:
            report['prestrip_elf_sha256'] = digest(args.prestrip_elf)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(accepted=accepted, files=len(rows), prestrip_sections=len(prestrip))))
        return 0 if accepted else 1


if __name__ == '__main__':
    raise SystemExit(main())
