# Contributing

**This page covers the GameCube decompilation. The one rule: the bytes do not change.**

- **Working on the Dreamcast port?** Read [port/dreamcast/CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md)
  instead. Clone with `--recurse-submodules` (the port's SH4ZAM maths library is a submodule).
- **Art or model-reduction help for Dreamcast?** Start with the
  [artist contribution guide](port/dreamcast/docs/CONTRIBUTING-ART.md).
- **Your own program on a test disc:** test releases ship a standard GD-ROM image (section 8 of that page), and
  `port/dreamcast/tools/swap-program.py` puts your program on it.
- **State of the tree:** complete. Every unit compiles to the original bytes. Work now is readability (names,
  comments, notes) and tooling.

## Build

Follow "Building" in [docs/DECOMPILATION.md](docs/DECOMPILATION.md#building).

- **You need** the native SN GCC (built once from SN's GPL source drop) and your own images of the debug discs in
  `orig/G4BE08/`.
- **First build:** `python3 configure.py && ninja` builds and verifies.
- **After that:** run `ninja` only. It reruns `configure.py` itself when a config file changes.

## Verify

Three checks. A change is done when all three pass on a clean rebuild.

1. Byte identity of the binaries:

   ```sh
   find build/G4BE08 -path '*/obj/*' -prune -o -name '*.o' -print | xargs rm -f
   ninja
   build/tools/dtk shasum -c config/G4BE08/build.sha1
   ```

   Every line must be `OK`; the number of lines is `wc -l < config/G4BE08/build.sha1` (one per binary
   your discs provide). The clean rebuild matters: the ProDG compile rule has no dependency file, so an
   incremental `ninja` after a header edit can leave stale objects in place.

2. One unit, while you work on it: `python3 tools/bytecmp.py <mod>/<unit>` must say `IDENTICAL`
   (`game/item`, `em10/em10`, `lib/adx_amp`). `python3 tools/fdiff.py <mod>/<unit> <symbol>` shows the
   side-by-side for one function when it does not.

3. No instruction from an asm template: `python3 tools/asmcheck.py --all` must report the same total and
   the same per-unit hits as before your change (the hardware kernels listed in
   [docs/DECOMPILATION.md](docs/DECOMPILATION.md#what-matching-means-here), "What matching means here"). A single unit: `python3 tools/asmcheck.py <mod>/<unit>`.

## Working on a unit

**Read `docs/matching.md` before changing a function's body.** Most differences you can produce by
reformulating C have a known cause and a known non-asm fix.

- **DOL units:** "Workflow for one unit (`game/foo`)".
- **REL units:** "Workflow for one module unit" under "REL modules".
- **Rules the tree follows:** "Conventions".
- **Lever catalogue:** maps a byte difference to the compiler mechanism behind it and the source shape that
  reproduces it.
- **Try a variant fast:** `tools/research/kit/variant.sh <unit> <variant-src> [FUNC]` compiles a variant of one
  unit and judges it without touching `build/` (about a second per variant).

## Rules

- **Bytes never change.** Not for a rename, not for a comment, not for a refactor. The clean rebuild
  and `dtk shasum` are the judge; `bytecmp.py IDENTICAL` per unit is the working check.
- **No asm that emits an instruction.** The only inline assembly allowed is what the vendor also had to
  write in assembly (paired-single, GQR, cache, SPR, the exception handler) and the codeless MWCC pins.
  Every other register or schedule difference is steered from C, tagged `// COMPILER-DIFF: <n>` with the
  mechanism, and the tag's mechanism is written up in `docs/matching.md` or `docs/research/`.
  `asmcheck.py` enforces it. No `.s` bodies for functions the vendor wrote in C.
- **Names.** `docs/naming.md` says where every class of name comes from. Vendor names (from the symbol
  files or the PS2 debug symbols) keep the vendor's spelling. New names follow the surrounding struct.
  Placeholders `xNN`/`pad_NN` are renamed only with evidence (below).
- **`#line` directives and `// COMPILER-DIFF:` tags** stay where they are. Both are load-bearing;
  `docs/naming.md` explains each.
- **Notes.** Per-unit observations go in `docs/unit-notes.md`; a compiler mechanism you worked out, with
  the evidence, goes in `docs/research/` (one `### ` section, so the lever catalogue can cite it by title);
  the conventions and the catalogue live in `docs/matching.md`. Source comments say what the code does
  and, at a tag, which mechanism it steers; the long argument goes in the docs.
- **Formatting.** New game code follows `.clang-format` (4-space indent, function brace on its own line,
  `T* x`, 110 columns). Do not run the formatter over existing files: a whitespace-only diff across half a
  million lines hides real changes and gains nothing. The vendor-style `src/lib/` sources (tabs) stay as
  they are.
- **Commit messages.** One line, factual, present or past tense, what changed and that bytes are
  unchanged when that is the point: `em10: name the Em10Work motion tables from the PS2 symbols (bytes
  unchanged)`. No trailers, no signatures.

## Proposing a rename

Open an issue with the "Struct or field name" template or send a PR. Either way the rename needs
evidence, and the class of evidence is stated:

- **PS2 debug symbols**: `python3 tools/ps2sym.py --struct <Name>` shows the field aligned to a PS2 field
  with its confidence. Confidence 1.00 with a name match on the neighbours is enough on its own. Lower
  confidence needs a second argument (a use site whose meaning agrees).
- **Usage**: the function(s) that read and write the field, what they do with it, and why that fixes the
  meaning. Quote the file and function, not line numbers (they move). The new name follows the
  surrounding struct's spelling. Say in the field's line comment which use the name was taken from.
- **Another vendor artefact** (a debug menu string, a format string, a file format spec): quote it.

A rename PR changes the declaration and its use sites, nothing else in those files, and passes the
clean rebuild with every `OK`. The rename tool (`ps2sym.py --apply`, `--fix-errors`) follows the
compiler's error list rather than a text search; do the same, or check every hit by hand. A name that
also appears in a mangled symbol (`config/G4BE08/sym_map.tsv`) cannot change: the link would fail.

## Pull requests

- One topic per PR (a rename set, a doc, a tool fix).
- The description states what changed and how it was verified. For a source change: the clean rebuild
  command above, every line `OK`, and `asmcheck.py --all` unchanged.
- No generated files, no `build/`, no `orig/`.
