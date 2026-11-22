"""room_capture.py <room hex> <slot std1|std2> --warp <warp.txt> --out <dir> [--base <capbase>] [--pad <padscript>]

The host side of a room capture of the old game for the engine's room bake (lane eng-rec1; the image and the disc
come from tools/engine/room_capture.sh). As lanes eng-e0b (collect.py) and eng-e1d (hillcollect.py) made the
village, farm and hill recordings, in one tool for every room:
- the warp fixture is written into track01 at LBA 400 (the disc redirects /dc/warp.txt there), the slot's disc links
  are made, Flycast runs on an inactive desktop (no window focus, no input; stopped by its own pid);
- the host arms the capture (control block m1r3_control, mode 1); the image records 300 consecutive ticks of the room
  after 300 pictures in it, one LOG3 picture each (room, sequence, tick), holding each picture until acknowledged;
- picture 1 also yields Leon's cloth binds (leon-bind.bin), a 16 MB RAM snapshot (resource-ram-001.raw: the HUD
  fix and the props read it), the room's props (extra-models.json: every live ObjMgr model and every live EmMgr
  model that is not Leon or a Ganado, with its parts chain; the template is the model's own address in this
  snapshot) and models.json (what was walked, for the report), and one still (still-001.png, reference only);
- each picture appends the props' poses (kind 2, role 2) and light inputs (kind 9), as collect.py did;
- receipt.json: every file's size and SHA-256, the room, the warp text, the image hash and tree commit, picture 1's
  tick. The bake hashes the capture files again (room_bake.py --receipt).
A picture from another room, a tick gap or an overflow stops the run (and the bake refuses such a capture).
The slot is leased (LEASE.txt) for the run only.
"""
import argparse, ctypes as ct, hashlib, json, msvcrt, os, re, shutil, struct, subprocess, sys, time
from ctypes import wintypes as W
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "flycast-harness"))
from read_pcs import Guest   # noqa: E402

SLOTS = Path(r"E:\RE4DC-Lanes\eng-e1d")


class Startup(ct.Structure):
    _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR), ("title", W.LPWSTR),
                *[(n, W.DWORD) for n in ("x", "y", "cx", "cy", "cols", "rows", "fill", "flags")],
                ("show", W.WORD), ("reserved_size", W.WORD), ("reserved_data", ct.c_void_p),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class ProcessInfo(ct.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]


def launch(slot, name):
    """Flycast in the slot on its own inactive desktop (as eng-e1d private_desktop.py): never the user's desktop"""
    user = ct.WinDLL("user32", use_last_error=True); kernel = ct.WinDLL("kernel32", use_last_error=True)
    user.CreateDesktopW.restype = W.HANDLE
    dname = "RE4DC-eng-rec1-" + slot.name
    desktop = user.CreateDesktopW(dname, None, None, 0, 0x000f01ff, None)
    if not desktop: raise ct.WinError(ct.get_last_error())
    app = str(slot / "flycast.exe")
    si = Startup(); si.cb = ct.sizeof(si); si.desktop = dname; si.title = "RE4DC eng-rec1 " + name
    si.flags = 1 | 0x100; si.show = 0
    pi = ProcessInfo()
    cmd = ct.create_unicode_buffer(subprocess.list2cmdline([app, "disc.gdi"]))
    serial = open(slot / "serial.txt", "wb"); null = open(os.devnull, "rb")
    si.stderr = si.stdout = msvcrt.get_osfhandle(serial.fileno()); si.stdin = msvcrt.get_osfhandle(null.fileno())
    os.set_handle_inheritable(si.stdout, True); os.set_handle_inheritable(si.stdin, True)
    try:
        if not kernel.CreateProcessW(app, cmd, None, None, True, 0x08000000, None, str(slot), ct.byref(si), ct.byref(pi)):
            raise ct.WinError(ct.get_last_error())
        kernel.CloseHandle(W.HANDLE(pi.thread))
    except BaseException:
        user.CloseDesktop(W.HANDLE(desktop)); raise
    finally:
        serial.close(); null.close()
    return kernel, user, desktop, pi


