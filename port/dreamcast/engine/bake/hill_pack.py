"""The hill path pack (lane eng-e1d, E1): r11d baked the way the village was (native_pack.py: whole-room compact world
from the PS2 world sidecars, per-piece bounds, materials, the nine logic streams of an old-game capture of the room,
the actor catalogue), with the E1 hill scene's two characters:
  - catalogue 0: Leon in the room's costume (chapter 2: the PS2 pl08 package's body roles 0 and 1 and its extra chunk,
    here role 9) over the pl00 model of native_models.py, which keeps eng-look's hair (the hair part with the body atlas,
    then the hair run, role 8);
  - catalogue 1-5: the Ganado appearances (native_models.py, as every pack);
  - catalogue 6: Ashley from her PS2 cast package (ashley_model.py; dc/native/r11d/partner.re4nmr).
The capture (an r3 capture of r11d: picture-NNN.bin, leon-bind.bin) gives the room's light set, environment (fog,
ambient) and HUD layout; the E1 image reads them from the first picture. Visibility: bench/bake_vis over this pack.
usage: hill_pack.py <disc dc dir> <capture dir> <out .pak> <private tables> [--report json]
"""
import argparse, json, struct
from pathlib import Path
import native_pack
import native_models
from native_models import models as base_models
from ashley_model import ashley_model
from leon_costume import pl08_chunks

ASHLEY_INDEX = 6
ROOM = 0x11d


def leon_pl08(disc, tables, cloth_bind, material):
    """native_models._model(model 0, level 0) with pl08's roles 0 and 1 and its chunk 8 (as role 9)."""
    files, tabs, hands = native_models._sources(disc, tables, cloth_bind)
    binds = tabs[0]
    b = files[0]
    base, rows, hair = native_models._leon_level(b, 0)
    swap = pl08_chunks((disc / 'native/pl08/leon_pl08_ps2.re4cp').read_bytes())
    parts = []
    for r in rows:
        arrays = [b[base + o:base + o + n] for o, n in zip(r[6:11], r[11:])]
        parts.append((r[0], swap[r[0]] if r[0] in (0, 1) else arrays))
        if r[0] == 7:   # the hair run over the hair part's positions and weights, with the hair UVs (eng-look)
            pc, tri, mat, asset, huo, hus, hro, hrs = hair
            parts.append((8, [arrays[0], arrays[1], b[base + huo:base + huo + hus], b[base + hro:base + hro + hrs], arrays[4]]))
    parts.append((9, swap[8]))
    parts += list(hands.items())
    return native_models._assemble(parts, binds, 0, 119, material, True, native_models.LEON_ATLAS)


def build(disc, capture, tables, report, hide_smd=()):
    if (capture / 'extra-models.json').exists():
        raise ValueError('a capture with props would move Ashley off catalogue index 6')

    def hill_models(disc_, tables_, cloth_bind, material):
        out = base_models(disc_, tables_, cloth_bind, material)
        out[0] = leon_pl08(disc_, tables_, cloth_bind, material)
        st = {}
        texpak = (disc_ / 'tex.pak').read_bytes()
        count, idx = struct.unpack_from('<2I', texpak, 12)
        lookup = {(a, b) for a, b, _, _ in struct.iter_unpack('<4I', texpak[idx:idx + 16 * count])}
        out.append(ashley_model((disc_ / 'native/r11d/partner.re4nmr').read_bytes(), lookup, material, stats=st))
        report.update(leon=dict(costume='pl08 roles 0, 1, 9 over pl00 with its hair'), ashley=st, ashley_index=len(out) - 1)
        assert len(out) - 1 == ASHLEY_INDEX
        return out
    native_pack.models = hill_models
    if hide_smd:   # world placements of these scroll (SMD) ids left out (boss_pack.hidden_world)
        import tempfile, shutil
        from boss_pack import hidden_world
        tmp = Path(tempfile.mkdtemp())
        hdir, removed = hidden_world(disc / f'native/r{ROOM:x}', set(hide_smd), tmp)
        report.update(hidden=[list(r) for r in removed])
        whole = native_pack.whole_world
        native_pack.whole_world = lambda directory, material: whole(hdir, material)
        try:
            return native_pack.build(disc, capture, ROOM, tables)
        finally:
            shutil.rmtree(tmp)
    return native_pack.build(disc, capture, ROOM, tables)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('disc', type=Path); p.add_argument('capture', type=Path); p.add_argument('out', type=Path)
    p.add_argument('tables', type=Path); p.add_argument('--report', type=Path)
    p.add_argument('--hide-smd', type=lambda s: [int(x, 0) for x in s.split(',')], default=[])
    a = p.parse_args()
    rep = {}
    data = build(a.disc, a.capture, a.tables, rep, a.hide_smd)
    a.out.write_bytes(data)
    rep.update(bytes=len(data))
    print(json.dumps({k: v for k, v in rep.items() if k != 'ashley'} | {'ashley': {k: v for k, v in rep['ashley'].items() if k != 'slot_joint'}}))
    if a.report: a.report.write_text(json.dumps(rep, indent=1))
