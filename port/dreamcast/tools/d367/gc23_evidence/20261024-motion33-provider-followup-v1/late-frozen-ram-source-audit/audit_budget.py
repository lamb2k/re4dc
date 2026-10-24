"""Read exact ELF/source/receipts and derive conditional capacity bounds only."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

OUT=Path(__file__).resolve().parent
TREE=Path('/root/work/lanes/gc-motion24')
KOS=Path('/root/work/kos-re4dc-d367')
BUILD=Path('/root/work/lanes/gc-port23-full-target2-scratch')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-target-static1d63-current')

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()

def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}

class Elf:
    def __init__(self,p):
        self.path=p
        with p.open('rb') as f:
            h=struct.unpack('<16sHHIIIIIHHHHHH',f.read(52))
            assert h[0][:6]==b'\x7fELF\x01\x01' and h[2]==42
            f.seek(h[6]);self.sections=[struct.unpack('<IIIIIIIIII',f.read(h[11])) for _ in range(h[12])]
            s=self.sections[h[13]];f.seek(s[4]);names=f.read(s[5])
            self.named={names[s[0]:].split(b'\0',1)[0].decode():s for s in self.sections}
            self.symbols={}
            for s in self.sections:
                if s[1]!=2:continue
                st=self.sections[s[6]];f.seek(st[4]);strings=f.read(st[5])
                f.seek(s[4]);data=f.read(s[5])
                for i in range(0,len(data),s[9]):
                    name,value,size,info,other,index=struct.unpack_from('<IIIBBH',data,i)
                    name=strings[name:].split(b'\0',1)[0].decode('utf-8','replace')
                    if not name:continue
                    q={'address':value,'size':size,'section':index,'type':info&15}
                    if name not in self.symbols or size>self.symbols[name]['size']:self.symbols[name]=q
    def word(self,name):
        q=self.symbols[name];s=self.sections[q['section']]
        with self.path.open('rb') as f:
            f.seek(s[4]+q['address']-s[3]);return struct.unpack('<I',f.read(4))[0]

def main():
    receipt=json.loads((E/'receipt.json').read_text(encoding='utf-8-sig'))
    summary=json.loads((E/'SUMMARY.json').read_text(encoding='utf-8-sig'))
    arms={}
    for arm in ('off','on'):
        p=BUILD/arm/'out/re4dc-game.elf';actual=pin(p)
        assert actual['sha256']==receipt['arms'][arm]['files']['re4dc-game.elf']['sha256']
        elf=Elf(p)
        end=elf.symbols['_end']['address']
        assert end==summary['boundary_symbols'][arm]['_end']
        knobs={k:v for line in (E/arm/'resolved-knobs.txt').read_text().splitlines() if '=' in line for k,v in [line.split('=',1)]}
        keys=['ARENA_FIT','ARENA_FIT_KOS_BYTES','ARENA_KOS_BYTES','SOUND_REGION_BYTES','CORE_RESIDENT_BYTES','OPTION_RESIDENT_BYTES',
              'PLAYER_RESIDENT_BYTES','WEAPON_RESIDENT_BYTES','IMAGE_PAD_BYTES','KOS_SBRK_LAST_PAGE','KOS_SQUEEZE','SS_FREEZE_RESERVE_BYTES',
              'TEX_SLOTS','TEX_META_EVICT','LINK_TIGHT','LINK_OVL_HELPERS','GC_ASSET_GATE','GC_ASSET_CATALOG_SHA256','MOTION_CAPACITY']
        fixed=sum(int(knobs[k],0) for k in ['SOUND_REGION_BYTES','CORE_RESIDENT_BYTES','OPTION_RESIDENT_BYTES','PLAYER_RESIDENT_BYTES','WEAPON_RESIDENT_BYTES'])
        stacks={n:elf.word('_arch_stack_'+n) for n in ('16m','32m')}
        bss=elf.named['.bss'];entry=elf.symbols['__ZN12_GLOBAL__N_1L7entriesE']
        symbol_names=[n for n in elf.symbols if ('gcasset' in n or 're4dc_gcasset' in n) and elf.symbols[n]['size'] and
                      elf.symbols[n]['section']<len(elf.sections) and elf.sections[elf.symbols[n]['section']][2]&2 and elf.symbols[n]['type']==1]
        objects=sorted([{'name':n,**elf.symbols[n]} for n in symbol_names],key=lambda x:-x['size'])
        limit=stacks['16m']-65536
        arms[arm]={'ELF':actual,'end':end,'end_hex':hex(end),'linked_bss':bss[5],'entries_array':entry,'selected_knobs':{k:knobs[k] for k in keys},
            'fixed_carve_bytes':fixed,'stack_top_words':{k:hex(v) for k,v in stacks.items()},'normal_16MiB_sbrk_limit':hex(limit),
            'coherent_fit_upper_bound_not_measured':min(13*1024*1024-int(knobs['ARENA_KOS_BYTES']),
                (limit-end-int(knobs['ARENA_FIT_KOS_BYTES'])-64)&~4095),
            'gc_named_resident_objects':objects}
    delta=arms['on']['end']-arms['off']['end']
    assert delta==60384
    residues=sorted({((r+delta)//4096)*4096 for r in range(4096)})
    assert residues==[57344,61440]
    assert arms['off']['entries_array']['size']==arms['on']['entries_array']['size']==100352
    assert arms['off']['fixed_carve_bytes']==arms['on']['fixed_carve_bytes']==3048896
    for a in arms.values():
        assert a['selected_knobs']['ARENA_FIT']=='1' and a['selected_knobs']['KOS_SBRK_LAST_PAGE']=='1'
    source_paths=[TREE/p for p in [
        'port/dreamcast/game/platform/mem.cpp','port/dreamcast/game/platform/os.cpp','port/dreamcast/game/ui_bridge.cpp',
        'src/game/main_mem.cpp','src/game/game.cpp','src/lib/OSAlloc.c','include/main_mem.h',
        'port/dreamcast/game/Makefile','port/dreamcast/game/platform/native_movie.cpp',
        'port/dreamcast/game/platform/gc_asset_gate.cpp','port/dreamcast/game/platform/gc_asset_disc.cpp',
        'port/dreamcast/game/platform/gc_asset_members.cpp','port/dreamcast/game/platform/gc_asset_motion_unknown.cpp',
        'port/dreamcast/docs/qualification/AUDITS23_20261023.md',
        'port/dreamcast/game/platform/sdk/dolphin.h','port/dreamcast/game/platform/sdk/dolphin/os.h']]
    source_paths += [KOS/p for p in ['kernel/mm/mm.c','kernel/libc/koslib/malloc.c','kernel/libc/newlib/newlib_sbrk.c',
        'kernel/arch/dreamcast/include/arch/stack.h','kernel/arch/dreamcast/include/arch/arch.h','kernel/arch/dreamcast/kernel/startup.S',
        'kernel/arch/dreamcast/kernel/init.c','utils/ldscripts/shlelf.xc','lib/dreamcast/libkallisti.a','kernel/fs/fs.c']]
    source_paths += [BUILD/arm/'out/obj/kosmm'/name for arm in ('off','on') for name in ('mm.c','mm.o')]
    source_paths += [E/n for n in ['receipt.json','SUMMARY.json','SHA256-MANIFEST.json']]
    source_paths += [E/arm/n for arm in ('off','on') for n in ['resolved-knobs.txt','symbols.txt','load-segments.txt','sections.txt']]
    pins=[pin(p) for p in source_paths]
    assert next(p['sha256'] for p in pins if p['path']==str(KOS/'lib/dreamcast/libkallisti.a'))=='5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf'
    private=(BUILD/'on/out/obj/kosmm/mm.c').read_text()
    assert 'if(new_base > (_arch_mem_top - THD_KERNEL_STACK_SIZE))' in private
    comparisons={}
    for rel in ['port/dreamcast/game/platform/mem.cpp','port/dreamcast/game/platform/os.cpp','port/dreamcast/game/ui_bridge.cpp',
                'src/game/main_mem.cpp','src/game/game.cpp','src/lib/OSAlloc.c','port/dreamcast/game/Makefile']:
        a=subprocess.check_output(['git','-C',str(TREE),'show','1d63cffe3a232c402418f2f2d919e7abae476957:'+rel])
        comparisons[rel]=a==(TREE/rel).read_bytes()
    metadata_arms={}
    for arm in ('off','on'):
        mm=Elf(BUILD/arm/'out/obj/kosmm/mm.o')
        metadata_arms[arm]={}
        with mm.path.open('rb') as f:
            for name,s in mm.named.items():
                if s[2]&2:
                    f.seek(s[4]);raw=f.read(s[5]) if s[1]!=8 else b''
                    metadata_arms[arm][name]={'size':s[5],'sha256':hashlib.sha256(raw).hexdigest()}
    assert metadata_arms['off']==metadata_arms['on']
    result={'status':'SOURCE_BOUND_CAPACITY_AUDIT_ONLY','linked_baseline_source':receipt['source'],
        'current_source':subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip(),
        'source_comparison_to_linked_1d63':comparisons,'arms':arms,'end_delta':delta,
        'conditional_same_prearena_trace_fit_reduction_bytes':residues,
        'condition':'Coherent active fit clamp; identical translated pre-arena allocation trace/top-chunk state; no intervening allocator activity or extra memalign failure/retry differences.',
        'private_mm_alloc_sections_identical':True,'private_mm_alloc_section_readback':metadata_arms,
        'measured_H2_heap_loss':None,'measured_KOS_heap_loss':None,'current_catalog_motion_full_link_price':None,
        'pins':pins,'scope':'No SDK/build/guest/reserve/arena/recipe changes. ELF/source/receipt reads only; arithmetic upper bounds are not runtime measurements.'}
    (OUT/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'end_delta':delta,'conditional_fit_loss':residues,
        'arms':{a:{k:v for k,v in x.items() if k in ('end_hex','fixed_carve_bytes','coherent_fit_upper_bound_not_measured','stack_top_words')} for a,x in arms.items()},
        'changed_allocator_files':[p for p,same in comparisons.items() if not same]}))

if __name__=='__main__':main()
