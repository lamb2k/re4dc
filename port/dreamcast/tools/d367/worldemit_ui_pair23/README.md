# Private PS2 Mendez pair candidate

The Mendez failure names a model material composite, not a HUD widget. The retained r11f registry has the two requested tokens in source-fact texture rows 0/1 of em35 TPL5. Those facts authenticate the source matching contract; they do not establish that the corresponding packaged pixels are PS2. The historical inventory's `PS2-native` label cannot supply that missing ancestry.

The actual PS2 USA BIO4DAT member em35.dat has the matching explicit material: BIN4 full body and BIN7 upper body each contain one flag4/diffuse0/opacity1 material, using TPL5 images0/1 at128x128. BIN6 extra and BIN8 legs have no opacity materials. The image is hair-card artwork; a precise on-model placement still requires runtime observation. This helper reads only that PS2 member. No GameCube pixel decoder or archive is used by candidate preparation.

`prepare_pair.py` pins the exact PS2 member and TPL hashes, verifies the material rows, descriptor shape and mask levels, and requires two independent GS/JL unswizzle implementations to agree. It combines PS2 RGB0 with opacity1's authored grayscale intensity using the existing PS2 object mask recipe (n*16 -> n*17), then writes a canonical full-body-CRC twiddled ARGB4444 native package. Source alpha in the opacity palette is deliberately not substituted for intensity. No resize, inferred matching, GC fallback, VQ or fake pixels are permitted.

The requested colour/mask tokens remain the runtime lookup names. The candidate receipt independently records the PS2 decoded-pixel and emitted-package SHA256 values; the tokens themselves must never be presented as PS2 provenance. Source material correspondence is established. Reference-mesh UV parity, target upload, VRAM, look and gameplay acceptance remain open.

Default is read-only audit:

```sh
python3 -B prepare_pair.py --ps2-iso '/path/to/PS2 USA.iso'
```

Private generation requires an explicit, new destination:

```sh
python3 -B prepare_pair.py --ps2-iso '/path/to/PS2 USA.iso' --prepare-private '/private/new-candidate'
```

The output is one package, three PS2-only preview PNGs, candidate.json and a local-pack.json manifest. `MENDEZ_PS2_PAIR23_PRIVATE` is a local manifest option with default0; it is not registered in the production stager or DATA. No original file is replaced, and an existing destination is refused. A failed output is not production input. Root must review the source/receipt and admit a separate private stage before any target run. User look approval is required before production enablement. Original control and candidate failures remain preserved; these host controls do not clear TEXCHK or Mendez.

```sh
python3 -B -m unittest -v test_prepare_pair
```

Nine controls exercise material routing refusals, intensity/alpha distinction, malformed mask/shape, exact native words/CRC/layout without GX decoding, pixel count, exact member rejection before parsing, runtime pair token order, audit-only behavior and exclusive output. Actual-member audit separately checks the pinned PS2 material and both unswizzlers. No SDK, guest or performance evidence is produced.
