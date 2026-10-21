# Opt-in native mipmaps

Native-package mode in tools/vq_export.py adds lower mip levels to an existing
square 16-bit full-codebook VQ package. It retains the original 2048-byte
codebook, largest-level indices, dimensions, material identity, source flags and
CRC convention. Existing base-level texels therefore decode identically.

This is an offline candidate path. It changes no runtime defaults. The existing
CAST_MIPMAP reader path must be enabled when these candidate packages are used.

## One package

    python port/dreamcast/tools/vq_export.py --native-package input.re4tex --package control.re4tex
    python port/dreamcast/tools/vq_export.py --native-package input.re4tex --package candidate.re4tex --add-mipmaps

Without --add-mipmaps the output is byte-identical to the input. New outputs are
exclusive: existing files are never overwritten. Existing encoded-VQ exporter
modes keep their previous behavior.

Input must have one version-2 native descriptor, square power-of-two dimensions
8 through 1024, RGB565/ARGB1555/ARGB4444, and a complete 256-vector VQ codebook.
Already mipmapped packages return unchanged. Rectangles, palettes,
linear/twiddled texels and runtime top-drop representations are refused by this
initial path; they need their own layout contract.

Lower levels use integer premultiplied color box filtering and nearest vectors
from the existing codebook. The optional NumPy engine is an offline speed aid;
its result is byte-identical to pure Python, including ties. No dependency is
required. Lower levels are lossy and need a same-scene visual review before
adoption. No original base texel is re-encoded.

The layout follows primary KOS pvrtex: smallest level first, Morton ordered VQ
indices, TL/BL/TR/BR vectors. The 1x1 level uses the fourth expanded-vector pixel.
Independent tests use the pinned pvrtex decoder, not a second copy of the new
encoder's layout logic.

## Checks

    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_vq.py -v
    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_runtime.py -v
    python -m unittest discover -s port/dreamcast/tests -p test_convert_tpl.py -v

The runtime test host-compiles the existing Package reader with CAST_MIPMAP
off/on. It checks all three formats, TCW VQ/mipmap bits, base admission,
truncated-chain refusal and the existing release streamed-CRC behavior.
It does not build the game or establish rendering or frame time.

Optional independent decoding is enabled with
MIPMAP_PVRTEX_ORACLE=/absolute/path/to/libmipmap_pvrtex_oracle.so. Build that host
library from tests/fixtures/mipmap_pvrtex_oracle.c and pinned KOS
utils/pvrtex/{pvr_texture_decoder.c,pvr_texture.c,mycommon.c}, using the pvrtex
include directory and -lm. No codec sources or binaries are duplicated here.

## Implementation checkpoint, 2026-10-21

At integration source 54cef5d1, the VQ suite passed on WSL using the independent
decoder (one NumPy check skipped), and on Windows with NumPy 2.5.3 (one Linux
decoder check skipped). Existing converter suite: 16/16. Actual reader: 4/4.
No game build, master, emulator, physical console, timing or look acceptance is
implied by these host checks.

The first intended private selection is the r103 farm's 15 compatible keys.
Payload/allocation deltas, precedence and unchanged archive members must be
checked against its exact release input before staging. Private source assets
and generated packages never belong in this repository.
