#!/usr/bin/env python3
"""Host-only synthetic controls. All C++ executables and fixtures live in /dev/shm."""
import copy, json, pathlib, random, shutil, struct, subprocess, sys, tempfile
import audit as A


def refused(fn):
    try:
        fn()
    except (ValueError, KeyError, OSError, struct.error):
        return
    raise AssertionError('negative was accepted')


def cpp_fixture(directory, flip, mutant=None):
    source = A.selector_source()
    if mutant == 'no-flip':
        source = source.replace('p -= p % RE4DC_WATER_PS2_FLIP;', 'p = p;')
    if mutant == 'wide-product':
        source = source.replace('(tick * (u32) r.rate)', '((unsigned long long)tick * (u32) r.rate)')
    prefix = '''#include <cstdint>
#include <iostream>
using u32=uint32_t; using u8=uint8_t;
struct WaterPs2Row { u8 rate,ptn0; };
struct EspAnmData { u32 Frames,Data_num; u8 Frame_cnt[8192]; };
struct EspTexWk { EspAnmData* pAnm; };
'''+f'#define RE4DC_WATER_PS2_FLIP {flip}\n'
    tail = '''
int main(){u32 n,raw,dn,nil,rate,p,tick,count;
while(std::cin>>n>>raw>>dn>>nil>>rate>>p>>tick>>count){
if(count>8192)return 2;EspAnmData a{};a.Frames=raw;a.Data_num=dn;
for(u32 i=0;i<count;++i){u32 v;std::cin>>v;a.Frame_cnt[i]=v;}
EspTexWk tw{nil?nullptr:&a};WaterPs2Row r{(u8)rate,(u8)p};
std::cout<<WaterPs2Pattern(r,&tw,n,tick)<<"\\n";}}
'''
    cpp=directory/f'select-{flip}-{mutant}.cpp';exe=cpp.with_suffix('')
    cpp.write_text(prefix+source+tail)
    subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra',str(cpp),'-o',str(exe)],check=True,capture_output=True)
    return exe


def cpp_run(exe, cases):
    data=[]
    for animation,n,rate,p,tick in cases:
        raw=animation['frames'] if animation else 0
        dn=animation['data_num'] if animation else 0
        table=animation['frame_cnt'] if animation else []
        data.append(' '.join(map(str,[n,raw,dn,int(animation is None),rate,p,tick,len(table),*table])))
    return [int(x) for x in subprocess.check_output([str(exe)],input=('\n'.join(data)+'\n').encode()).split()]


def selector_controls(directory):
    rng=random.Random(0x24a)
    animations=[None,{'frames':0,'data_num':0,'frame_cnt':[]},
                {'frames':3,'data_num':1,'frame_cnt':[0,1,2,0,4,1]},
                {'frames':6,'data_num':1,'frame_cnt':list(range(6))+[0,0,1,0,2,0]},
                {'frames':2,'data_num':1,'frame_cnt':[0,1,0,0]},
                {'frames':9,'data_num':0,'frame_cnt':list(range(9))}]
    total=0
    for flip in (1,8,16):
        cases=[]
        for animation in animations:
            for n in (0,1,2,3,8,17):
                for rate in (0,1,32,36,42,128,255):
                    try:
                        legal=A.legal_patterns(animation,n,rate,255,flip)
                    except ValueError:
                        continue
                    ticks={0,1,31,32,33,0x7fffffff,0x80000000,0xfffffffe,0xffffffff,*legal.values()}
                    ticks.update(rng.randrange(1<<32) for _ in range(8))
                    for tick in ticks:
                        cases.append((animation,n,rate,255,tick))
                    # Exhaustive short period supplements the exact algebra and wrap cases.
                    sampled={A.select(animation,n,rate,255,t,flip) for t in range(1024)}
                    assert sampled<=legal.keys()
        expected=[A.select(*c,flip) for c in cases]
        actual=cpp_run(cpp_fixture(directory,flip),cases)
        assert len(actual)==len(cases) and actual==expected
        total+=len(cases)
        if flip==8:
            for mutation in ('no-flip','wide-product'):
                assert cpp_run(cpp_fixture(directory,flip,mutation),cases)!=expected,mutation
    refused(lambda:A.legal_patterns({'frames':3,'data_num':1,'frame_cnt':[0,1]},3,32,0,8))
    refused(lambda:A.legal_patterns(None,3,32,0,0))
    refused(lambda:A.legal_patterns(None,5000,32,0,8))
    refused(lambda:A.legal_patterns({'frames':1000,'data_num':1,'frame_cnt':[0]*1000+[255]*1000},1000,255,0,8))
    return total


