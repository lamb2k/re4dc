#!/usr/bin/env python3
"""Build34 EF15: source-extracted frontend consumer and SMD/model producer fixture."""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import front_sources as source

HERE, ROOT = source.HERE, source.ROOT
SCROLL = ROOT / 'src/game/scroll.cpp'
MODEL = ROOT / 'src/game/model.cpp'
OWNER = ROOT / 'src/game/frontend_tpl_owner34.h'
TEMPLATE = HERE / 'front_owner34_fixture.cpp.in'


def block(text, start):
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    files = [*source.source_files(), SCROLL, MODEL, OWNER, TEMPLATE, Path(__file__)]
    frozen = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    values = source.source_values()
    types_template = (HERE / 'front_fixture_types.hpp.in').read_text()
    types_template = types_template.replace('struct cModelInfo {',
                                            'struct cModelInfo {\n    void addTplAddr(void*);\n    void setTplAddr(void*);')
    types_template = types_template.replace('@TEX_GET@', 'static unsigned descriptor_walks;\n@TEX_GET@')
    types_template = types_template.replace('@CACHE@', '''
struct cSmd {
    u8 Version, Flag; u16 nModel;
    u32 BinTblOfs, TplTblOfs, MotTblOfs;
};
#include "@OWNER_HEADER@"
@CACHE@''')
    tex_get = values['TEX_GET']
    tex_get = tex_get.replace('{', '{ ++descriptor_walks;', 1)
    values['TEX_GET'] = tex_get
    values['OWNER_HEADER'] = str(OWNER)
    values['TYPES'] = source.render(types_template, values)
    values['MODEL_ADD'] = source.function(MODEL.read_text(), 'void cModelInfo::addTplAddr(')
    values['MODEL_SET'] = source.function(MODEL.read_text(), 'void cModelInfo::setTplAddr(')
    scroll = SCROLL.read_text()
    setparam = scroll[scroll.index('int SmdSetParam('):]
    values['SCROLL_ADD'] = block(setparam, setparam.index('if (pSmdComn != NULL) {'))
    for path, text in [(ROOT / 'src/game/read.cpp', 're4dc_front_tpl_bind_room(pG->pRoom, out_data_size)'),
                       (ROOT / 'src/game/game.cpp', 're4dc_front_tpl_retire_room()'),
                       (ROOT / 'src/game/main.cpp', 're4dc_front_tpl_retire_room()'),
                       (SCROLL, 're4dc_front_tpl_smd_begin(smd, comn)'),
                       (SCROLL, 're4dc_front_tpl_smd_clear()'),
                       (SCROLL, 're4dc_front_tpl_smd_slide(this)'),
                       (MODEL, 're4dc_front_tpl_palette_changed(tpl)')]:
        assert text in path.read_text(), (path, text)
    generated = source.render(TEMPLATE.read_text(), values)
    with tempfile.TemporaryDirectory(prefix='front-owner34-') as tmp:
        cpp = Path(tmp) / 'fixture.cpp'
        cpp.write_text(generated)
        results = []
        for mode in (0, 1):
            for sanitize in (False, True):
                exe = Path(tmp) / f'owner-{mode}-{int(sanitize)}'
                flags = ['-std=c++20', '-O2', '-fpermissive', '-Wall', '-Wextra',
                         '-Wno-unused-function', '-Wno-class-memaccess',
                         f'-DRE4DC_FRONT_TPL_OWNER={mode}', '-DRE4DC_FRONT_TEXOBJ=1']
                if sanitize:
                    flags[1:2] = ['-O1', '-g', '-fsanitize=address,undefined',
                                  '-fno-omit-frame-pointer', '-no-pie']
                compile_result = subprocess.run(['g++', *flags, str(cpp), '-o', str(exe)],
                                                capture_output=True, text=True)
                assert compile_result.returncode == 0, compile_result.stderr
                env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0',
                           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                run = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
                assert run.returncode == 0, run.stdout + run.stderr
                results.append((mode, int(sanitize), run.stdout.strip()))
    assert frozen == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in frozen}, 'source changed during fixture'
    print('PASS front_owner34 source=' + hashlib.sha256(generated.encode()).hexdigest()[:16])
    for mode, sanitize, output in results:
        print(f'  owner={mode} sanitizer={sanitize} {output}')


if __name__ == '__main__':
    main()
