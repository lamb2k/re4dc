Runtime04 is a new read-only observer namespace for exact source 004cf224, raw
a58579b8 and ELF e08c9abc. It leaves observer.py 694b, PhaseLatch 8deb, runtime03
bindings and every retained guest capture unchanged. It does not start a guest.

Future controller invocation, only after root allocates coverage:

    python observer04.py --cap <fresh-owned-capture> --plan <candidate-plan-01> --seconds 41

The controller must preserve its PID/start/executable and exact image receipt,
fresh userdata/cold clock origin, 41-second inner / 47.5-second absolute process
limit, 60 MB total capture bound, disk floors and global resource ownership.
This observer adds read/query access only. It does not write guest memory, use
GDB, suspend threads, replay input, load/save states or alter game programmes.

Before process attach, all four runtime source files, the exact plan and selected
inputs, corrected scene layout, full linked-ELF paths, phase contract and coverage
contract must match binding hashes. The exact ELF audit resolves promoted fields,
Entry[448] and same-name/same-size phase symbols by CU/type/DIE/address, including
all 19 192-byte completed-frame members and actual 4-byte target pointers.

Each scalar sample requires identical pre/post completed nonzero even sequence,
current UI/completed frame, source Frame_cnt plus actual accumulated skipped
frames, ordinary Rno0/flags, SndWatcher and PROCESS CPU cursor, zero_tick and all
source pointers. Every body read is reread and byte-compared. Tables have their
own independent full latch and bounded read window; their failures never supply
replacement scalar rows. The default read window is at most 80 ms, each read is
at most 100352 bytes, JSONL is capped at 3.5 MB with summary reserve. Startup and
invalid samples wait with reasons, never imply death. Host read durations use
perf_counter; read deadlines use monotonic consistently.

Runtime04 does not collect a SQ header in this completed-state channel because
direct_open must be zero. Existing runtime03 minimum-header observations remain
separate; no missing sample proves nonuse. Typed tables are a partial RAM/VRAM
view, not allocator high water, net saving, all-key vertices or raster proof.

First future guest is coverage-only. Require every completed source state
240..360, including the predecessor of 241, and zero differing accepted variants.
Preserve all attempts/rejections/variants, with no matching-row selection,
sliding window or tolerance. Exact paired player/active camera/controller camera,
life/room/ordinary controls, source/phase/counters and rendering/presentation
lineage remain additional gates. Render uses the prior source state; a completed
update sample is not proof of the displayed pose or its texture binding.

Current C assets also fail independent behavioral controls: remapped R4PW CRC
versus old R4TC expected CRC falls back to classes=other, and stale R4ID CRC
produces ids=header placements=0 under the frozen TRANS_POLICY3/DYNAMIC1 knobs.
Rectangle owns the source-qualified CRC-consumer repair plan. No B/C comparison
can be accepted on the current assets even if phase coverage passes. This tool
does not edit those assets. Prior strict B01/C03 47/120 mismatch and all admission
reviews are retained; neither a speedup nor physical Dreamcast acceptance follows.