def eff(tex,n,ps2=False):
    endian='<' if ps2 else '>'
    if not ps2:
        head=12+8*n;pixels=head+12*n
        tpl=bytearray(pixels+32*n)
        struct.pack_into('>3I',tpl,0,0x0020af30,n,12)
        for i in range(n):
            struct.pack_into('>2I',tpl,12+8*i,head+12*i,0)
            struct.pack_into('>HHII',tpl,head+12*i,8,8,0,pixels+32*i)
            tpl[pixels+32*i:pixels+32*(i+1)]=bytes([17*(i+1)])*32
    else:
        tpl=bytearray(12+48*n+128*n)
        struct.pack_into('<3I',tpl,0,0x1000,n,12)
        for i in range(n):
            d=12+48*i;pixels=12+48*n+128*i
            struct.pack_into('<4H',tpl,d,8,8,8,0)
            struct.pack_into('<2I',tpl,d+32,pixels,pixels+32)
            tpl[pixels:pixels+128]=bytes([i+1])*128
    a=80+len(tpl);out=bytearray(a+16+2*n)
    struct.pack_into(endian+'12I',out,0,11,48,0,0,0,0,60,68,0,0,0,0)
    struct.pack_into(endian+'IHHI',out,48,1,tex,0,0)
    struct.pack_into(endian+'2I',out,60,1,20)
    struct.pack_into(endian+'2I',out,68,1,a-68)
    out[80:a]=tpl;struct.pack_into(endian+'H',out,a+8,n);out[a+12]=1
    out[a+16:a+16+2*n]=bytes(range(n))+bytes([1]*n)
    return bytes(out)


def inventory_controls(directory):
    def ref(name,data):
        (directory/name).write_bytes(data)
        return {'file':name,'sha256':A.digest(data),'span_sha256':A.digest(data)}
    gc,ps=eff(0xfe,3),eff(0xfe,2,True)
    sr,pr=ref('source.eff',gc),ref('ps2.eff',ps)
    source,target=A.eff_texture(gc,0xfe),A.eff_texture(ps,0xfe,True)
    sys.path.insert(0,str(A.ROOT/'port/dreamcast/tools'))
    from convert_tpl import build_package, TplImage, MaterialBinding
    packages,bindings={},[]
    for i,im in enumerate(source['pictures']):
        # Entirely synthetic host fixture, never a game asset or overlay.
        payload,_=build_package([TplImage(8,8,0,bytes([17*(i+1)])*32)],
                                [MaterialBinding('synthetic',0,None)],twiddle=True,
                                pad_to_power_of_two=True,source_intensity_alpha=True)
        packages[im['key']]=ref(im['key']+'.test',payload)
        bindings.append({'source_key':im['key'],'texture':0xfe,'ps2_frame':i%2,
                         'ps2_picture':target['pictures'][i%2],'package_sha256':A.digest(payload)})
    converter=(A.ROOT/'port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py').read_bytes()
    cr=ref('converter.test',converter)
    receipt={'schema':1,'profile':'fx_ps2_pack.py:frame-mod-v1','source_eff_sha256':A.digest(gc),
             'ps2_eff_sha256':A.digest(ps),'converter_sha256':A.digest(converter),'bindings':bindings}
    rr=ref('conversion.json',json.dumps(receipt).encode())
    scope=[r['index'] for r in A.rows() if r['room']==0x10e and r['texture']!=0xf7 and r['level']>=2]
    manifest={'schema':1,'option':'waterres24-private-off','rooms':[0x10e],'renderer_level':2,
              'selector_sha256':A.digest(A.selector_source().encode()),'source_contract':A.source_contract(),
              'flip':8,'row_scope':scope,'entries':[{'row_index':i,'source_eff':sr,'ps2_eff':pr,
              'conversion_receipt':rr,'converter':cr,'packages':packages} for i in scope]}
    result=A.audit(manifest,directory)
    assert len(result['rows'])==2 and all(len(r['selected'])==3 for r in result['rows'])
    assert result['source_owner_binding']=='UNPROVEN' and not result['origin_admitted']
    assert not result['current_loaded_payload_binding'] and not result['resident_memory_qualified']
    assert result['resident_record_coverage']['status']=='NOT_RUN'
    def pack(records):
        data=b''.join(struct.pack('<4H2I',*x) for x in records)
        return data+b'\0'*(-len(data)%512)
    original=[(0x100,8,8,0,1,2)]
    required=[tuple(x) for x in result['required_resident_records']]
    candidate=sorted(original+required,key=lambda x:(x[0],x[4],x[5]))
    manifest['resident']={'before':ref('old.bin',pack(original)),'candidate':ref('candidate.bin',pack(candidate)),
                          'remap_before':ref('old-remap.tsv',b'synthetic-remap'),'remap_candidate':ref('candidate-remap.tsv',b'synthetic-remap')}
    assert A.audit(manifest,directory)['resident_record_coverage']['status']=='RECORD_COVERAGE_ONLY'
    negatives=0
    def negative(change):
        nonlocal negatives
        altered=copy.deepcopy(manifest);change(altered);refused(lambda:A.audit(altered,directory));negatives+=1
    negative(lambda m:m.update(option='on'))
    negative(lambda m:m.update(selector_sha256='0'*64))
    negative(lambda m:m['source_contract'].update({'include/esp.h':'0'*64}))
    negative(lambda m:m.update(row_scope=scope[:-1]))
    negative(lambda m:m['entries'].pop())
    negative(lambda m:m['entries'].append(copy.deepcopy(m['entries'][0])))
    negative(lambda m:m['entries'][0]['source_eff'].update(sha256='0'*64))
    negative(lambda m:m['entries'][0]['source_eff'].update(length=len(gc)+1))
    negative(lambda m:m['entries'][0]['ps2_eff'].update(span_sha256='0'*64))
    negative(lambda m:m['entries'][0]['converter'].update(sha256='0'*64))
    for key in packages:
        negative(lambda m,k=key:m['entries'][0]['packages'].pop(k))
        negative(lambda m,k=key:m['entries'][0]['packages'][k].update(sha256='0'*64))
    for number,key in enumerate(required):
        replacement=ref('drop-resident-%d.bin'%number,pack([x for x in candidate if x!=key]))
        negative(lambda m,r=replacement:m['resident'].update(candidate=r))
    for field in ('descriptor_sha256','pixels_sha256','palette_sha256'):
        bad=copy.deepcopy(receipt);bad['bindings'][0]['ps2_picture'][field]='0'*64
        replacement=ref('bad-'+field+'.json',json.dumps(bad).encode())
        negative(lambda m,r=replacement:m['entries'][0].update(conversion_receipt=r))
    for raw,flag in [(b'bad',False),(gc[:-1],False),(ps[:-80],True)]:
        refused(lambda b=raw,p=flag:A.eff_texture(b,0xfe,p));negatives+=1
    return negatives


