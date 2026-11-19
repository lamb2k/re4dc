import sys
sys.path.insert(0,'/root/probe/lanes-20261016/final16/tree/port/dreamcast/tools')
import aica_banks as A
sh=A.stream_headers('/root/probe/lanes-20261014/ch22/snd/mirror-c23')
want={0x62c0000}
for k,v in sorted(sh.items()):
    if v['offset'] in want or k in ((1,0x2F),(1,0xE8),(1,0xED)):
        print(k, hex(v['offset']), v['rate'], v['samples'], 'loop' if v['flag']&4 else '', 'in ch5' if k in A.CH5_STREAMS else 'NOT in ch5')
