# Alternating failed index sectors: source characterization

The frozen source violates its documented per-failed-sector retry bound when two different index sectors fail between attempts. Its actual mechanism remembers only the **most recent** failed sector. No runtime repair or policy change is made by this unit; main owns that decision.

Source: `edfe8f1765fbbd418235537e7b2f0b3b6aeab25d`. The complete `texpack_index.inc` is compiled unchanged (SHA256 `64d725e6a34c2e368bc8a4e8796530232d1c2a94487015afcbed5be8b42a3e18`), along with the frozen payload helper. `receipt.json` binds source, fixture, compiler commands, process guards and all outputs.

The header documentation says: "A lookup's index sector that failed to read is re-read at most once per kRetryFrames"; `kRetryFrames` is30. `find()` instead gates only `s == bad_sector`, then overwrites `bad_sector` and `bad_until` on **every** failed lookup read. The declaration explicitly describes the last failed lookup, so the representation is clear. No documented exception authorizing a last-sector-only retry policy was found. This is a demonstrated mismatch between the broad documented guarantee and the narrower implementation, without assuming how often real media triggers it.

## Minimal counts

A and B are distinct failed index sectors0/1; H is healthy sector2. All scenarios begin after complete valid index initialization with H cached. Initialization/priming calls are excluded from the following counts.

| Lookups | A calls | B calls | H calls | Error logs |
| --- | ---: | ---: | ---: | ---: |
| A,B,A in one UI frame |2|1|0|3|
| A,H,B,H,A,H in one UI frame |2|1|3|3|
| A,H once per frame for30frames |1|0|1|1|
| A,B,H once per frame for30frames |30|30|30|60|
| A,B,H repeated30times in one frame |30|30|30|60|

These are **synthetic read_file_range calls**, not measured low-level KOS requests, drive transactions or bytes transferred. The documented bound permits at most one failed attempt for A and one for B within this30-frame interval absent a reset; the observed repeated pair makes60 failed attempts. The extra H reads are the correct consequence of failed reads invalidating the sole cache buffer before H is needed again. They are not evidence of a stale cached-buffer defect.

Exact sequence: A failure stores `bad_sector=A`. B differs, so B reads and fails, replacing the slot with B. A now differs again and rereads in the same frame. Repeating only the latest B is correctly held until its deadline; a subsequent A failure displaces that hold. A successful healthy-sector read does not displace the failed-sector slot. The separate one-failure control demonstrates that existing single-sector behavior still meets the30-frame bound.

## Guard and recovery controls

`RE4DC_TEX_PAYLOAD_RETRY=0` and1 both reproduce these counts for injected I/O failures and first-key mismatch refusal. With the guard1, changed **non-first-row** bytes that preserve the first key trigger the enabled sector CRC check, and two such CRC refusals reproduce the same counts. A mixed I/O/CRC pair also reproduces them. With guard0, the non-first-row mutation is not CRC-checked: the unmodified requested first-row keys still return found,90 reads/0errors. That is an explicit existing guard-OFF control, not an adoption claim or a new diagnosis of default-path corruption.

The fixture checks that an attempted failed read leaves `cached=~0U` and no offset/size/ordinal published. A throttled failure may preserve a different, valid cached sector. Healthy lookups always return their original offset/size and enabled ordinal. It also checks the existing retry at frame30, frame29 hold, recovery after a room reset, and retry arithmetic across UINT wrap. These controls address the index failure policy only; they do not establish thread/TA/owner lifetime safety.

**UBSan passes3113 assertions OFF and6764 ON.** Both builds set `RE4DC_TEX_PACK_FAULT=0`; deterministic post-init fault injection happens in the synthetic reader, allowing complete valid initialization first. The complete real51-sector sorted index is validated by the unchanged source before injection. No mocked find implementation is used.

## Exact index input and resource limits

The reader uses the fresh106496-byte header/index prefix of the retained original6501-member pack, virtual file size156254208. Fresh prefix SHA256 `5cb0097cb28b03c30fbf0b59443f659420f7ee4be247e6ca2ad48d730cb21b40`. The previously sealed whole-pack SHA256 is `18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef`; this unit rereads/hashes the prefix only, not the full pack. Package payload bytes are not read or copied. Original index bytes remain private.

Latest private outputs: `C:/Flycast-Evidence/re4-dreamcast/cache21-payload-20261021/index-backoff-host-v2`, approximately771KiB including two small host executables and the private prefix. Compile jobs serialize through the shared buildslot. Fresh disk floors,55-second owned PID/process-group identity guards, bounded logs and a20MiB output cap are enforced. Earlier v1 is preserved; v2 uses the final canonical runner bytes and produces identical counts.

The earlier21,898 payload-policy assertions and actual find/load fixture showing60 index reads in both arms are separate evidence, unchanged. This unit does not replace those results or establish a package-level performance benefit. No runtime/shared edits, SH4 build, full program, stage, guest, release check or physical Dreamcast acceptance was performed. Guards remain default-off; the negative window-restoration candidate remains disabled.

## Reproduce

```sh
python3 run.py --source /root/probe/codex-cache21-integration-next \
  --ref edfe8f1765fbbd418235537e7b2f0b3b6aeab25d \
  --pack /root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak \
  --out /path/to/fresh-output
```
