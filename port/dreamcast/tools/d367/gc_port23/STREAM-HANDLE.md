# Diagnostic stream handle reuse

Frozen parent aab201cea remains unchanged. The existing default-off GC_ASSET_GATE block now fingerprints the already-open aica_str.dat descriptor before str_main enters its sole stream loop. It saves the actual file offset, seeks to0, hashes the entire container using the existing fingerprint routine, and requires exact offset restoration before publishing the source identity. No catalog check or hash coverage is relaxed; healthy playback starts at its former position. If restoration fails, it reports unresolved, closes its own descriptor and returns the existing silent-stream failure. Failed bookmark/hash/size/seek remain unresolved rather than fabricating a source identity.

This removes a confirmed second transient open, not a proven leak. The entry-only census has two additional filesystem-open-associated blocks (+368 requested bytes), but does not establish their lifetime, owner, or original KOS floor cause. Original ON4000/4016 failures remain.

45 host fake-IO cases exercise the actual extracted str_index_load function, including short/invalid/large headers, exact full-container reads, saved positions2048/4096/8192, bookmark/seek/read/restore failures and no extra open/close. Existing knob-off function preprocessing is identical. These checks do not establish target/ELF identity, guest memory, audio output, steady ownership, physical acceptance or a performance gain.

Next: independent source review, selected target/full QA build, OFF identity and repeat the original matched memory gates before integration. No recipe or asset edit.
