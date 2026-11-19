"""Build the nominal simulator with read-only observers for the M1 timing stores."""
import argparse
import subprocess
from pathlib import Path
def instrument(src):
    def replace(old,new):
        nonlocal src
        if src.count(old)!=1:raise ValueError(f"unexpected simulator source at {old!r}")
        src=src.replace(old,new)
    replace('static inline PcStat *PS(','''static unsigned phase=7,phase_mask=255,timing_base;
static PcStat outside;
static inline PcStat *PS(''') if 'static inline PcStat *PS(' in src else None
    if 'static PcStat outside;' not in src:
        point=src.index('return ram_valid(pc) ? &ps')
        point=src.rfind('\n',0,point)+1
        if 'PS(' not in src[point:point+100]:
            point=src.rfind('\n',0,point-1)+1
        src=src[:point]+"static unsigned phase=7,phase_mask=255,timing_base;\nstatic PcStat outside;\n"+src[point:]
    replace('return ram_valid(pc) ? &ps','if(!(phase_mask & (1u<<phase)))return &outside; return ram_valid(pc) ? &ps')
    replace('    const char *elf = NULL;', '''    timing_base=strtoul(getenv("M1_TIMING"),NULL,16);
    if(getenv("M1_PHASE_MASK"))phase_mask=strtoul(getenv("M1_PHASE_MASK"),NULL,0);
    const char *elf = NULL;''')
    replace('        u32 a = e->addr;', '''        u32 a=e->addr;
        if(e->type==3 && a>=timing_base && a<timing_base+600*32){
            unsigned i=(a-timing_base)/32,k=((a-timing_base)/4)&7;
            fprintf(stderr,"M1STAMP %u %u %.0f\\n",i,k,t);
            phase=k==6?0:k==7?7:k+1;
        }''')
    return src
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("simulator",type=Path)
    p.add_argument("directory",type=Path)
    a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    output=a.directory/"observe.c"
    output.write_text(instrument(a.simulator.read_text()))
    subprocess.run(["cc","-O2","-march=native",str(output),"-lm","-o",str(a.directory/"observe")],check=True)