def finish(handles):
    kernel, user, desktop, pi = handles
    if kernel.WaitForSingleObject(W.HANDLE(pi.process), 0) == 258:
        kernel.TerminateProcess(W.HANDLE(pi.process), 0); kernel.WaitForSingleObject(W.HANDLE(pi.process), 10000)
    kernel.CloseHandle(W.HANDLE(pi.process)); user.CloseDesktop(W.HANDLE(desktop))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()


def u32(r, a): return struct.unpack_from("<I", r, a)[0] if 0 <= a <= len(r) - 4 else 0
def ptr(r, a):
    """a main-RAM pointer as an offset into the snapshot, 0 for null or anything outside main RAM"""
    v = u32(r, a)
    return v & 0xffffff if 0x8c000000 <= v < 0x8d000000 and (v & 0xffffff) < len(r) - 0x200 else 0


def model_ok(r, m):
    """a drawable source model: its ModelInfo chain reaches ModelData with parts (what bake/native_extra.py follows)"""
    if not (0x8c000000 <= u32(r, m + 0x15c) < 0x8d000000): return False
    p = ptr(r, m + 0x15c); n = 0
    while p and n < 40:
        d = ptr(r, p + 12)
        if d and struct.unpack_from("<H", r, d + 26)[0] and ptr(r, d + 28): return True
        p = ptr(r, p + 20); n += 1
    return False


def walk(r, head_at, limit=512):
    """the live models of a cManager. include/cManager.h gives pAlive at +0x10 and cUnit's be_flag +0, pNext +4 for
    the GameCube build; in this image both classes start with their vtable pointer, so pAlive is at +0x14 and a
    unit's be_flag at +4, pNext at +8 (read from the snapshot: EmMgr's head is a Ganado, id 0x15 at +0x100)"""
    out = []; q = ptr(r, head_at + 0x14)
    while q and len(out) < limit and q not in out:
        out.append(q); q = ptr(r, q + 8)
    return out


TEXPAK = Path(r"\\wsl.localhost\Ubuntu-24.04\root\work\lanes\eng-bench\.m1\pristine\dc\tex.pak")
_PACKAGES = None


def package_names(path=TEXPAK):
    """tex.pak: {key: package name}; the bake's census counts names 'source' and 'source-pair' as GameCube rows"""
    global _PACKAGES
    if _PACKAGES is None:
        t = Path(path).read_bytes(); count, idx = struct.unpack_from("<2I", t, 12); _PACKAGES = {}
        for a, b, off, size in struct.iter_unpack("<4I", t[idx:idx + 16 * count]):
            at = struct.unpack_from("<I", t, off + 24)[0]
            _PACKAGES[(a, b)] = t[off + at:off + at + 64].split(b"\0")[0].decode("latin-1")
    return _PACKAGES


def textures_keyed(r, m):
    """every part's texture carries the static texture identity (R4NREF + its tex.pak key), as bake/native_extra.py
    requires, and the key's tex.pak package is a PS2 one: a texture without a key, or keyed to a GameCube package
    ('source', 'source-pair'), leaves its prop out (no GameCube rows added; the rule of 2026-10-23)"""
    names = package_names()
    p = ptr(r, m + 0x15c); n = 0
    while p and n < 40:
        d = ptr(r, p + 12); tpl = ptr(r, p + 16); p = ptr(r, p + 20); n += 1
        if not d: continue
        count = struct.unpack_from("<H", r, d + 26)[0]; part = ptr(r, d + 28); desc = ptr(r, tpl + 8) if tpl else 0
        for _ in range(count):
            if not part or not desc: return False
            th = ptr(r, desc + r[part + 12] * 8); pixels = ptr(r, th + 8) if th else 0
            if not pixels or r[pixels:pixels + 6] != b"R4NREF": return False
            if names.get(struct.unpack_from("<2I", r, pixels + 8), "source") in ("source", "source-pair"): return False
            part = part + 32 + u32(r, part + 24)
            if part >= len(r) - 64: return False
    return True


def shape(r, m):
    """what makes two models the same catalogue model: the parts count and the ModelData chain they draw"""
    out = [r[m + 0x102]]; p = ptr(r, m + 0x15c)
    while p and len(out) < 41:
        out.append(ptr(r, p + 12)); p = ptr(r, p + 20)
    return tuple(out)


