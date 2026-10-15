# Third-party notices

## SH4ZAM

The Dreamcast port uses SH4ZAM (https://github.com/gyrovorbis/sh4zam), the SH4 maths library by Falco Girgis and
SH4ZAM contributors, as a kos-ports dependency: it is installed by kos-ports' sh4zam port (`make install` in
`kos-ports/sh4zam`) at the commits pinned in `port/dreamcast/toolchain.lock` (`KOS_PORTS_SHA`, `SH4ZAM_SHA`), and is not
copied into this repository. Thanks to Bruceleeto, who measured the first SH4ZAM gains on his fork and brought it to the port.

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
