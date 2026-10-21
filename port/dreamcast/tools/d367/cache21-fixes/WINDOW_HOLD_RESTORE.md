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
