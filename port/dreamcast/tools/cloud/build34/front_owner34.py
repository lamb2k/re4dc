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
OLD_ALIAS_PIN = 'f90dd0482fc0bd2e4e36acc725c0917f0801d758'


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
    # Execute the production cold structural writers. Only the target's
    # 32-bit pointer-sign/address representation is adapted on the 64-bit host.
    model_text = MODEL.read_text()
    model_addr = source.function(model_text, 'void calcTplAddr(TEXPalette* tpl)')
    model_offset = source.function(model_text[model_text.index('// Inverse of calcTplAddr.'):],
                                   'void calcTplOffset(TEXPalette* tpl)')
    for field in ('tpl->descriptorArray[i].textureHeader->data',
                  'tpl->descriptorArray[i].textureHeader', 'tpl->descriptorArray'):
        old_math = '(u8*) ' + field + ' - (u8*) tpl'
        assert old_math in model_offset
        model_offset = model_offset.replace(old_math,
                                            '(std::uintptr_t) ' + field + ' - (std::uintptr_t) tpl')
    c8_text = (ROOT / 'src/game/trans.cpp').read_text()
    model_c8 = source.function(c8_text[c8_text.index('// Relocate a TPL whose texture headers also carry a CLUT'):],
                               'void CalcTplAddrC8(TEXPalette* tpl)')
    values['MODEL_TPL_ADDR'] = (model_addr.replace('void calcTplAddr(', 'void writer_calcTplAddr(', 1)
                                .replace('if ((int) tpl->descriptorArray < 0)', 'if (!host_offsets)')
                                .replace('(u32)', '(std::uintptr_t)'))
    values['MODEL_TPL_OFFSET'] = (model_offset.replace('void calcTplOffset(', 'void writer_calcTplOffset(', 1)
                                  .replace('if ((int) tpl->descriptorArray >= 0)', 'if (host_offsets)'))
    values['TRANS_C8'] = (model_c8.replace('void CalcTplAddrC8(', 'void writer_CalcTplAddrC8(', 1)
                          .replace('if ((s32) tpl->descriptorArray < 0)', 'if (!host_offsets)')
                          .replace('(u32)', '(std::uintptr_t)'))
    assert 'if (!host_offsets)' in values['MODEL_TPL_ADDR'] and 'if (host_offsets)' in values['MODEL_TPL_OFFSET']
    assert 'if (!host_offsets)' in values['TRANS_C8']
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
    old_cache = source.source_values(control_ref=OLD_ALIAS_PIN)['CACHE']
    assert values['CACHE'] in values['TYPES']
    old_values = dict(values, CACHE=old_cache, TYPES=values['TYPES'].replace(values['CACHE'], old_cache))
    old_generated = source.render(TEMPLATE.read_text(), old_values)
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
        old_cpp = Path(tmp) / 'old-alias.cpp'
        old_cpp.write_text(old_generated)
        old_exe = Path(tmp) / 'old-alias'
        old_build = subprocess.run(['g++', '-std=c++20', '-O2', '-fpermissive', '-w',
                                    '-DRE4DC_FRONT_TPL_OWNER=1', '-DRE4DC_FRONT_TEXOBJ=1',
                                    '-DFRONT_OWNER_OLD_REPRO=1', str(old_cpp), '-o', str(old_exe)],
                                   capture_output=True, text=True)
        assert old_build.returncode == 0, old_build.stderr
        old_run = subprocess.run([str(old_exe)], capture_output=True, text=True)
        assert old_run.returncode == 31 and 'FAIL: source GX object/remap/tail' in old_run.stderr, (
            old_run.returncode, old_run.stdout, old_run.stderr)
    assert frozen == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in frozen}, 'source changed during fixture'
    print('PASS front_owner34 source=' + hashlib.sha256(generated.encode()).hexdigest()[:16])
    for mode, sanitize, output in results:
        print(f'  owner={mode} sanitizer={sanitize} {output}')
    print('  pinned f90 alias control: stale qualified object reproduced; current owner walks and matches source')


if __name__ == '__main__':
    main()
