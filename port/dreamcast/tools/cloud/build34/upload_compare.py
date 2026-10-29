#!/usr/bin/env python3
"""Compare bound full-release programme, overlays and every allocated ELF section.

Whole debug ELF equality is deliberately separate. No disc/mastering, game
execution, look, STRICT, GPU lifetime or physical-console claim is made.
"""
import argparse, hashlib, json, struct
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def sections(path):
    data=path.read_bytes();assert data[:6]==b'\x7fELF\x01\x01'
    h=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
    at,step,count,strings=h[6],h[11],h[12],h[13]
    rows=[struct.unpack_from('<IIIIIIIIII',data,at+n*step) for n in range(count)]
    names=data[rows[strings][4]:rows[strings][4]+rows[strings][5]]
    result={}
    for name,kind,flags,address,offset,size,link,info,alignment,entry in rows:
        if not flags&2:continue
        name=names[name:names.index(0,name)].decode()
        payload=data[offset:offset+size] if kind!=8 else b''
        result[name]=dict(type=kind,flags=flags,address=address,bytes=size,alignment=alignment,sha256=sha(payload))
    return result

def bindings(out):
    assert (out/'missing.txt').is_file() and (out/'missing.txt').stat().st_size==0
    elf=out/'re4dc-game.elf';assert elf.stat().st_size>0
    return dict(directory=str(out),elf_sha256=sha(elf.read_bytes()),stack=(out/'stack.txt').read_text(),
        build_log_sha256=sha((out/'build.log').read_bytes()),
        resolved_knobs_sha256=sha((out/'resolved-knobs.txt').read_bytes()))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True,type=Path);p.add_argument('--arm',required=True,type=Path,action='append');p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    base=a.baseline;receipt=dict(scope=__doc__,baseline=bindings(base),arms=[])
    base_sections=sections(base/'re4dc-game.elf')
    base_overlays={p.name:sha(p.read_bytes()) for p in sorted(base.glob('*.ovl'))}
    # The raw programme is the ordered file-backed allocated load image without
    # the conventional .stack section, matching route's objcopy -R .stack.
    import subprocess
    tool='/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy'
    def programme(out):
        dest=a.output.parent/(out.name+'.programme.bin')
        subprocess.run([tool,'-R','.stack','-O','binary',str(out/'re4dc-game.elf'),str(dest)],check=True)
        return dest.read_bytes()
    a.output.parent.mkdir(parents=True,exist_ok=True);base_program=programme(base)
    for out in a.arm:
        row=bindings(out);current_sections=sections(out/'re4dc-game.elf')
        overlays={p.name:sha(p.read_bytes()) for p in sorted(out.glob('*.ovl'))}
        program=programme(out)
        row.update(programme_equal=program==base_program,programme_bytes=len(program),programme_sha256=sha(program),
            allocated_sections_equal=current_sections==base_sections,allocated_sections=current_sections,
            overlays_equal=overlays==base_overlays,overlays=overlays,
            debug_elf_equal=row['elf_sha256']==receipt['baseline']['elf_sha256'])
        receipt['arms'].append(row)
    receipt['baseline'].update(programme_sha256=sha(base_program),programme_bytes=len(base_program),allocated_sections=base_sections,overlays=base_overlays)
    receipt['status']='PASS' if all(r['programme_equal'] and r['allocated_sections_equal'] and r['overlays_equal'] for r in receipt['arms']) else 'FAIL'
    a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(status=receipt['status'],arms=len(receipt['arms']),allocated_sections=len(base_sections),overlays=len(base_overlays),receipt=str(a.output))))
    assert receipt['status']=='PASS'
if __name__=='__main__':main()
