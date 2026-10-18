#!/usr/bin/env python3
"""Create exact ELF function extents and explicit root-owner labels for the exporter."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


OWNERS = {
    'cPlayer::move()': 1,
    'cEm10::move()': 2,
    'ObjMove': 3,
    'EspMove': 4,
}
BARRIERS = {'arch_switch_to', 'thd_switch', 'irq_set_context', 'arch_irq_set_context'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('--nm', default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm')
    a = p.parse_args()
    text = subprocess.check_output([a.nm, '-n', '-S', '-C', str(a.elf)], text=True)
    syms, vbr = {}, 0
    for line in text.splitlines():
        fields = line.split(None, 3)
        if len(fields) == 4 and fields[2] in 'tTwW':
            address, size, kind, name = fields
            row = dict(start=int(address, 16), size=int(size, 16), name=name)
        elif len(fields) >= 3 and fields[1] in 'tTwW':
            address, kind, name = line.split(None, 2)
            row = dict(start=int(address, 16), size=0, name=name)
        else:
            continue
        if row['name'] in ('_irq_vma_table', 'irq_vma_table'):
            vbr = row['start']
        old = syms.get(row['start'])
        if old is None or (row['size'] > old['size']) or (row['name'] in OWNERS and old['name'] not in OWNERS):
            syms[row['start']] = row
    rows = [dict(symbol=i + 1, **row) for i, row in enumerate(sorted(syms.values(), key=lambda r: r['start']))]
    for row in rows:
        row.update(end=row['start'] + row['size'], owner=OWNERS.get(row['name'], 0), barrier=int(row['name'] in BARRIERS))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(f'vbr {vbr:x}\n' + ''.join(f"{r['start']:x}\t{r['end']:x}\t{r['owner']}\t{r['barrier']}\t{r['name']}\n" for r in rows))
    a.out.with_suffix('.json').write_text(json.dumps(dict(elf=str(a.elf), elf_sha256=hashlib.sha256(a.elf.read_bytes()).hexdigest(), vbr=vbr, symbols=rows), indent=2))
    print(f'{len(rows)} exact function entries; {sum(r["size"] == 0 for r in rows)} zero-size extents stay unknown; VBR={vbr:x}')


if __name__ == '__main__':
    main()
