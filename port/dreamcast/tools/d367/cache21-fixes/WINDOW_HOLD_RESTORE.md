# Remember texture-window evictions during a sub screen hold

Base: current integration `54cef5d1560c41d074beee05ffa1ecd38f2ee642`, with the
independent readEm repair `a3727579` already committed. This change needs no
six-fix or d4 import. The actual `movie_window_release`, `close_entry`,
`vram_claim`, hold and unclaim bodies are identical before this change in
published Test21 `fe0efcdd`, current integration and retained six-fix `d4a3b31f`.
Receipts pin those exact helper identities. Current-vs-Test21 native_ui changes
are 23 additive scenery lines outside this path; sscrn_bridge is unchanged.

The ordinary `load()` eviction path calls `RE4DC_HOLD_EVICTED` before closing an
upload. `movie_window_release()` omits it. The same helper also releases windows
for fragmented texture uploads during a packed inventory hold, so those entries
are absent from the remembered set when the inventory closes. The root audit
observed such window evictions on its retained d4 inventory run; this component
does not provide a new gameplay reproduction or measured I/O reduction.

`SS_WINDOW_HOLD_RESTORE=1` adds that existing hold note immediately before the
window closes each selected entry. Default is zero. It requires the existing
`SS_HOLD_RESTORE=1 MOVIE_WINDOW=1 TEX_RESIDENT=1` configuration. There is no new
journal, allocation, cache size, selection rule or extra preload policy. The
existing 60-frame eligibility rule, 64-key bound and dropped counter remain.
An entry owning several VRAM blocks is still closed and remembered once.

The existing restore pass still intersects remembered keys with its resident
preload picks. Remembering a key does not guarantee that it is selected or loaded.
Other menu-file reads, returning-world keys outside that list and working-set
budget questions remain with root. This hook alone does not establish a read-quiet
return, generic reset safety or complete texture residency.

## Actual-source host checks

`test_window_hold.py` reuses the existing native-UI extraction helper from
`test_movie_world_arena.py`. It compiles the actual helper bodies, actual Key/Entry
declarations, existing hold macro and real `TextureLeases` class under ASan and
UBSan. Package close, GPU fences, VRAM snapshots and allocation probes are host
boundary adapters. A package-close observer verifies that real entry retirement
revokes leases and that the note is present before that boundary. This is not a
physical PVR fence or target ABI test.

Baseline, disabled and enabled arms each pass 26 cases; hold-disabled passes
25. Cases include active/inactive and nested holds; ages 59/60/61; fragment ages
29/30; multiple blocks per entry; frame, real actor-lease and core pins; cheapest
window and opaque-block rejection; actual normal/movie claim callers; movie
fallback and refused-fence control; and 65 victims under the unchanged 64-key
cap. Only enabled remembers eligible window victims. Close, claim, hold and
unclaim bodies, plus the four fragment/movie/reserve call statements, are
verified unchanged. No source evaluator, drawing or source-state policy changes.

```
python3 port/dreamcast/tools/d367/cache21-fixes/test_window_hold.py --out /root/probe/<owned-new-output>
```

## Actual SH-4 object checks

`qualify_window_hold_sh4.py` uses actual Make commands and generated prerequisite
headers for the whole native_ui unit with the D349/PS2 frame owner and the
existing movie/fragment/hold paths enabled. Baseline Make and source are exported
from `a3727579`. Both source snapshots share a compile path; a quote-include path
restores native_ui's normal source-directory header lookup. Commands, flags,
generated headers, unstripped objects and strip-debug comparisons are retained.

| Arm | Stripped native_ui.o SHA-256 | Text / data / BSS bytes |
| --- | --- | --- |
| Exact baseline and disabled | `965f482a0ab050e805191508f6aba3ad0fbf85f3f76e805d9063bdf4b30c9c81` | 33404 / 30740 / 43849 |
| Enabled | `f3e7471f9ca08f8ff056c5143a643c4adde581ab34dae6b71bfd98a8f26a8444` | 33500 / 30740 / 43849 |

Enabled adds 96 text bytes; data/BSS are unchanged. No performance claim follows
from object size. Make rejects values 2/-1/yes and missing prerequisites. Small
object preflight/stop guards remain 16 GiB plus 128/64 MiB; full build guards are
unchanged. With the pinned KOS d367 environment sourced:

```
python3 port/dreamcast/tools/d367/cache21-fixes/qualify_window_hold_sh4.py --out /root/probe/<owned-new-output>
```

The committed receipts are `window-hold-host-receipt.json` and
`window-hold-sh4-receipt.json`. Raw proof is mirrored under
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/window-hold`.
Earlier unsupported minimal-flag attempts remain preserved separately and are
not acceptance evidence. This is source/object qualification only: no full
linked-program/overlay build, stage, guest, screenshot, hardware, recipe enable,
release, issue or SD action ran. Root owns chosen-candidate integration and
gameplay qualification; Claude alone merges production and publishes.

## October 21 matched inventory result: disabled

Main subsequently qualified current source b21116ec0 on integration892c10dd.
Both full builds finished, and OFF matches the retained QA program and all14
overlays. ON preserves all1,728 unrelated files. The ordinary-input inventory
pair has one actual menu cycle per arm, no guest errors and no log overruns.
Its matched host-time interval adds102 low-level nonmusic requests and168,032
bytes with the candidate enabled. This is a negative traffic result. Keep
SS_WINDOW_HOLD_RESTORE disabled; no recipe adoption or performance claim.

The retained logs show exactly26 additional eager restored keys with122,912
upload bytes, matching the26-entry/122,912-byte window release. OFF opens none
of those26 keys later in its captured return tail. This does not prove no
future demand from a different camera or path, and upload bytes are not added
to drive counters. No counterfactual saving is derived from this attribution.

Main inspected both returned-room screenshots. They show the ordinary room;
this is bounded visual evidence, not a source-tick or whole-scene equivalence
gate. The raw global-prefix bytes in the old observer are unvalidated and do
not establish game mode. Low-level requests are not physical optical seeks.
Flycast blocked time and screenshots do not establish console performance.

The eligibility contract needs further work: Entry.frame is written by resident
preload selection, successful preloads and ordinary unpinned lookups as well as
scene commitment. The hold rule therefore cannot treat that shared field as
exclusively the last visible draw. Simply restoring the larger journal fixes
bookkeeping coverage while eagerly reloading data; it is not a cache policy
improvement. Preserve explicit owner/lease/fence and memory limits when tracing
actual pre-hold demand. Do not replace this result with a source-only estimate.

Reproduce attribution without a guest using analyze_window_demand.py with
--evidence pointing to the sealed cache21-window-20261021 directory, --source
pointing to this native_ui.cpp, and --output pointing to a new private file.
The tool hashes the complete source/logs and original pair receipt, labels
cold/menu/restore/tail opens, and preserves existing outputs. Raw key lists and
logs remain in private evidence. Broader menu/movie/Continue/resource and
physical Dreamcast gates remain open.
The optional --pack argument hashes the exact original archive and reads only
selected members. The recovered original pack18fcee1149 contains126,656 stored
member bytes for these26 keys, of which122,912 are texture payload. This is
asset size attribution; it does not account for all168,032 additional measured
drive bytes or102 low-level requests. Metadata, validation, filesystem traffic
and replacement/fragmentation effects must be traced before attributing every
request to a package.