def props(r, sym):
    """the room's props: live ObjMgr models that are not SMD scroll objects (cModel kindid +0x12E == 2: the room's
    scenery, already in the world), and live EmMgr models other than Leon (id 0) and the Ganados (ids 0x10 to 0x20,
    recorded as actors by bench/r3_inputs.inc), each with its parts chain (cModel +0xF4, nParts +0x102). Instances
    that draw the same ModelData share one template (the first instance), as collect.py shared its templates."""
    rows = []; extra = []; templates = {}
    for mgr in ("ObjMgr", "EmMgr"):
        for m in walk(r, sym[mgr] & 0xffffff):
            bf = u32(r, m + 4); mid, typ, parts = r[m + 0x100], r[m + 0x101], r[m + 0x102]
            alive = (bf & 0x201) == 1; ok = model_ok(r, m); kindid = r[m + 0x12e]
            take = alive and ok and not (mgr == "ObjMgr" and kindid == 2) \
                and not (mgr == "EmMgr" and (mid == 0 or 0x10 <= mid <= 0x20))
            keyed = textures_keyed(r, m) if ok else False
            take = take and keyed
            bones = []
            if take:
                q = ptr(r, m + 0xf4)
                for _ in range(parts):
                    if not q: break
                    bones.append(q); q = ptr(r, q + 0xf4)
                take = len(bones) == parts
            t = templates.setdefault(shape(r, m), m) if take else None
            rows.append(dict(manager=mgr, model=m, id=mid, type=typ, parts=parts, kindid=kindid, be_flag=bf,
                             drawable=ok, ps2_textures=keyed, taken=take, template=t))
            if take: extra.append((m, t, bones))
    return extra, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("room", type=lambda s: int(s.lower().lstrip("r"), 16))
    ap.add_argument("slot", choices=["std1", "std2"])
    ap.add_argument("--warp", type=Path, required=True); ap.add_argument("--pad", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", type=Path, default=Path(r"E:\RE4DC-Lanes\eng-rec1\capbase"))
    ap.add_argument("--start", type=int, default=0, help="first game tick to record (0: the first after the warm-up)")
    ap.add_argument("--capacity", type=int, default=0, help="capture buffer bytes (0: the image's 384 KiB)")
    ap.add_argument("--seconds", type=int, default=420, help="give up after this long")
    ap.add_argument("--lane", default="eng-rec1")
    a = ap.parse_args()
    slot = SLOTS / a.slot; base = a.base; ev = a.out
    if ev.exists(): sys.exit(f"{ev} exists")
    meta = json.loads((base / "base.json").read_text())
    sym = {k: int(v, 16) for k, v in (l.split() for l in (base / "symbols.txt").read_text().split("\n") if l.strip())}
    # the lease: written before the slot is touched; refused if another lease under two hours old or a Flycast runs
    lease = slot / "LEASE.txt"
    if lease.exists() and time.time() - lease.stat().st_mtime < 7200: sys.exit(f"{slot} leased: {lease.read_text().strip()}")
    if (slot / "WANTED-eng-int.txt").exists(): sys.exit(f"{slot}: wanted by eng-int")
    busy = subprocess.run(["powershell", "-NoProfile", "-Command",
                           f"Get-Process flycast -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '{slot}\\*' }} | Measure-Object | % Count"],
                          capture_output=True, text=True).stdout.strip()
    if busy not in ("", "0"): sys.exit(f"{slot}: a flycast.exe runs from it")
    lease.write_text(f"{a.lane} {time.strftime('%Y-%m-%d %H:%M:%S')} room capture r{a.room:x}\n")
    ev.mkdir(parents=True)
    handles = None; done = 0; tick1 = None
    try:
        track = bytearray((base / "track01-template.iso").read_bytes())
        warp = a.warp.read_bytes().replace(b"\r", b""); assert len(warp) < 8192
        (ev / "warp.txt").write_bytes(warp); i = 2048 * meta["warp_lba"]; track[i:i + len(warp)] = warp
        if a.pad:
            pad = a.pad.read_bytes().replace(b"\r", b""); assert len(pad) < 8192
            (ev / "pad.txt").write_bytes(pad); i = 2048 * meta["pad_lba"]; track[i:i + len(pad)] = pad
        for n in ("disc.gdi", "track01.iso", "track02.raw", "track03.iso", "serial.txt", "flycast.log"):
            p = slot / n
            for _ in range(20):
                try:
                    if p.exists(): p.unlink()
                    break
                except PermissionError: time.sleep(.5)
        (slot / "track01.iso").write_bytes(track); (slot / "disc.gdi").write_text(meta["gdi"])
        os.link(base / "track02.raw", slot / "track02.raw"); os.link(base / "track03.iso", slot / "track03.iso")
        cfg = (slot / "emu.cfg").read_text(errors="replace")
        dyn = re.findall(r"Dynarec\.Enabled\s*=\s*(\S+)", cfg); clk = re.findall(r"Sh4Clock\s*=\s*(\S+)", cfg)
        handles = launch(slot, f"capture r{a.room:x}"); kernel, user, desktop, pi = handles
        (slot / "flycast.pid").write_text(str(pi.pid))   # read_pcs.Guest finds the process by it
        (ev / "launch.json").write_text(json.dumps(dict(pid=pi.pid, slot=str(slot), room=hex(a.room), start=a.start,
                                                        dynarec=dyn, sh4clock=clk, desktop="inactive")))
        log = slot / "flycast.log"
        for _ in range(2000):
            if log.exists() and "VRAM64(8 MB)" in log.read_text(errors="replace"): break
            time.sleep(.05)
        vbase = int(re.findall(r"VRAM64\(8 MB\) ([0-9A-Fa-f]+)", log.read_text(errors="replace"))[-1], 16)
        g = Guest(str(slot))
        k = ct.WinDLL("kernel32", use_last_error=True); k.OpenProcess.restype = ct.c_void_p
        hw = k.OpenProcess(0x28, False, pi.pid)
        k.WriteProcessMemory.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_size_t, ct.c_void_p]
        ctl = sym["m1r3_control"] - 0x8c000000
        def put(off, v):
            v = ct.c_uint32(v)
            if not k.WriteProcessMemory(hw, g.base + ctl + off, ct.byref(v), 4, None): raise ct.WinError()
        def read_at(addr, n): return g.read(addr & 0xffffff, n)
        deadline = time.monotonic() + a.seconds; previous = None; extra = []
        for pic in range(1, 301):
            while True:
                if time.monotonic() > deadline: raise TimeoutError(f"picture {pic}")
                data = g.read(ctl, 48)
                if data:
                    mode, seq, ack, num, tick, room, n, ov, fb, cap, dptr, start = struct.unpack("<12I", data)
                    # arm until it holds (the image's BSS clear at boot wipes an early write)
                    if pic == 1 and (mode != 1 or start != a.start) and g.read(0x10400, 4) not in (None, b"\0\0\0\0"):
                        put(44, a.start)
                        if a.capacity: put(36, a.capacity)
                        put(0, 1)
                    if seq == 2 * pic and ack != seq and num == pic: break
                if kernel.WaitForSingleObject(W.HANDLE(pi.process), 0) != 258: raise RuntimeError(f"exit before picture {pic}")
                time.sleep(.003)
            if room != a.room: raise RuntimeError(f"picture {pic} is from room {room:x}, not r{a.room:x}")
            assert not ov and 0 < n <= cap, (ov, n, cap)
            if pic == 1:
                tick1 = tick
                player = struct.unpack("<I", g.read(sym["pPL"] - 0x8c000000, 4))[0]
                part = struct.unpack("<I", read_at(player + 0xf4, 4))[0]; binds = bytearray()
                for _ in range(119):
                    binds += read_at(part + 0xf8, 48); part = struct.unpack("<I", read_at(part + 0xf4, 4))[0]
                (ev / "leon-bind.bin").write_bytes(binds)
                raw = g.read(0, 16 << 20); (ev / "resource-ram-001.raw").write_bytes(raw)
                extra, rows = props(raw, sym)
                (ev / "extra-models.json").write_text(json.dumps(extra))
                (ev / "models.json").write_text(json.dumps(rows, indent=1))
            elif tick != previous + 1: raise RuntimeError(f"tick gap at picture {pic}: {previous} -> {tick}")
            previous = tick
            extra_data = bytearray()
            for index, (m, template, bones) in enumerate(extra):   # as eng-e0b collect.py: poses, then light inputs
                extra_data += struct.pack("<II4I", 2, 64, 2, index, template, 0) + read_at(m + 12, 48)
                for j, q in enumerate(bones):
                    extra_data += struct.pack("<II4I", 2, 64, 2, index, template, j + 1) + read_at(q + 12, 48)
            for index, (m, template, bones) in enumerate(extra):
                li = read_at(m + 0x164, 0x74); info = struct.unpack("<I", read_at(m + 0x15c, 4))[0]
                color = read_at(info + 0x8c, 4) if 0x8c000000 <= info < 0x8d000000 else bytes(4)
                enable, flag, parts = li[0x50], li[0x51], li[0x52]; select = struct.unpack_from("<I", li, 0x54)[0]
                off = struct.unpack_from("<3f", li, 0x58); size = struct.unpack_from("<3f", li, 0x64)
                tev = read_at(m + 0x12d, 1)[0]; amb = read_at(m + 0x139, 3)
                extra_data += struct.pack("<II5I3f3f", 9, 68, 2, index, m, flag | parts << 8 | enable << 16, select, *off, *size) \
                    + color + struct.pack("<5I", tev | 255 << 8, amb[0] | amb[1] << 8 | amb[2] << 16, 0xffffffff, 0xffffffff, 0)
            payload = g.read((dptr & 0x1fffffff) - 0xc000000, n); assert len(payload) == n
            (ev / f"picture-{pic:03}.bin").write_bytes(struct.pack("<4s3I", b"LOG3", room, pic, tick) + payload + extra_data)
            if pic == 1:   # one still, for the reference only (the bake does not read it)
                import numpy as np
                from PIL import Image
                offset = (fb - 0xa5000000) // 2
                word = np.arange(offset // 4, offset // 4 + 640 * 480 // 2, dtype=np.uint32)
                mapped = (word & 0xfffff) * 2 + (word >> 20); lo, hi = int(mapped.min()), int(mapped.max()) + 1
                vb = ct.create_string_buffer((hi - lo) * 4); got = ct.c_size_t(0)
                ct.windll.kernel32.ReadProcessMemory(ct.c_void_p(g.handle), ct.c_void_p(vbase + lo * 4), vb, (hi - lo) * 4, ct.byref(got))
                px = np.frombuffer(vb.raw, dtype="<u4")[mapped - lo].view("<u2").reshape(480, 640)
                rgb = np.stack([(px >> 11) * 255 // 31, (px >> 5 & 63) * 255 // 63, (px & 31) * 255 // 31], axis=2)
                Image.fromarray(rgb.astype("uint8")).save(ev / "still-001.png", compress_level=1)
            put(8, seq); done = pic
    finally:
        if handles: finish(handles)
        for f in ("flycast.log", "serial.txt"):
            if (slot / f).exists(): shutil.copyfile(slot / f, ev / f)
        for n in ("track02.raw", "track03.iso", "track01.iso", "disc.gdi"):
            for _ in range(20):
                try:
                    if (slot / n).exists(): (slot / n).unlink()
                    break
                except PermissionError: time.sleep(.5)
        if lease.exists() and lease.read_text().startswith(a.lane): lease.unlink()
    # bake/native_pack.build looks for the props' RAM snapshot under <prior>/eng-bench-<cross|hayfork>-4 (the village
    # and farm recordings' first snapshot); this capture's own snapshot is linked under both names in <out>/prior
    if (ev / "resource-ram-001.raw").exists():
        for scene in ("cross", "hayfork"):
            d = ev / "prior" / f"eng-bench-{scene}-4"; d.mkdir(parents=True, exist_ok=True)
            if not (d / "resource-ram-001.raw").exists(): os.link(ev / "resource-ram-001.raw", d / "resource-ram-001.raw")
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(ev.iterdir())
             if p.is_file() and p.suffix in (".bin", ".raw", ".json", ".txt") and p.name != "receipt.json"}
    rec = dict(room=f"r{a.room:x}", pictures=done, tick_first=tick1, warp=warp.decode("latin-1"),
               image_sha256=(base / "elf.sha256").read_text().split()[0], tree_commit=(base / "tree-commit.txt").read_text().strip(),
               track03_sha256=(base / "track03.sha256").read_text().strip(), files=files)
    (ev / "receipt.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(room=rec["room"], pictures=done, tick_first=tick1, props=len(extra))))


if __name__ == "__main__":
    main()
