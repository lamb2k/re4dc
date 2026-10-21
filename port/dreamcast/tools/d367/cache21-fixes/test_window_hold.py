#!/usr/bin/env python3
"""Compile actual current helpers using the existing native UI extraction method."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
UI_PATH = "port/dreamcast/game/platform/native_ui.cpp"
FUNCTIONS = (
    "void close_entry(", "unsigned movie_window_release(",
    "int vram_claim(", 'extern "C" void re4dc_ui_vram_hold(',
    'extern "C" void re4dc_ui_vram_unclaim('
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_source(ref, path=UI_PATH):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{path}"])


def command(argv, log):
    log.with_suffix(".command.json").write_text(json.dumps(list(map(str, argv)), indent=2) + "\n")
    result = subprocess.run(list(map(str, argv)), text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=60)
    log.write_text(result.stdout)
    if result.returncode:
        print(result.stdout[-10000:])
        result.check_returncode()
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-ref", default="54cef5d1560c41d074beee05ffa1ecd38f2ee642")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    extractor_path = REPO / "port/dreamcast/tests/test_movie_world_arena.py"
    spec = importlib.util.spec_from_file_location("actual_ui_extraction", extractor_path)
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)
    pins = {}

    def export(name, data):
        out = args.out / name
        source = out / "game/platform/native_ui.cpp"
        source.parent.mkdir(parents=True)
        source.write_bytes(data)
        text = data.decode()
        extractor.G = out / "game"
        bodies = {sig: extractor.function("platform/native_ui.cpp", sig) for sig in FUNCTIONS}
        (out / "window_actual_types.inc").write_text(
            extractor.function("platform/native_ui.cpp", "struct Key {").rstrip() + ";\n" +
            extractor.function("platform/native_ui.cpp", "struct Entry {").rstrip() + ";\n")
        hold_start = text.index("#if defined(RE4DC_SS_HOLD_RESTORE)")
        hold_end = text.index("\n#endif", hold_start) + len("\n#endif")
        hold = text[hold_start:hold_end]
        (out / "window_actual_hold.inc").write_text(hold + "\n")
        pin = re.findall(r"^#define RE4DC_ENTRY_PINNED.*$", text, re.M)[0]
        (out / "window_actual_entry_pin.inc").write_text(pin + "\n")
        (out / "window_actual_methods.inc").write_text("\n".join(bodies.values()))
        pins[name] = {"source_sha256": sha(data), "hold_macro_sha256": sha(hold.encode()),
                      "function_sha256": {sig: sha(body.encode()) for sig, body in bodies.items()}}
        return out, bodies

    prior, prior_bodies = export("baseline", git_source(args.baseline_ref))
    candidate, candidate_bodies = export("candidate", (REPO / UI_PATH).read_bytes())
    selected = {}
    for ref in ("fe0efcdd", "d4a3b31fac3362937a3f21eaa874e07be94fd061"):
        _, bodies = export("selected-" + ref, git_source(ref))
        # Every helper used in this regression has the same body in the live
        # release, current integration and d4. No historic mechanism is imported.
        assert bodies == prior_bodies
        selected[ref] = {sig: sha(body.encode()) for sig, body in bodies.items()}
    for sig in FUNCTIONS:
        if sig != "unsigned movie_window_release(":
            assert prior_bodies[sig] == candidate_bodies[sig]
    prior_text = (prior / "game/platform/native_ui.cpp").read_text()
    for marker in (
        "unsigned wb=0;frag_min_age=kFragMinAge;const unsigned wr=movie_window_release(need,false,wb);frag_min_age=0;",
        "unsigned db=0;const unsigned dr=movie_window_release(need,true,db);",
        "unsigned wb=0;const unsigned wr=movie_window_release(bytes,fell_back,wb);",
        "unsigned wb=0;const unsigned wr=movie_window_release(want,false,wb);",
    ):
        assert marker in prior_text and marker in (REPO / UI_PATH).read_text()
    flags = ["g++", "-std=c++20", "-O1", "-g", "-fsanitize=address,undefined",
             "-fno-sanitize-recover=all", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie",
             "-DRE4DC_ACTOR_TRANSACTION=1", "-DRE4DC_CORE_PIN=2", "-DRE4DC_UI_FRAG_WINDOW=1",
             "-DRE4DC_TEX_RESIDENT=1", "-DRE4DC_MOVIE_WINDOW=1", "-DRE4DC_SS_PACK=1",
             "-DRE4DC_PVR_STREAM=1", "-DRE4DC_PVR_PIPELINE=1", "-DRE4DC_CLAIM_TEST=0",
             "-I" + str(REPO / "port/dreamcast/game/platform/include")]
    results = []
    for name, source, enabled, hold in (
        ("baseline", prior, 0, 1), ("disabled", candidate, 0, 1),
        ("enabled", candidate, 1, 1), ("hold-disabled", candidate, 0, 0)
    ):
        out = args.out / (name + "-run")
        out.mkdir()
        command([*flags, f"-DRE4DC_SS_WINDOW_HOLD_RESTORE={enabled}", f"-DRE4DC_SS_HOLD_RESTORE={hold}",
                 "-I" + str(source), HERE / "window_hold_host.cpp", "-o", out / "test"], out / "compile.log")
        result = command([out / "test"], out / "run.log")
        print(result, end="")
        results.append({"variant": name, "window_note": enabled, "hold_restore": hold, "output": result})
    receipt = {"scope": "Actual helpers, actual actor lease class, ASan/UBSan; package/GPU/snapshot boundary adapters; no PVR or gameplay acceptance",
               "baseline_revision": args.baseline_ref, "selected_helper_identities": selected,
               "source_pins": pins, "variants": results,
               "test_sha256": {p.name: sha(p.read_bytes()) for p in (
                   Path(__file__), HERE / "window_hold_host.cpp", extractor_path,
                   REPO / "port/dreamcast/game/platform/include/actor_resource_lease.h")}}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
