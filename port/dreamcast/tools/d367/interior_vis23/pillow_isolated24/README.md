# Isolated Pillow availability — host preparation only

Status: HOST source/control preparation complete; root review and a separate guest grant are required. Previous GCperiod25 `No module named PIL` failures remain untouched. No captured images or corrected guest observations are claimed.

The launcher supplies the authentic installed Pillow 12.3.0 package to the existing in-process screenshot import. It does not change `census-bound-run.py`, `fp_run.py`, `capture_ui_vram.py`, the exact-child 55-second timer, console selection, locks, media, fixture or runner arguments.

Use the ordinary approved slot → trace_lock chain, with its Windows Python segment changed ONLY to:

```
<absolute pinned python.exe> -I -S -B -X pycache_prefix=<fresh absolute nonexistent path> <absolute pillow_launcher.py> -- <original census-bound-run.py> <original fp_run.py> <all original runner arguments>
```

No guest command is authorized by this kit. The root controller must keep its explicit environment, guest allocation, caps, template/executable/fixture pins and lock evidence. Choose a NEW cache prefix for each arm; it must not exist. Do not add site-packages to sys.path or enable site startup. Root's original source/argv pins are in kos-census-media-prep-v1/OBSERVATION-PROPOSAL.json and kos-census-media-root-review-v1/root-caller-pair-v2.py.

`PILLOW-PINS.json` seals all 114 non-cache installed PIL payloads (14,641,977 bytes), authentic package init, source files, every installed extension, type/support files, distribution metadata and actual Python/bound/harness/capture inputs. No DLL exists in the PIL payload tree and there is no sibling pillow.libs directory in this installation. Native extensions still use normal CPython/system native-loader dependencies; this is not a standalone OS/CPython runtime attestation. No installation or package copies occur in actual launcher operation.

Only PIL namespace imports are intercepted. Python source is authenticated and directly compiled/executed; adjacent bytecode is never consulted by that loader. Extension bytes are checked before normal ExtensionFileLoader loading. Authentic __init__.py executes normally with package __path__ restricted to the PIL directory. Unknown PIL modules and package membership changes fail closed. Other services retain normal interpreter behavior. The fresh no-write cache prefix protects the unchanged screenshot spec loader too; loader/harness inputs remain separately pinned. This does not authorize arbitrary alternative wrapper/runner source.

Host controls: `HOST-CONTROLS.json` records 12 checks, actual WindowsPython -I-S-B. These include in-memory RGB→PNG→RGB, PYTHONHOME/PYTHONPATH isolation, actual unchanged wrapper+harness --help with original --cap/--syms/--seconds45/--period25 argument shape (no guest), authentic capture-template compile without calling capture, four matching-source unchecked-hash adjacent PIL caches ignored/preserved, source/init/native mutation refusals, extra module and pre-existing cache-prefix refusal. Owned cache/source test copies are preserved at OWNED-HOST-SCRATCH.json; no original installation/cache or failed capture was modified. The 2×2 PNG exists only in BytesIO.

Known scope: these controls establish installed dependency availability and argument preservation on host. They establish no screenshot of a guest, framebuffer correctness, memory/performance improvement, runtime rain behavior or physical-console result.
