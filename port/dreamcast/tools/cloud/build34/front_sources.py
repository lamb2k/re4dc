"""Exact source extraction shared by the FRONT_TEXOBJ host/cost fixtures."""
from pathlib import Path
import hashlib
import re
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
TRANS = ROOT / 'src/game/trans.cpp'
GX = DC / 'game/platform/gx_stub.cpp'
MISC = DC / 'game/platform/misc.cpp'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function(source, name):
    start = source.index(name)
    body = source.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def source_values(control_ref=None):
    trans = TRANS.read_text() if control_ref is None else subprocess.check_output(
        ['git', 'show', control_ref + ':src/game/trans.cpp'], cwd=ROOT, text=True)
    start = trans.index('#if RE4DC_FRONT_TEXOBJ\n// D367 records30')
    end = trans.index('static void frontNativeModelTrans(', start)
    native = function(trans[end:], 'static void frontNativeModelTrans(')
    loop_start = native.index('for (i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++)')
    loop_end = native.index('\n            }\n        }\n        PSet(g_prev_tpl_addr', loop_start)
    return dict(CACHE=trans[start:end],
        SOURCE_LOOP=native[loop_start:loop_end],
        SWAP=function(trans, 'void cTexChg::move('),
        GX_INIT=function(GX.read_text(), 'void GXInitTexObj('),
        TEX_GET=function(MISC.read_text(), 'TEXDescriptor* TEXGet('),
        GX_WORK=function(trans, 'struct GxWork {') + ';',
        MODEL_EXT=function(trans, 'struct cModelExt {') + ';',
        TPL_HEADER=str(ROOT / 'include/tpl.h'))


def render(template, values):
    result = template
    for name, value in values.items():
        result = result.replace('@' + name + '@', value)
    assert not re.search(r'@[A-Z_0-9]+@', result), 'Unsubstituted front fixture token'
    return result


def source_files():
    return [TRANS, GX, MISC, ROOT / 'include/tpl.h', ROOT / 'include/trans.h',
            ROOT / 'include/model.h', ROOT / 'include/global.h',
            HERE / 'front_sources.py', HERE / 'front_fixture_types.hpp.in']
