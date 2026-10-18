# Third-party notices

The project's own tools and documents are [CC0](LICENSE). The Dreamcast program also contains code from these
projects, each under its own licence. Their licence texts stay with the code, unchanged.

| Project | What the port uses | Licence | Where |
| --- | --- | --- | --- |
| [KallistiOS](https://github.com/KallistiOS/KallistiOS) (commit 804b3195, plus the port's patches) | the Dreamcast system library the program is linked with | KOS licence (new BSD style) | `port/dreamcast/patches/LICENSE.KOS`, `port/dreamcast/toolchain.lock` |
| [pl_mpeg](https://github.com/phoboslab/pl_mpeg) (commit c871f2be) | MPEG-1 video decoding for the cutscene movies | MIT | licence at the top of `port/dreamcast/game/third_party/pl_mpeg.h`; pin in `PL_MPEG_PIN.md` beside it |
| [SH4ZAM](https://github.com/gyrovorbis/sh4zam) (v0.9.1, commit 33fa4850) by Falco Girgis and SH4ZAM contributors; thanks to Bruceleeto, who measured the first SH4ZAM gains on his fork and brought it to the port | SH-4 matrix and trigonometry routines used by the renderer (GAME_SH4ZAM_RENDER_ONLY) | MIT (text below) | git submodule `port/dreamcast/game/third_party/sh4zam`, pinned to the upstream commit this repository records for it (`git submodule status`); its files are not copied into this repository |

## SH4ZAM licence

    MIT License

    Copyright (c) 2025, 2026 Falco Girgis and SH4ZAM Contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
