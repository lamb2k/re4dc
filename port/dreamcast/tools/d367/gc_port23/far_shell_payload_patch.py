"""Generate an unapplied far-shell observer patch; root owns the renderer."""
from pathlib import Path
import difflib

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'game/platform/far_shell.inc'


def patched(source):
    def once(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('far-shell source drift: ' + old[:90])
        source = source.replace(old, new, 1)

    # The paired native_static proposal includes gc_asset_payloads.h at file
    # scope. This fragment is included inside an anonymous namespace: never
    # include that header here, nor embed the intrusive proof in reset State.
    once('State st;', '''State st;
#if RE4DC_GC_ASSET_GATE
re4dc_gcasset::PayloadProof asset_proof;
#endif''')
    once('void close() {\n    if (st.block)', '''void close() {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(asset_proof);
#endif
    if (st.block)''')
    once('        st.bytes = size; st.room = room;', '''        st.bytes = size; st.room = room;
#if RE4DC_GC_ASSET_GATE
        if (re4dc_gcasset::ensure_disc_catalog())
            (void)re4dc_gcasset::payload_capture(asset_proof, &st, st.block, size);
#endif''')
    once('    const float near_w = near * 1.01f;', '''#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadScope asset_scope(asset_proof, &st);
#endif
    const float near_w = near * 1.01f;''')
    return source


def patch(source):
    return ''.join(difflib.unified_diff(source.splitlines(True), patched(source).splitlines(True),
        fromfile='a/port/dreamcast/game/platform/far_shell.inc',
        tofile='b/port/dreamcast/game/platform/far_shell.inc'))


if __name__ == '__main__':
    destination = HERE / 'far-shell-payload-hooks.patch'
    destination.write_text(patch(SOURCE.read_text()))
    print(destination)
