#!/usr/bin/env python3
"""Prepare observational model-id witnesses in a private logic18 hwsim copy.

Requires the exact source accessor machine code and stable NMRM-admitted source
models in the selected interval. No runtime, timing rule or context state changes.
Compile/replay the generated private copy, then require timing and context parity.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def elf_bytes(data, address, length):
    if data[:6] != b'\x7fELF\x01\x01':
        raise ValueError('Expected little-endian ELF32')
    ph = struct.unpack_from('<I', data, 28)[0]
    size, count = struct.unpack_from('<HH', data, 42)
    for i in range(count):
        h = struct.unpack_from('<8I', data, ph+i*size)
        if h[0] == 1 and h[2] <= address and address+length <= h[2]+h[4]:
            return data[h[1]+address-h[2]:h[1]+address-h[2]+length]
    raise ValueError('Accessor is outside verified loaded bytes')


def source_models_in_window(text, descriptors, window):
    """Consume the source logger's actual admit and room-less retire records."""
    lo, hi = window
    active, events = {}, []
    for line in text.splitlines():
        admit = re.search(r'NMRM admit t=(\d+) room=([0-9a-f]+) m=([0-9a-f]+)(.*)', line)
        retire = re.search(r'NMRM retire t=(\d+)(?: room=([0-9a-f]+))? m=([0-9a-f]+)(?:\s|$)', line)
        if admit:
            tick, room, model, rest = admit.groups()
            name = re.search(r'\bdesc=([\w-]+)', rest)
            if not name:
                raise ValueError('Source admit lacks descriptor identity')
            kind, name = 'admit', name[1]
        elif retire:
            tick, room, model = retire.groups()
            kind, name = 'retire', None
        elif 'NMRM admit ' in line or 'NMRM retire ' in line:
            raise ValueError('Malformed source model ownership record')
        else:
            continue
        tick = int(tick)
        if tick < lo:
            if kind == 'admit':
                active[model] = dict(model=model,name=name,room=room,admitted_tick=tick)
            else:
                if room and model in active and active[model]['room'] != room:
                    raise ValueError('Source retirement room differs')
                active.pop(model, None)
        elif tick <= hi:
            events.append((model, name))
    selected = {m:r for m,r in active.items() if r['name'] in descriptors}
    if not selected or {r['name'] for r in selected.values()} != set(descriptors):
        raise ValueError('Selected descriptors lack stable admitted models before interval')
    if any(m in selected or n in descriptors for m,n in events):
        raise ValueError('Selected source ownership changes inside interval')
    return selected


def prepare(profile, boot, output, descriptors, window):
    lo, hi = window
    if lo > hi or output.exists():
        raise ValueError('Invalid interval or existing output')
    runtime = profile/'runtime.elf'
    manifest = json.loads((profile/'runtime.json').read_text())
    if sha(runtime) != manifest['augmented_elf_sha256'] or sha(boot) != manifest['boot_sha256']:
        raise ValueError('Runtime ELF or exact loader log identity differs')
    symbols = json.loads((profile/'runtime-symbols.json').read_text())['symbols']
    getter = [r for r in symbols if r['name'] == 're4dc_actor_model_id']
    if len(getter) != 1:
        raise ValueError('Need one exact model-id getter extent')
    getter = getter[0]
    # model_bridge.cpp: null guard; kindid==0; byte id at model+0x100.
    words = (0x2448,0x8909,0x900c,0x304c,0x840e,0x2008,0x8b06,
             0x9008,0x304c,0x8400,0x000b,0x600c,0x000b,0xe0ff,
             0x000b,0xe0ff,0x0120,0x0100)
    expected = struct.pack('<18H', *words)
    actual = elf_bytes(runtime.read_bytes(), getter['start'], len(expected))
    if getter['end']-getter['start'] != len(expected) or actual != expected:
        raise ValueError('Source getter instruction/field contract differs; audit first')
    raw = boot.read_bytes()
    text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8')
    selected = source_models_in_window(text, descriptors, window)
    pc = getter['start']+18
    cases = ''.join(f'        if(a==0x{int(m,16)+0x100:08x}U)m=0x{m}U;\n' for m in selected)
    extra = r'''
/* Host-only observation. Does not modify charge tokens, nodes or timing. */
static void b18_model_witness(u32 pc,u16 op,const Ev* ev,int nev) {
    if(!l18_enabled || pc!=ACCESSOR_PC) return;
    if(op!=0x8400U) l18_die("boss model-id getter instruction differs");
    for(int i=0;i<nev;i++) {
        if(ev[i].type!=2 || ev[i].size!=1) continue;
        u32 a=ev[i].addr, m=0;
MODEL_CASES
        if(!m) continue;
        unsigned cur=l18_current,common=~0U,tx=~0U;
        for(unsigned guard=0;guard<256 && cur<l18_count;guard++) {
            const L18Node* n=&l18_nodes[cur];
            const char* name=n->symbol?l18_symbols[n->symbol].name:"UNKNOWN";
            if(common==~0U && !strcmp(name,"commonModelTrans"))common=cur;
            if(tx==~0U && !strcmp(name,"re4dc_actor_transaction_draw"))tx=cur;
            if(n->parent>=cur)break;
            cur=n->parent;
        }
        static FILE* out;
        if(!out) {
            const char* path=getenv("B18_MODEL_WITNESS");
            if(!path)l18_die("boss witness output missing");
            out=fopen(path,"w");if(!out)l18_die("boss witness output unavailable");
            fputs("sample\tnode\tcommon_root\ttx_root\tmodel\tpc\taddress\tsize\n",out);
        }
        fprintf(out,"%u\t%u\t%u\t%u\t%08x\t%08x\t%08x\t%u\n",l18_sample,l18_current,common,tx,m,pc,a,ev[i].size);
        fflush(out);
    }
}
'''.replace('ACCESSOR_PC', f'0x{pc:08x}U').replace('MODEL_CASES', cases)
    source = profile/'simulator/hwsim_profile.c'
    code = source.read_text()
    anchor = 'typedef struct { u32 addr, type, size, size_code; } Ev;'
    hook = '    l18_before(pc, op);'
    if code.count(anchor) != 1 or code.count(hook) != 1:
        raise ValueError('Expected unique unchanged exporter anchors')
    code = code.replace(anchor, anchor+'\n'+extra).replace(hook, hook+'\n    b18_model_witness(pc,op,ev,nev);')
    output.mkdir(parents=True)
    (output/'hwsim_profile_witness.c').write_text(code)
    shutil.copyfile(profile/'simulator/profile_context.h', output/'profile_context.h')
    proof = dict(source_profile_C_sha256=sha(source),runtime_elf_sha256=sha(runtime),
                 runtime_manifest_sha256=sha(profile/'runtime.json'),boot_sha256=sha(boot),
                 symbols_sha256=sha(profile/'runtime-symbols.json'),getter=getter,
                 accessor_pc=pc,id_offset=0x100,getter_bytes_sha256=hashlib.sha256(actual).hexdigest(),
                 window=list(window),models=list(selected.values()),
                 contract='Exact source kindid0/id getter and stable native descriptor log; observational host copy only. Timing/context parity and complete valid invocation coverage required separately.')
    (output/'build-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--boot',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--descriptors',required=True)
    p.add_argument('--window',required=True,help='First:last source tick, inclusive')
    a=p.parse_args()
    print(json.dumps(prepare(a.profile,a.boot,a.out,a.descriptors.split(','),tuple(map(int,a.window.split(':')))),indent=2))
