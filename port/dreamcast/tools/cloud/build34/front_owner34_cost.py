#!/usr/bin/env python3
"""Host-only production Ft object footprint; target SH-4 compiler is required for target cost."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import front_sources as source


def main():
    values = source.source_values()
    template = (source.HERE / 'front_fixture_types.hpp.in').read_text()
    template = template.replace('@CACHE@', '''
struct cSmd { u8 Version, Flag; u16 nModel; u32 BinTblOfs, TplTblOfs, MotTblOfs; };
#include "''' + str(source.ROOT / 'src/game/frontend_tpl_owner34.h') + '''"
@CACHE@''')
    cpp = source.render(template, values)
    cpp += '\nextern "C" int front_owner_footprint(cModel* m,cModelInfo* i,ModelData* d) { return frontTexInit(m,i,d); }\n'
    with tempfile.TemporaryDirectory(prefix='front-owner34-cost-') as temp:
        results = []
        for mode in (0, 1):
            folder = Path(temp) / str(mode)
            folder.mkdir()
            src = folder / 'foot.cpp'
            obj = folder / 'foot.o'
            src.write_text(cpp)
            compile_result = subprocess.run(['g++', '-std=c++20', '-O2', '-fpermissive', '-w',
                                             '-fstack-usage', '-DRE4DC_FRONT_TEXOBJ=1',
                                             f'-DRE4DC_FRONT_TPL_OWNER={mode}', '-c',
                                             str(src), '-o', str(obj)], capture_output=True, text=True)
            assert compile_result.returncode == 0, compile_result.stderr
            sections = subprocess.check_output(['size', '-A', str(obj)], text=True)
            sizes = {line.split()[0]: int(line.split()[1]) for line in sections.splitlines()
                     if re.match(r'^\.[A-Za-z0-9_.]+\s+\d+', line)}
            stack = (folder / 'foot.su').read_text().splitlines()
            consumer = [line for line in stack if 'front_owner_footprint' in line]
            publisher = [line for line in stack if 're4dc_front_tpl_smd_publish' in line]
            assert len(consumer) == 1 and len(publisher) == mode
            results.append((mode, sizes, int(consumer[0].split('\t')[1]),
                            int(publisher[0].split('\t')[1]) if publisher else 0))
        for mode, sizes, consumer, publisher in results:
            print(f'owner={mode} .text={sizes.get(".text",0)} .bss={sizes.get(".bss",0)} '
                  f'.data={sizes.get(".data",0)} consumer_stack={consumer} publisher_stack={publisher}')
        before, after = results
        print(f'host-only delta: .text={after[1].get(".text",0)-before[1].get(".text",0):+} '
              f'.bss={after[1].get(".bss",0)-before[1].get(".bss",0):+}; '
              '32-bit field layout: 64*36=2304 owner-row bytes + 32*4=128 key-extension bytes '
              '+ at least 25 scalar bytes, before target alignment; '
              'target layout/linker and SH-4 text/stack are unmeasured')


if __name__ == '__main__':
    main()
