#!/usr/bin/env python3
"""One pre-emptable, PID-owned <=50s unchanged-QA regression run.

Uses a hash-pinned fullplay runner. Controller posts target only the owned
emulator windows. Optional checkpoints restore Flycast's entire unedited state
with exact input/code/data ancestry; no individual game/HP/AI fields are written.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runner", type=Path, required=True)
    ap.add_argument("--runner-sha256", required=True)
    ap.add_argument("--disc", type=Path, required=True)
    ap.add_argument("--cap", type=Path, required=True)
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--syms", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--binding", type=Path)
    ap.add_argument("--layout", type=Path)
    ap.add_argument("--event-shots", action="store_true")
    ap.add_argument("--require-mendez-for-pause", action="store_true")
    ap.add_argument("--allow-event-skip", action="store_true")
    ap.add_argument("--movement-clock", choices=("host", "source"), default="host")
    ap.add_argument("--seconds", type=int, choices=range(30, 48), default=45)
    ap.add_argument("--no-limit", action="store_true", help="existing Flycast unthrottled harness setting")
    ap.add_argument("--save-checkpoint", action="store_true", help="Flycast's unedited normal-unload state")
    ap.add_argument("--checkpoint-seed", type=Path, help="own sealed ordinary-controller run directory")
    ap.add_argument("--elf", type=Path, help="exact bound ELF for read-only checkpoint code audit")
    ap.add_argument("--health-stop", action="store_true", help="end on first naturally observed life decrease")
    a = ap.parse_args()
    if a.no_limit:
        os.environ["FP_NOLIMIT"] = "1"  # explicit Windows argument; WSL exports need not cross interop
    source_snapshots = {Path(__file__).name: Path(__file__).read_bytes()}
    if a.layout:
        observer_source = Path(__file__).with_name("observe.py")
        source_snapshots[observer_source.name] = observer_source.read_bytes()
    if a.save_checkpoint or a.checkpoint_seed:
        if not (a.save_checkpoint and a.elf and a.binding and a.layout):
            raise SystemExit("checkpoint continuation requires save, exact ELF, binding and layout")
        for filename in ("checkpoint.py", "checkpoint_runner.py", "checkpoint_read_log.py"):
            path = Path(__file__).with_name(filename)
            source_snapshots[filename] = path.read_bytes()
    if hashlib.sha256(a.runner.read_bytes()).hexdigest() != a.runner_sha256:
        raise SystemExit("runner identity changed")
    if a.cap.exists():
        raise SystemExit("evidence directory exists")
    if a.binding:
        bound = json.loads(a.binding.read_text(encoding="utf-8-sig"))
        source_track = a.disc / bound.get("disc_track03_name", "track03.bin")
        with source_track.open("rb") as stream:
            actual_track = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual_track != bound["input_track03_sha256"]:
            raise SystemExit("disc track differs from bound QA input; guest not started")
        offsets = [int(bound["symbols"][key], 0) - 0x8c000000 for key in ("logbuf", "head", "stage")]
        if [int(value, 0) for value in a.syms.split()] != offsets:
            raise SystemExit("log symbols differ from bound ELF; guest not started")
    spec = importlib.util.spec_from_file_location("owned_fp_run", a.runner)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    disc_identity = None
    parent_checkpoint = None
    if a.save_checkpoint:
        from checkpoint import sha, verify
        names = ["disc.gdi", "track01.bin", "track02.raw", bound.get("disc_track03_name", "track03.bin")]
        disc_identity = dict(files={name: sha(a.disc/name) for name in names},
                             program_sha256=bound["disc_program_sha256"], elf_sha256=bound["elf_sha256"])
        if a.checkpoint_seed:
            parent_checkpoint = verify(a.checkpoint_seed, a.elf, a.binding, a.layout, disc_identity, runner.emu_exe())
            os.environ["RE4DC_CHECKPOINT_SEED"] = str(a.checkpoint_seed)
            os.environ["RE4DC_CHECKPOINT_LOG_HEAD"] = str(parent_checkpoint["audit"]["log_head"])
        else:
            os.environ.pop("RE4DC_CHECKPOINT_SEED", None)
            os.environ.pop("RE4DC_CHECKPOINT_LOG_HEAD", None)
    if runner.count_flycasts() >= 12:
        raise SystemExit("release launch pressure: no guest started")
    os.environ["RE4DC_MAX_FLYCASTS"] = "16"
    # Exact default KeyboardInputMapping: F/V are the full analog triggers;
    # I/K/J/L are the left analog stick. Existing controller bindings remain.
    runner.KEYS.update(ltrig=(0x21, 0), rtrig=(0x2f, 0),
                       fwd=(0x17, 0), back=(0x25, 0), turnleft=(0x24, 0), turnright=(0x26, 0))
    runner.VK.update(ltrig=0x46, rtrig=0x56, fwd=0x49, back=0x4b, turnleft=0x4a, turnright=0x4c)
    def capture_context(label):
        if not a.event_shots:
            return
        try:
            text = (a.cap / "run-output.txt").read_text(errors="replace")
            fb = re.findall(r"fb=[0-9a-f]+,[0-9a-f]+", text)
            if not fb:
                raise ValueError("no source framebuffer pointer")
            folder = a.cap / "events" / ("%02d-" % len(state.get("input_posts", [])) + label)
            folder.mkdir(parents=True)
            for filename in ("emu.cfg", "flycast.log", "flycast.pid"):
                shutil.copyfile(a.cap / filename, folder / filename)
            (folder / "boot.log").write_text(fb[-1] + "\n", encoding="utf-16")
            spec = importlib.util.spec_from_file_location("owned_event_capture", a.cap / "capture_ui_vram.py")
            capture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(capture)
            capture.capture(folder, folder / "frames")
            (folder / "state-context.json").write_text(json.dumps(observer.last if observer else {}, indent=2) + "\n")
        except Exception as exc:
            state.setdefault("event_shot_errors", []).append(str(exc))

    def press(pid, names, hold):
        if observer and a.require_mendez_for_pause and set(names) & {"fwd", "back", "turnleft", "turnright"} and observer.last and observer.last["mendez"]:
            deadline = time.monotonic() + 8
            while (observer.last.get("global", {}).get("rno", [])[:2] != [3, 0]
                   or observer.last.get("global", {}).get("stop") != 0 or observer.last["event_start_cnt"]):
                if state.get("checkpoint_close_requested"):
                    return 0
                if time.monotonic() > deadline or not runner.windows_of(pid):
                    raise RuntimeError("ordinary boss resume did not reach free play; movement withheld")
                time.sleep(0.05)
            state.setdefault("movement_resume_gates", []).append(observer.last)
        if observer and set(names) == {"ltrig", "rtrig", "down"}:
            deadline = time.monotonic() + 14
            while not observer.qa_safe(observer.last):
                if time.monotonic() > deadline or not runner.windows_of(pid):
                    raise RuntimeError("QA safe-state sampling did not reach 30 ticks; chord withheld")
                time.sleep(0.1)
            state.setdefault("chord_safe_samples", []).append(observer.last)
        if a.require_mendez_for_pause and names == ["start"]:
            last = observer.last if observer else None
            boss = last and any(e["alive"] & 1 and e["hp"] > 0 for e in last["mendez"])
            event = last and last["event_start_cnt"] > 0 and last.get("global", {}).get("status", [0, 0])[1] & 0x10000000
            if not boss and not (a.allow_event_skip and event):
                raise RuntimeError("original Mendez encounter not active; pause input withheld")
        if not runner.windows_of(pid):
            raise RuntimeError("owned emulator window unavailable; input aborted")
        if names == ["start"]:
            capture_context("before-start")
        state.setdefault("input_posts", []).append(dict(keys=names, host_s=time.monotonic() - host_started,
                                                         state=observer.last if observer else None))
        def post(key_up):
            # Re-enumerate after every hold: a pre-empted guest's old HWND may
            # already have been recycled by another application.
            windows = runner.windows_of(pid)
            if not windows or state.get("preempted") or state.get("checkpoint_close_requested"):
                raise RuntimeError("owned emulator window vanished; input aborted")
            for key in names:
                scan, extended = runner.KEYS[key]
                flags = 1 | (scan << 16) | (extended << 24)
                if key_up:
                    flags |= (1 << 30) | (1 << 31)
                for window in windows:
                    if not runner.user32.PostMessageW(window, 0x101 if key_up else 0x100, runner.VK[key], flags):
                        raise ctypes.WinError(ctypes.get_last_error())
            return len(windows)
        count = post(False)
        until = time.monotonic() + hold
        movement = set(names) & {"fwd", "back", "turnleft", "turnright"}
        source_start = observer.last.get("global", {}).get("frame") if observer and observer.last else None
        source_hold = a.movement_clock == "source" and movement and source_start is not None
        source_pointer = int(observer.last["global"]["ptr"], 0) if source_hold else None
        if source_hold:
            source_start = observer.field(source_pointer, "GlobalWork", "Frame_cnt", "I")
        source_frames = max(1, round(hold * 30))
        while source_hold or time.monotonic() < until:
            if state.get("checkpoint_close_requested"):
                return count  # normal SDL unload releases its keys and saves the entire state
            if state.get("preempted") or not runner.windows_of(pid):
                raise RuntimeError("owned guest ended during key hold; further posts aborted")
            if source_hold:
                last = observer.last
                if last["event_start_cnt"] or last["subscreen_type"] or last.get("global", {}).get("rno", [0])[0] != 3:
                    break  # release normal movement as soon as an original event takes control
                source_current = observer.field(source_pointer, "GlobalWork", "Frame_cnt", "I")
                if source_current - source_start >= source_frames:
                    break
                time.sleep(0.02)
            else:
                time.sleep(min(0.05, max(0, until - time.monotonic())))
        post(True)
        if source_hold:
            state.setdefault("source_movement_holds", []).append(dict(keys=names, first=source_start,
                last=observer.field(source_pointer, "GlobalWork", "Frame_cnt", "I"), requested_frames=source_frames))
        if set(names) == {"ltrig", "rtrig", "down"}:
            capture_context("qa-chord-released")
        return count

    runner.press = press
    runner.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                 ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.GetProcessTimes.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulonglong),
                                      ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong),
                                      ctypes.POINTER(ctypes.c_ulonglong)]
    done = threading.Event()
    host_started = time.monotonic()
    state = dict(hard_guest_limit_seconds=48, initial_flycasts=runner.count_flycasts(),
                 release_preemption_threshold=14, preempted=False,
                 memory_writes=False, controller_target="owned PID windows only",
                 gameplay_field_writes=False, unedited_whole_emulator_restore=bool(a.checkpoint_seed),
                 fp_nolimit=os.environ.get("FP_NOLIMIT") == "1", movement_clock=a.movement_clock,
                 allow_normal_event_skip=a.allow_event_skip,
                 save_unedited_checkpoint=a.save_checkpoint,
                 checkpoint_parent=str(a.checkpoint_seed) if a.checkpoint_seed else None,
                 tool_sha256={name: hashlib.sha256(data).hexdigest() for name, data in source_snapshots.items()})
    observer = None
    if a.binding or a.layout:
        if not (a.binding and a.layout):
            raise SystemExit("read-only sampling requires both binding and DWARF layout")
        from observe import Observer
        observer = Observer(a.cap, a.binding, a.layout)

    def stop_owned(reason, graceful=False, register_only=False):
        pidfile = a.cap / "flycast.pid"
        if not pidfile.exists():
            return
        pid = int(pidfile.read_text())
        handle = kernel.OpenProcess(0x1001, False, pid)
        if not handle:
            return
        try:
            path = ctypes.create_unicode_buffer(32768)
            length = ctypes.c_ulong(len(path))
            if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(length)):
                raise RuntimeError("cannot verify owned emulator executable")
            if os.path.normcase(os.path.abspath(path.value)) != os.path.normcase(str((a.cap / "flycast.exe").resolve())):
                raise RuntimeError("PID no longer belongs to this evidence executable")
            times = [ctypes.c_ulonglong() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                raise RuntimeError("owned emulator start time unavailable")
            if "owned_start_filetime" in state and state["owned_start_filetime"] != times[0].value:
                raise RuntimeError("owned emulator PID start time changed")
            state["owned_start_filetime"] = times[0].value
            state["owned_pid"] = pid
            if register_only:
                return
            if graceful:
                runner.STOP_REQUESTED = True
                state.update(checkpoint_close_requested=True, close_reason=reason)
                for hwnd in runner.windows_of(pid):
                    cls = ctypes.create_unicode_buffer(256)
                    runner.user32.GetClassNameW(hwnd, cls, 256)
                    if cls.value == "SDL_app":
                        runner.user32.PostMessageW(hwnd, 0x10, 0, 0)
            else:
                kernel.TerminateProcess(handle, 125)
                state.update(preempted=True, reason=reason)
        finally:
            kernel.CloseHandle(handle)

    def watchdog():
        started = None
        life_baseline = None
        try:
            while not done.wait(0.25):
                if (a.cap / "flycast.pid").exists() and started is None:
                    started = time.monotonic()
                    stop_owned("initial PID/start identity", register_only=True)
                    snapshots = a.cap / "owned-tools"
                    snapshots.mkdir()
                    for filename, data in source_snapshots.items():
                        (snapshots / filename).write_bytes(data)
                if started is None:
                    continue
                if observer and not state.get("checkpoint_close_requested"):
                    observer.sample()
                    row = observer.last
                    life = (row or {}).get("global", {}).get("player_life")
                    alive = (row or {}).get("player", {}).get("alive", 0) & 1
                    if a.health_stop and alive and life is not None and life > 0 and life_baseline is None:
                        life_baseline = life
                        state["health_baseline"] = dict(life=life, sample=row)
                    if a.health_stop and alive and life_baseline is not None and life < life_baseline and not state.get("health_stop"):
                        state["health_stop"] = dict(first_natural_life_decrease=life, sample=row)
                        capture_context("natural-health-decrease")
                        stop_owned("first natural player life decrease", graceful=a.save_checkpoint)
                if a.save_checkpoint and time.monotonic() - started >= a.seconds-0.5 and not state.get("checkpoint_close_requested"):
                    capture_context("checkpoint-close")
                    stop_owned("bounded ordinary-route checkpoint", graceful=True)
                if time.monotonic() - started >= 48:
                    stop_owned("hard guest time limit")
                    break
                if runner.count_flycasts() >= 14:
                    stop_owned("release launch pressure")
                    break
        except Exception as exc:
            state["watchdog_error"] = str(exc)
            stop_owned("watchdog failure")

    thread = threading.Thread(target=watchdog, daemon=True)
    thread.start()
    sys.argv = [str(a.runner), "--disc", str(a.disc), "--cap", str(a.cap),
                "--syms", a.syms, "--seconds", str(a.seconds), "--period", "3",
                "--name", a.name, "--keys", str(a.keys)]
    try:
        runner.main()
    finally:
        done.set()
        thread.join(timeout=2)
        if observer:
            observer.close()
        if a.cap.exists():
            (a.cap / "ownership-resource-guard.json").write_text(json.dumps(state, indent=2) + "\n")
            if a.save_checkpoint:
                from checkpoint import seal
                if parent_checkpoint and json.loads((a.cap/"initial-data.json").read_text()) != parent_checkpoint["data"]:
                    raise RuntimeError("restored initial emulator data differs from sealed parent")
                seal(a.cap, a.elf, a.binding, a.layout, disc_identity, a.checkpoint_seed)


if __name__ == "__main__":
    main()
