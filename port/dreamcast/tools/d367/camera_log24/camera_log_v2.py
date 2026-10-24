"""Compile the actual camera logger call through its real 256-byte constraint."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys

def parse(line):
    m=re.fullmatch(r'PS2CAM2 ((?:[0-9a-f]{8} ){26}[0-9a-f]{8})\n',line)
    if not m:raise ValueError('camera v2 requires exactly 27 complete words and newline')
    words=[int(w,16) for w in m[1].split(' ')]
    return dict(frame=words[0],far_bits=words[1],view_bits=words[2:14],projection_bits=words[14:21],viewport_bits=words[21:27])

def legacy_line(row):
    h=lambda xs:' '.join(f'{v:08x}' for v in xs)
    return f"PS2CAM f={row['frame']} cf={row['far_bits']:08x} c={h(row['view_bits'])} p={h(row['projection_bits'])} vp={h(row['viewport_bits'])}\n"

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--old-call',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert a.out.resolve().is_relative_to(Path('/dev/shm'))
    a.out.mkdir(exist_ok=False)
    source=(a.tree/'port/dreamcast/game/platform/native_static.cpp').read_text()
    pos=source.index('        re4dc_log("PS2CAM2 ');call=source[pos:source.index(';',pos)+1]
    old=a.old_call.read_text()
    head='''#include <cstdio>
#include <cstdarg>
#include <cstdint>
#include <cstdlib>
static unsigned frame_value;static char text[256];static int needed;
unsigned re4dc_ui_frame(){return frame_value;}
void re4dc_log(const char* fmt,...){va_list v;va_start(v,fmt);needed=vsnprintf(text,sizeof(text),fmt,v);va_end(v);}
int main(int argc,char**argv){frame_value=argc>1?strtoul(argv[1],nullptr,10):0xffffffffU;
unsigned far_bits=0xffffffffU,w[25];for(unsigned i=0;i<25;++i)w[i]=0x10000000U+i;
'''
    tail='\nstd::fprintf(stderr,"needed=%d\\n",needed);std::fwrite(text,1,std::char_traits<char>::length(text),stdout);}\n'
    tail=tail.replace('std::char_traits<char>::length(text)','__builtin_strlen(text)')
    cases={};sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for tag,body in [('old',old),('fixed',call),('swapped',call.replace('w[0],w[1]','w[1],w[0]'))]:
        cpp=a.out/f'{tag}.cpp';cpp.write_text(head+body+tail)
        binary=a.out/tag;cmd=['g++','-std=c++20','-O2',str(cpp),'-o',str(binary)]
        subprocess.run(cmd,check=True,capture_output=True)
        rows=[]
        for frame in (0,800,4294967295):
            r=subprocess.run([str(binary),str(frame)],check=True,capture_output=True)
            text=r.stdout.decode();(a.out/f'{tag}-{frame}.txt').write_bytes(r.stdout)
            needed=int(re.search(r'needed=(\d+)',r.stderr.decode())[1])
            if tag=='old':
                # Distinguish the tag/schema change from actual snprintf loss.
                if frame==0:assert needed==255 and len(r.stdout)==255 and text.endswith('\n')
                else:assert needed>255 and len(r.stdout)==255 and not text.endswith('\n')
            try:
                p=parse(text)
                exact=p['frame']==frame and p['far_bits']==0xffffffff and p['view_bits']+p['projection_bits']+p['viewport_bits']==list(range(0x10000000,0x10000019))
            except ValueError:exact=False
            if tag=='fixed':assert exact and len(r.stdout)==251 and text.endswith('\n')
            else:assert not exact,(tag,frame)
            rows.append(dict(frame=frame,bytes=len(r.stdout),stderr=r.stderr.decode().strip(),exact_full_record=exact))
        cases[tag]=rows
    valid=(a.out/'fixed-800.txt').read_text()
    negatives=[valid[:-1],valid.replace('10000018','1000001'),valid.replace('PS2CAM2','PS2CAM'),valid+'00000000',valid.replace('10000018','gggggggg')]
    for bad in negatives:
        try:parse(bad)
        except ValueError:pass
        else:raise AssertionError('malformed row accepted')
    projected=[]
    for body in (old,call):
        r=subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_PS2_PVS=0','-'],input=('#if RE4DC_PS2_PVS\n'+body+'\n#endif\n').encode(),check=True,capture_output=True)
        projected.append(r.stdout)
    assert projected==[b'',b'']
    report=dict(status='PASS_ACTUAL_SOURCE_FORMATTER_256B',native_sha256=sha(a.tree/'port/dreamcast/game/platform/native_static.cpp'),actual_call_sha256=hashlib.sha256(call.encode()).hexdigest(),old_call_sha256=sha(a.old_call),fixed_bytes_including_newline=251,logger_bytes=256,cases=cases,malformed_controls=len(negatives),pvs0_changed_region_identical=True,scope='Host actual formatter/argument order; not new target or guest qualification.')
    (a.out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
