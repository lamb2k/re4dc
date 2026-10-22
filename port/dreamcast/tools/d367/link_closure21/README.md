# Future compiler/link tool closure

This optional offline helper discovers and checks a tool closure. It never compiles,
links, renames an object, or changes a recipe. Existing 650 programme artifacts stay
held because their unit omitted four tool prehashes. This source snapshot cannot
supply those missing historical hashes.

`tool_closure.py capture` uses fixed read-only driver queries for collect2, ld,
lto-wrapper, lto1, cc1, cc1plus and as. It binds collect2, the LTO wrapper and the
shared plugin to the actual GCC `-###` record. The installed driver returns the
unresolved basename for `-print-file-name=liblto_plugin.so`; the helper records that
fact and requires the absolute plugin selected by the actual driver log. It never
guesses a plugin search result.

Pins include aliases and their resolved target, byte length, SHA256 and mode.
Optional explicit tools cover wrappers, binutils, the shell, Python, scramble and
strace. The helper also pins their resolved host loader/library dependencies,
loaded controller/Python ELF extensions, loader configuration and absent preload
invariants. Added search/preload environment overrides fail closed. `check`
rechecks identities, driver selection, host loader selection and mapped shared code.
Unknown executed tools or host ELF inputs require explicit review.

## Future allocated unit contract

1. Select and freeze a complete source snapshot during preparation. Review its
   source commit and all tool paths. This is discovery, not build qualification.
2. In a separately allocated fresh unit, verify the approved snapshot and record
   the actual pre-execution pins before any object derivation/compiler/link.
   Freeze imports, runner and environment first. Combine these pins with the
   existing source/header/object/archive/startup/script closure and absence gates.
3. Capture actual driver queries and `-###` output. Preserve all paths, options,
   archives and object order. If comparing invocations, only the proven single
   owned GCC `-fresolution=<TMPDIR>/ccNNNNNN.res` nonce may differ; preserve the raw
   dumps and exact substitution. A path or option change is not a nonce.
4. Use pinned strace around each binary-producing child, keeping the original
   argv unchanged, with bounded owned logs for `execve,openat`. Require successful
   executable paths to match `exec_path_allowed`; successful host ELF/shared-plugin
   inputs must match `host_elf_path_allowed`. Target objects and outputs remain
   subject to their separate object/source policies. Reject unknown host code.
   This helper exposes the identity predicates; the future allocated runner must
   still implement and qualify trace parsing and enforce these gates.
5. Verify all exact pins, queries, loader selection, environment and absence gates
   after execution. Preserve actual pre/post manifests and trace evidence with
   the new programme identities. Do not relabel inherited or later pins as prehashes.

No future build is allocated by this tool. A qualifying programme may use a later
cohort; there is no need to rebuild the held 650 artifacts merely to exercise this
source plan. No image, guest, visual, performance, release or hardware claim follows.

## Checks

```sh
python3 test_tool_closure.py
python3 tool_closure.py capture --driver /path/to/sh-elf-g++ \
  --driver-log /path/to/actual-driver-pre.txt --tool /path/to/explicit/tool \
  --output /new/source-snapshot.json
python3 tool_closure.py check /new/source-snapshot.json
```

Synthetic negative controls cover changed tools/plugins, aliases, mode, missing or
duplicate pins, unknown execution paths, loader/config misuse, environment and
absence changes, unplanned mapped code, changed driver selection and ambiguous
actual driver/plugin bindings. Real discovery/check receipts are kept outside Git.