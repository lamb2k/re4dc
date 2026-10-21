# Unchanged-program boss and QA regression tools

These tools inspect a separately verified QA disc. They do not build, stage,
patch assets, edit the guest, enable invincibility, damage actors or force
encounter phases. Controller input targets only windows of the one owned
Flycast process. The existing fullplay runner is copied privately and
SHA256-pinned; shared helper files remain unchanged.

`run_unchanged.py` adds full raw trigger bindings (F/V) and the normal left
stick (I/K/J/L) to the runner's existing keyboard controls. It refuses a
busy release window, yields its guest when release pressure rises, and
terminates only its verified evidence executable at a48-second hard limit.
Use the project's trace_lock.sh around the guest invocation. The global
limit is16 and this lane owns at most one guest. A host guard termination
or withheld controller input is not a game failure.

When `--binding` and `--layout` are supplied, the source track is hashed
again before launch. Its hash and log-symbol offsets must agree with the
binding receipt. The receipt must bind the disc program to the actual ELF's
extracted binary; `dwarf_layout.py` exports the selected structures from
that same ELF with pyelftools0.32. Independent ELF/raw-byte verification is
required before creating the receipt. Layouts from another ELF are refused.

`observe.py` uses Windows ReadProcessMemory only, validates the owned
executable path and bounds all guest reads to main RAM. It writes separate
JSONL samples of game frame, room/mode/stop flags, player routine/position,
mapped input, QA safe ticks, event/subscreen gates, and actual Mendez
manager entries. Reads are non-atomic and do not stop or advance the game.
Normal mapped controls may be stale while the raw QA menu holds its loop.

The QA shortcut waits for a read-only sample of30 safe ticks before it is
posted. `--require-mendez-for-pause` withholds Start unless an actual alive
Mendez actor is present. `--event-shots` records actual framebuffer images
before Start and after a QA shortcut, plus the most recent sampled source
context. Capture times and source context are approximate, not an exact
simulation-tick or Dreamcast performance certificate.

The mandatory run arguments are `--runner`, `--runner-sha256`, `--disc`,
`--cap` (new path), `--keys`, `--syms` and `--name`. Binding receipt fields:
`input_track03_sha256`, `elf_sha256`, `disc_program_sha256`,
`elf_binary_sha256`, and `symbols` containing main-RAM addresses for
`logbuf`, `head`, `stage`, `pG`, `pPL`, `EmMgr`, `qa_frames`, `qa_flags`,
`Pad_data`, `Joy`, `SceSys` and `SubScreenWk`. `disc_track03_name` defaults
to `track03.bin`. The layout comes from the exact preserved ELF, not from
source comments or an unrelated symbols file.

See [QA_REOPEN.md](QA_REOPEN.md) for the confirmed original QA shortcut
problem, the narrow source repair and remaining target gates. Private
runtime evidence lives under `feedback21-boss-qa-20261021` in the normal
Flycast evidence root. The completed texture work remains unchanged.
