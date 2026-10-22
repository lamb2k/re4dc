# Source-only future programme trace contract

`trace_closure.py` validates a separately reviewed, fully prepinned contract against
PID-qualified `strace -f -qq -v -x -s 262144 -yy` output. It does not run commands.
The required capture filter is `execve,execveat,open,openat,openat2,creat`.
Only execve/openat are supported; other captured calls refuse admission, including
failed calls. Unknown, partial, nonzero, truncated or unpaired resumed trace lines
refuse admission. Ordinary failed execve/openat probes admit no code or bytes.

Every successful execution must match one exact requested/resolved executable,
full argv/order, exact full environment (plus required absent GCC/loader override
keys), and exact execution count. Executables must also be prepinned inputs.
Only explicitly indexed GCC resolution or Python temporary basenames may vary,
inside the exact owned TMPDIR, with bijective token mapping across subprocesses.
No broad path replacement or option normalization is allowed.

Every successful regular input/plugin/shared-library read must match its pin,
requested alias and flags. Hash, extent, permissions and symlink target are
rechecked. Directory/special reads require explicit reviewed entries. Output
writes need exact path/alias/flags; temporary writes need an exact owned-root
profile. Unknown successful reads or writes refuse admission. Generated outputs
must be hashed after their producing child and pinned before a consuming child.
The trace parser cannot establish the historical bytes of an unpinned input.

The caller must separately require fresh `tool_closure.capture`/check before and
after the allocated unit, including its actual driver `-###` binding, all resolved
executables/plugins, host loaders/shared libraries/configuration, controller ELF
mappings, explicit/implicit archives/startup/linker scripts, source and generated
headers. Pin strace and the caller itself. A trace alone does not pin the inspector
or kernel interpreter. Do not widen policy from a qualifying trace after a failure.

`test_trace_closure.py` provides host-only mutation controls, including an optional
retained source-only real trace via `TRACE_CLOSURE_FIXTURE`. That fixture runs
installed Python, a `/usr/bin/true` subprocess, and read-only ctypes loading of the
installed GCC plugin. It is not a compiler/link/game test. The frozen future792
contract, actual fresh ON object identities, read-only 20B proof and 447-slot
proposal are retained in private `texture-consumers21-trace792-plan-20261022`.
It explicitly refuses programme admission until a new root allocation and exact
per-child expansion/prepin contract are frozen. No runner or programme is created.

The held650 outputs and missing fresh-unit tool-prehash gate remain unchanged.
Source fixtures and current tool snapshots cannot retroactively qualify them.
