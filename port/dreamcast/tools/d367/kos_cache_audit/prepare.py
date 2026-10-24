#!/usr/bin/env python3
"""Prepare a verified, build-local KOS cache header/helper; never edit KOS_BASE."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from cache_diag import instrument, validate_timer, TIMER_INPUTS

KOS_SHA = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
INPUTS = {
    "Makefile": "a96167ebe94a03eb66cc5f2e00a01b8086a2c2b53b7619095e2a6c20eb7a4353",
    "kernel/arch/dreamcast/kernel/Makefile": "408b60f466ee7307f45fa282deddd5f760a6773e9172ff80cff5f9eaa808072a",
    "include/kos/cache.h": "cb65548d09447e45329be136666bbb1d22f3f1448b7f7a4f1ad09fb600372c02",
    "kernel/arch/dreamcast/include/arch/cache.h": "d5ca901258bc9ec3f3f4f92c4fbfef97ee15bf61c9b02486de173bf1f93b8295",
    "kernel/arch/dreamcast/kernel/exec.c": "f87de9ba11e38fb13159a87123126426fda39c0b770483c0018a516b5f8bdc76",
    "kernel/arch/dreamcast/hardware/dmac.c": "fa5ebdd2ebb734d8953b1ab1d4cf1d8ada252d74333b6dad8a7c211eca18d236",
    "kernel/arch/dreamcast/hardware/g1ata.c": "cff571846082795163ac77a61d7819ac43207aea01f09b6c936fa95418c166b1",
    "kernel/arch/dreamcast/hardware/network/broadband_adapter.c": "8bdb117e3b5400959a59c85dc8727b2ee8f14af7c5d36aeb70097f5641dc7a56",
}
CALLERS = {path for path in INPUTS if path.endswith(".c")}
API_HEADERS = {"kernel/arch/dreamcast/include/arch/cache.h", "include/kos/cache.h"}
CALL = re.compile(r"\b(?:arch_)?dcache_(?:wback|flush)_(?:range|all)\b")
COMMENT = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', re.S)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(kos):
    """Check all API token uses, including address-taking and macro aliases."""
    candidates = subprocess.check_output(
        ["rg", "--files", "kernel", "include", "addons", "-g", "*.c", "-g", "*.h",
         "-g", "*.cpp", "-g", "*.S", "-g", "*.s"], cwd=kos, text=True).splitlines()
    result = {}
    for relative in candidates:
        path = kos / relative
        source = path.read_text(errors="strict")
        source = COMMENT.sub(lambda m: "\n" * m[0].count("\n"), source)
        matches = [source.count("\n", 0, m.start()) + 1 for m in CALL.finditer(source)]
        if matches and relative not in API_HEADERS:
            result[relative] = matches
    if set(result) != CALLERS:
        raise ValueError("KOS_CACHE_P2: inline writeback caller inventory changed: " +
                         json.dumps(result, sort_keys=True))
    return result


def validate(kos):
    head = subprocess.check_output(["git", "-C", str(kos), "rev-parse", "HEAD"], text=True).strip()
    if head != KOS_SHA:
        raise ValueError("KOS_CACHE_P2 needs pinned KOS " + KOS_SHA + "; found " + head)
    for relative, expected in INPUTS.items():
        if sha(kos / relative) != expected:
            raise ValueError("KOS_CACHE_P2 unsupported KOS source: " + relative)
    calls = inventory(kos)
    return head, calls


def prepare(kos, output, patch, diagnostics=False):
    kos, output, patch = kos.resolve(), output.resolve(), patch.resolve()
    if output == kos or kos in output.parents:
        raise ValueError("KOS_CACHE_P2: output must be outside KOS_BASE")
    head, calls = validate(kos)
    if diagnostics:
        validate_timer(kos)
    tree = output / "tree"
    # Copy only patch inputs. Existing files in the isolated output may be
    # refreshed by Make; unrelated files and the installed SDK are untouched.
    for relative in ("Makefile", "kernel/arch/dreamcast/kernel/Makefile",
                     "kernel/arch/dreamcast/include/arch/cache.h"):
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((kos / relative).read_bytes())
    helper = tree / "kernel/arch/dreamcast/kernel/cache_p2.S"
    if helper.exists():
        helper.unlink()
    command = ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-d", str(tree)]
    result = subprocess.run(command, input=patch.read_bytes(), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=True)
    if diagnostics:
        helper.write_text(instrument(helper.read_text(), True))
    # The pinned environment uses -isystem; our -I overlay wins regardless of
    # command order. Fail clearly if a different environment overrides that.
    (output / "require_p2.h").write_text('''#include <kos/cache.h>
#ifndef KOS_DCACHE_WBACK_P2_ACTIVE
#error KOS_CACHE_P2: compiler did not select the patched KOS arch/cache.h
#endif
''')
    receipt = dict(status="PASS", kos_commit=head, kos_root=str(kos), source_sha256=INPUTS,
                   inline_callers=calls, patch_sha256=sha(patch), patch_log=result.stdout.decode(),
                   output_sha256={str(p.relative_to(tree)): sha(p) for p in tree.rglob("*") if p.is_file()})
    if diagnostics:
        receipt["diagnostics"] = dict(timer_source_sha256=TIMER_INPUTS, helper_scope="masked subinterval, observer tail excluded")
    (output / "prepare.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.kos_root, args.output, args.patch, args.diagnostics)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(dict(status=result["status"], inline_callers=result["inline_callers"])))


if __name__ == "__main__":
    main()
