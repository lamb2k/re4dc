# Camera diagnostic qualification

Frozen runtime source: c2f0d82e95050a708d0b977f94fad34890cbc279 on integration fb254e82.
This follow-up commits only exact helper source and qualification metadata.

Independent source/host review passed 256 actual-logger vectors, argument mutants and malformed-record controls. The actual normal OFF target main raw image is 49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b, byte-identical to integration, with all 14 overlays identical. Recipe and original assets are unchanged.

The camera diagnostic uses PS2_PVS=1/default2 (no visibility cuts), batching0 to preserve the existing incompatibility guard, and explicit limited console mode. It is not a performance comparison. Actual owned guest PID51692 completed in42.921seconds under exact55. The complete original record set contains616 rows, frames182..797, with all six viewport words. The43-frame offline sample is500..794 stride7. The legacy text is explicitly derived from complete words; CRLF is normalized, no missing bit is inferred.

The original R1 full camera is refused because the actual256-byte logger truncated its last viewport word/newline. Its bounded observation and context pictures remain separately retained. R2 both held pictures show Leon, forest and HUD and were stable across reads; this does not establish sampled full actor/runtime/presented-frame identity or hardware speed.

Actual programmes, original assets, media, screenshots and raw logs remain private under C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/restrip23-fb254/root-forest-camera{-v2}. This unit makes no full release, physical acceptance, production culling or recipe enablement claim.
