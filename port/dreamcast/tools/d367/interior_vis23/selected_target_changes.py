#!/usr/bin/env python3
"""Generate an UNAPPLIED owner proposal; never edit shared runtime sources."""
from pathlib import Path
import difflib

NATIVE = 'port/dreamcast/game/platform/native_static.cpp'
MAKE = 'port/dreamcast/game/t2exact.mk'
CERTIFY = 'port/dreamcast/tools/d367/interior_vis23/certify.py'


def once(source, old, new):
    if source.count(old) != 1:
        raise AssertionError(f'proposal anchor is not unique: {old!r}')
    return source.replace(old, new)


def propose(files):
    out = dict(files)
    source = files[NATIVE]
    source = once(source,
        '#if RE4DC_PS2_PVS\n        const std::uint8_t* const pvs_cur=pvs::can_cut(i)?pvs::cur:nullptr;',
        '#if RE4DC_PS2_PVS && !RE4DC_PS2_PVS_SELECTED_TARGETS\n        const std::uint8_t* const pvs_cur=pvs::can_cut(i)?pvs::cur:nullptr;')
    source = once(source,
        '#if RE4DC_PS2_PVS\n        if(pvs_cur && pvs::hidden(i))continue;',
        '#if RE4DC_PS2_PVS && !RE4DC_PS2_PVS_SELECTED_TARGETS\n        if(pvs_cur && pvs::hidden(i))continue;')
    anchor = '        const unsigned pvs_source_placement=(RE4DC_PS2_AFFINE==pl.affine)?i:~0U;\n#endif'
    source = once(source, anchor, anchor + '''
#if RE4DC_PS2_PVS && RE4DC_PS2_PVS_SELECTED_TARGETS
        // Target certificates cover baked geometry. Query may retain a moved
        // delta after a fresh-rest check, so qualify only the selected affine.
        const std::uint8_t* const pvs_cur=pvs_source_placement==i && pvs::can_cut(i)?pvs::cur:nullptr;
        if(pvs_cur && pvs::hidden(i))continue;
#endif''')
    out[NATIVE] = source
    source = once(files[MAKE], 'PS2_PVS_DEFAULT ?= 1', '''PS2_PVS_DEFAULT ?= 1
# Qualify conditional target tables only after the actual dynamic affine choice.
# Default 0 keeps the previously qualified static-target path unchanged.
PS2_PVS_SELECTED_TARGETS ?= 0
ifneq ($(PS2_PVS_SELECTED_TARGETS),0)
ifneq ($(PS2_PVS_SELECTED_TARGETS),1)
$(error PS2_PVS_SELECTED_TARGETS must be 0 or 1)
endif
ifneq ($(PS2_PVS),1)
$(error PS2_PVS_SELECTED_TARGETS needs PS2_PVS=1)
endif
endif''')
    source = once(source,
        '-DRE4DC_PS2_PVS=1 -DRE4DC_PS2_PVS_DEFAULT=$(PS2_PVS_DEFAULT)',
        '-DRE4DC_PS2_PVS=1 -DRE4DC_PS2_PVS_DEFAULT=$(PS2_PVS_DEFAULT) -DRE4DC_PS2_PVS_SELECTED_TARGETS=$(PS2_PVS_SELECTED_TARGETS)')
    out[MAKE] = source
    source = once(files[CERTIFY], "    if panels:(root/'pvs23_certificates.inc').write_text('\\n'.join(lines)+'\\n')", '''    if a.conditional_targets:
        # This exact table/descriptor pair must never run the earlier target
        # gate. Research status and all geometric/runtime gates still apply.
        lines=['#if !defined(RE4DC_PS2_PVS_SELECTED_TARGETS) || RE4DC_PS2_PVS_SELECTED_TARGETS != 1',
               '#error "conditional-target PVS descriptor requires PS2_PVS_SELECTED_TARGETS=1"',
               '#endif']+lines
    if panels:(root/'pvs23_certificates.inc').write_text('\\n'.join(lines)+'\\n')''')
    out[CERTIFY] = source
    return out


def read_inputs(repo):
    return {path: (repo/path).read_text() for path in (NATIVE, MAKE, CERTIFY)}


def proposal_patch(before, after):
    return ''.join(''.join(difflib.unified_diff(before[path].splitlines(True), after[path].splitlines(True),
                                              fromfile='a/'+path, tofile='b/'+path)) for path in before)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    inputs = read_inputs(here.parents[4])
    (here/'selected-targets-owner.patch').write_text(proposal_patch(inputs, propose(inputs)))
