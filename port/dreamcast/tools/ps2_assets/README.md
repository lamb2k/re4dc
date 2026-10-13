# Offline PS2 world helpers

These are the previously used conversion helpers, brought into the repository so
`ps2_room_r4im.py` does not import files from a maintainer's private work directory.
No game data is included. See [the build guide](../../docs/PS2_ASSET_BUILD.md).

| File | Provenance | Retained behavior |
| --- | --- | --- |
| `scenario.py` | September 2026 world agent, `ps2_tree_materials.py` | OBJ/material, SMD and SMX readers |
| `texture.py` | September 2026 character prototype, `g_re4tex.py` | RE4DCTX decode, twiddle and 16-bit pixel helpers |
| `light.py` | Original-world reference, `ow_extract.py` | `gx_light`, used only during offline conversion |
| `vq.py` | World agent `c1/tools/vq_review.py` | Float32 nearest-centre selection, unchanged |
| `tpl.py` | World agent `ps2_tpl_decode.py` | Existing JADERLINK decoder, PNG writer and TPL parser |

Only the used functions are retained. The TPL helper uses the existing Python port
of JADERLINK's interlace decoder from
[RE4-PS2-TPL-TOOL](https://github.com/JADERLINK/RE4-PS2-TPL-TOOL), B.1.1.1.
It is MIT-licensed, copyright 2023 JADERLINK; see
[LICENSE-JADERLINK.txt](LICENSE-JADERLINK.txt). The alternate GS-model diagnostic
decoder and its tables are not included. Both retained rooms' complete TPLs,
including mip levels, were compared against that earlier decoder: 166 images with
identical dimensions, RGBA pixels and decode statistics.

Original source-file SHA-256 values, for migration provenance:

```text
ps2_tree_materials.py  78a1a7e5e08ec39752740df38591870de49694e2ee0d18e4cab75700e037775d
g_re4tex.py            58d8083ceb939515337bda293b56873bcd5282b4b28736fdbf8998e48d164920
ow_extract.py         d9bdffe9ae7abda3b0c863715c99d8e4df500d5bc9ae8e0eda81cf95da0458d9
vq_review.py          22368b8dace8554a7646c859ce9f8656bd0fb72972ae9716c022b0fa23dbd533
```

The DATUDAS and SMD executables are downloaded from pinned upstream release ZIPs;
they are not committed. Their own licenses and credits remain in the tool cache.
`worlds.json` pins their release and executable hashes as well as the disc revision
and the converter settings. Additional rooms require their accepted recipe and
source/runtime comparison before they join this profile.
