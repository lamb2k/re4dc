# Exact memory2158 ISO restoration

Source-only executor. No actual image has been opened, hashed, restored or allocated by this unit. It requires the essential actor ce034 file to have been independently restored first. It does not restore or remove that prerequisite, the bea image, old stage metadata, any delta or any case evidence.

The unchanged memory-archive2158/archive_core.py iter_restored stream and unchanged recovery-native-base validate_delta implementation replay the pinned original manifest. The exact retained source is ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad (1028911104 bytes); delta changed-blocks.bin is4532224 bytes, SHA9b1f021daf760930c83d819ce2c638c02181c3bd7087f1d09ad97f790b9c978e. Original metadata pins are in INPUTS.json. Target is the existing memory stage base/track03.iso:1028859904 bytes, e0860b747b84fb10edc2db7ee66d0e91b42479fd201d2c80305cd8bfc1ef013b. Old stage receipt fade104d remains untouched.

The default command prints the fixed source plan and does not examine images. Deliberate execution requires exact independent CLEAR review (restore_source_seal_sha256), this source seal pin and a fresh main resource receipt/hash. It takes the existing world-scratch23 integration tree lease and canonical package lease nonblocking. Main must serialize other actors, retire/archive unrelated images only under separate authority and admit the actual capacity first. This tool does not create a census or free space.

Admission reserves one target ISO plus256KiB metadata and the existing60MiB future guest: root projected_peak (already including the guest) plus ISO+metadata must fit16GiB; package_current_bytes plus ISO+metadata+guest must fit3758096384; C free must retain20468203520 plus all three reservations. Receipt age must be0..60s at allocation. During the admitted copy, the fixed leases and disk-floor/remaining-copy/future-guest checks remain held; this does not renew the admission timestamp.

The tool retains all parent-directory descriptors and source/blob descriptors. Replay uses /proc/self/fd/<held parent fd>/<fixed basename>, so the original immutable stream opens the anchored directory. Each stream guard compares retained source/blob identity with both DFD and literal named paths and checks every parent descriptor against its literal path. A replaced source, symlink, ancestor or parent rename refuses acceptance.

It creates exactly one exclusive .track03.restore-e086-r1.tmp in the literal target directory. The original stream verifies the complete source including truncated tail, blob and reconstructed target; a second independent hash reads every written candidate byte. Only then does publication hardlink the same verified inode to the previously absent literal track03.iso name, verify DFD/literal/current-writer identities and nlink2, unlink only the owned temporary name, then require nlink1 and final literal identity. Parent checks repeat before and after link/unlink. There is no os.replace, overwrite, second full image, automatic retry or deletion of an input. Any failure preserves the candidate/result and any link already created, marked unaccepted. No failed artifact is silently cleaned or relabeled.

Run in WSL only after final source review and fresh main resource admission:

```sh
python3 -B '/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/memory-restore2158-r1/restore.py' --execute --source-seal-sha256 SOURCE_SHA --review /absolute/restore-review.json --review-sha256 REVIEW_SHA --root-admission /absolute/resource.json --root-admission-sha256 RESOURCE_SHA
```

The sole new result is scratch23-2158baff-memory-q01/base/restore-e086-r1-result.json (bounded32KiB). A successful result establishes exact restored bytes, not game, memory, limiter, performance or guest qualification. Actual canonical1200 tests remain separate and unchanged.

Host checks use tiny temporary files only:

```sh
python3 -B -m unittest discover -s '/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/memory-restore2158-r1' -p test_restore.py -v
```

The parent-rename regression tests cover refusal before linking and after linking while retaining the same original directory handle. They do not run the production executor, perform a resource census or touch actual images.