def preservation_controls():
    def pack(rows):
        data=b''.join(struct.pack('<4H2I',*r) for r in rows)
        return data+b'\0'*(-len(data)%512)
    old=[(0,8,8,0,7,8),(0x100,8,8,0,1,2),(0x10d,64,64,1,3,4)]
    required=[(0x10c,64,64,0,8,9),(0x10e,64,64,1,5,6)]
    ordered=sorted(old+required,key=lambda x:(x[0],x[4],x[5]))
    A.preserve_resident(pack(old),pack(ordered),required,b'remap',b'remap')
    for row in required:
        refused(lambda r=row:A.preserve_resident(pack(old),pack([x for x in ordered if x!=r]),required))
    refused(lambda:A.preserve_resident(pack(old),pack(ordered),required,b'a',b'b'))
    refused(lambda:A.preserve_resident(pack(old),pack(ordered[1:]),required))  # core record removed
    refused(lambda:A.preserve_resident(pack(old),pack([x for x in ordered if x[0]!=0x100]),required))
    refused(lambda:A.preserve_resident(pack(old),pack(ordered+[(0x200,1,1,0,1,1)]),required))
    refused(lambda:A.resident_records(pack(ordered)[1:]))
    refused(lambda:A.resident_records(pack(ordered+ordered[-1:])))
    refused(lambda:A.resident_records(pack(list(reversed(ordered)))))
    refused(lambda:A.resident_records(pack(old)+pack(required)))
    return 10


def main():
    assert len(A.rows())==22
    with tempfile.TemporaryDirectory(prefix='water-rain24-host-',dir='/dev/shm') as temporary:
        directory=pathlib.Path(temporary)
        count=selector_controls(directory)
        negatives=inventory_controls(directory)
        preservation=preservation_controls()
        print(json.dumps({'status':'PASS','selector_cpp_vectors':count,'selector_mutants_defeated':2,
                          'inventory_negatives':negatives,'resident_negatives':preservation,
                          'source_contract':A.source_contract(),
                          'limits':'host synthetic controls only; no private game payload audit, SDK, guest, residency/memory/look or origin gate acceptance'},indent=2))


if __name__=='__main__':main()
