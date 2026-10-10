#!/usr/bin/env python3
"""Turns a REL linked as an overlay section into a relocatable file the game loads at run time
(SUBSCREEN_OVL=1, tools/link.sh; loader: sscrn_bridge.cpp).

    gen_overlay.py <elf linked at A> <elf linked at B> <section> <A> <B> <out.ovl>

The two ELFs are the same link with only the overlay section's address changed. Every 32-bit
word of the overlay that differs between them by exactly B - A is an absolute pointer into the
overlay (a relocation); every other word must be identical. Anything else fails the build:
  - an overlay word that moved by another amount (a PC-relative reference across the boundary);
  - any difference in the rest of the image (the image holds a pointer into the overlay, which
    would dangle while the sub screen is closed).

Output, little endian: a 64-byte header (u32 words)
   0 magic 'RE4O'   1 version 1      2 image bytes    3 relocation count
   4 link address A 5 prolog        6 epilog         7 data  8 data_end  9 bss  10 bss_end
  11 pristine       (5-11: offsets from A)            12 FNV-1a of the image  13 of the relocations
then the image bytes, then the relocation offsets (u32, from the image start).
"""
import os
import struct
import subprocess
import sys
import tempfile

MAGIC = 0x4F344552  # "RE4O"


def binary(elf, args):
    with tempfile.NamedTemporaryFile(delete=False) as t:
        path = t.name
    try:
        subprocess.check_call(["sh-elf-objcopy", "-O", "binary"] + args + [elf, path])
        return open(path, "rb").read()
    finally:
        os.unlink(path)


def fnv(data):
    h = 2166136261
    for i in range(0, len(data), 4):
        h = ((h ^ struct.unpack_from("<I", data, i)[0]) * 16777619) & 0xFFFFFFFF
    return h


def symbols(elf):
    out = {}
    for line in subprocess.check_output(["sh-elf-nm", elf], text=True).splitlines():
        parts = line.split()
        if len(parts) == 3:
            out[parts[2]] = int(parts[0], 16)
    return out


def main():
    elf_a, elf_b, section, a, b, out = sys.argv[1:7]
    a, b = int(a, 0), int(b, 0)
    delta = (b - a) & 0xFFFFFFFF
    mod = section[len(".ovl_"):]
    img_a = binary(elf_a, ["-j", section])
    img_b = binary(elf_b, ["-j", section])
    if not img_a or len(img_a) != len(img_b) or len(img_a) % 4:
        sys.exit("gen_overlay: %s missing or sized differently (%d / %d)" % (section, len(img_a), len(img_b)))
    # The rest: every other overlay section is linked at the same address in both ELFs, but is left
    # out too (outside RAM: a binary dump across it would be mostly gap).
    drop = ["-R", ".ocram"]
    for line in subprocess.check_output(["sh-elf-objdump", "-h", elf_a], text=True).splitlines():
        f = line.split()
        if len(f) > 1 and f[1].startswith(".ovl_"):
            drop += ["-R", f[1]]
    rest_a = binary(elf_a, drop)
    rest_b = binary(elf_b, drop)
    if rest_a != rest_b:
        bad = [i for i in range(0, min(len(rest_a), len(rest_b)), 4) if rest_a[i:i + 4] != rest_b[i:i + 4]]
        sys.exit("gen_overlay: the image outside %s changes with its address (%d words, first at +0x%x): "
                 "something in the image points into the overlay" % (section, len(bad), bad[0] if bad else 0))
    relocs = []
    for i in range(0, len(img_a), 4):
        wa, wb = struct.unpack_from("<I", img_a, i)[0], struct.unpack_from("<I", img_b, i)[0]
        if wa == wb:
            continue
        if (wb - wa) & 0xFFFFFFFF != delta or not (a <= wa < a + len(img_a) + 1):
            sys.exit("gen_overlay: %s+0x%x %08x -> %08x is not an absolute pointer into the overlay" %
                     (section, i, wa, wb))
        relocs.append(i)
    sa = symbols(elf_a)
    names = ["_%s_prolog" % mod, "_%s_epilog" % mod] + \
            ["_re4dc_mod_%s_%s" % (mod, k) for k in ("data", "data_end", "bss", "bss_end", "pristine")]
    offs = []
    for n in names:
        v = sa.get(n)
        if v is None or not (a <= v <= a + len(img_a)):
            sys.exit("gen_overlay: %s not inside %s" % (n, section))
        offs.append(v - a)
    rel = b"".join(struct.pack("<I", r) for r in relocs)
    head = struct.pack("<16I", MAGIC, 1, len(img_a), len(relocs), a, *offs, fnv(img_a), fnv(rel), 0, 0)
    with open(out, "wb") as f:
        f.write(head + img_a + rel)
    print("gen_overlay: %s %u bytes, %u relocations, image outside it identical at both addresses -> %s" %
          (section, len(img_a), len(relocs), out))


if __name__ == "__main__":
    main()
