# Sealed menu-window traffic accounting

The frozen inventory pair remains a negative result: ON adds **102 low-level nonmusic requests and 168,032 requested bytes**. The restoration candidate stays disabled. This read-only audit explains the aggregate request/byte difference from source and retained evidence; it does not supply a new guest run or a per-request historical drive trace.

The 26 additional eager restores have 122,912 payload bytes and 3,744 header/descriptor bytes (26 times 144), for 126,656 stored member bytes. Their exact member hashes and source rows are preserved in the receipts. Real pack index ordinals joined to the logged ordered requests give 23 index-sector transitions in ON versus 3 in OFF: 20 additional 2,048-byte lookup streams, or 40,960 bytes. This transition count is derived from the complete retained request order and the real index.

The remaining 416 bytes follow the actual KOS read path. The selected `room_storage` compiler command uses a 16 KiB bounce with address offset 16, although the underlying buffer is aligned to 32. A streamed native member has a 48-byte header and a 96-byte descriptor: its payload starts 144 bytes into a sector-aligned member. The first read brings a 2,048-byte cache sector; the first 1,904 payload bytes are copied from that sector. That copy advances the initially misaligned destination onto a 32-byte boundary, so KOS then starts an aligned stream. Each selected member ends with an outstanding 16-byte portion: KOS requests a complete 32-byte tail. The final unused portion is 16 bytes per member, or 416 bytes total. Rounding every complete member to an optical sector would describe the wrong path.

Source-derived bytes therefore reconcile exactly:

| Component | Bytes |
|---|---:|
| Additional native texture payload | 122,912 |
| Additional header/descriptors | 3,744 |
| Final 32-byte stream overread | 416 |
| Additional index lookups | 40,960 |
| Total | 168,032 |

The actual retained generated KOS cache/read/seek functions are compiled unchanged into the host replay. Mock drive requests are counted using the game wrapper's semantics. It produces 26 additional header-sector calls, 28 bulk-stream requests, 28 32-byte tail-stream requests and 20 index-stream requests: 102. Two additional 18,432-byte payloads cross the 16 KiB storage chunk boundary; each contributes two requests beyond the smaller member pattern. The 22 distinct held-menu member headers are warmed first, disjoint from all restored members, so the 16-entry data-cache history is constrained rather than assumed empty for the return.

The replay's restoration subset is OFF 16 requests / 47,584 bytes and ON 118 requests / 215,616 bytes. Independently sampled return plateaus are OFF 59 / 135,648 and ON 161 / 303,680. Each arm therefore retains the same unassigned common return remainder: 43 requests / 88,064 bytes. The earlier held-menu interval is also identical in both arms: 130 requests / 2,095,168 bytes. The exact aggregate reconciliation is a consistency result; the old capture cannot uniquely label every individual drive call.

The request meter increments at the wrapped sector-read or stream-request entry, using the requested size, before success is known. Stream starts affect busy/block time but do not increment reads/bytes. Music-thread requests are separate; other nonmusic threads are included. Internal `__real_*` fallback attempts are not separately counted. These are neither distinct optical seeks nor a count of bytes actually consumed by textures. The observed 417,678 microsecond block-time difference is not attributed by this byte model.

## Exact inputs and limits

Frozen game source is b21116ec0cf2c984e9f49769a148373553bff00d, parent 892c10dd. Both arms use KOS_DISC_FIX=1. The authoritative source is the retained generated `obj/kosfix/fs_iso9660.c`, SHA256 500da02b87d0e0790585f9a3661abd487a2bde0bca0ff1126cb561277113a0bc, identical in OFF and ON. Their `_iso_read` symbols are each 824 bytes; complete ELF/program and symbol byte identities are in reconciliation.json. The current unpatched libkallisti archive is a different implementation and is not substituted for that input. Initial unpatched host-v1 evidence is retained as superseded.

Selected actual knobs include DISC_READ_FALLBACK=3, DISC_READ_METER=1, TEX_RESIDENT=1, TEX_PAYLOAD_CRC=0, TEX_PACK=1, TEX_PACK_WINDOW=0, STORAGE_BOUNCE_ALIGNED=0, IO_SERIAL=1, DISC_READ_LOG=0 and IO_PROBE=0. No second payload CRC pass or read-ahead pack window is invented.

Host replay uses source-level Package read sizes, mocked drive/file handles and real KOS read/cache/seek bodies. File directory lookups, background scheduling, real drive timing and errors are not replayed. DISC_READ_LOG and IO_PROBE were off, so per-call target paths/LBAs cannot be recovered independently. The pair is host-time matched, not frame-identical. No future visible-use need, Flycast rerun, release acceptance or physical Dreamcast acceptance follows. Entry.frame remains a preload/lookup timestamp as well as a draw-related field.

Run audit_window_traffic.py with `--evidence`, `--pack`, `--kos-source` pointing to the exact retained generated file, and a fresh `--output`. Inputs stay read-only; no game data is copied into the repository. The authoritative host replay is private window-traffic-host-v3.json; reconciliation.json pins its SHA and all sources/programs/assets/logs/counter plateaus.
