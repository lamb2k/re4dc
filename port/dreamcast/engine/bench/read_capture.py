"""Read a single scene capture using the existing read-only Flycast reader."""
import argparse
import ctypes
from pathlib import Path
import struct
import re
import sys
import time
p = argparse.ArgumentParser()
p.add_argument("evidence", type=Path)
p.add_argument("room", type=lambda value: int(value, 16))
p.add_argument("address", type=lambda value: int(value, 16))
args = p.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/flycast-harness"))
from read_pcs import Guest
ev = args.evidence
deadline = time.monotonic() + 160
while not ((ev/"flycast.pid").exists() and (ev/"flycast.log").exists()):
    if time.monotonic() > deadline: raise SystemExit("no Flycast PID/log")
    time.sleep(.05)
guest = Guest(str(ev))
win = ctypes.windll.user32
@ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p)
def title(hwnd, _):
    pid = ctypes.c_ulong()
    win.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    if pid.value == guest.pid: win.SetWindowTextW(hwnd, "RE4DC eng-bench " + ev.name)
    return 1
address = args.address - 0x8c000000
last = 0
last_title = 0
while guest.alive() and time.monotonic() < deadline:
    if time.monotonic() - last_title > 1:
        win.EnumWindows(title,0)
        last_title = time.monotonic()
    h = guest.read(address,28)
    if not h: continue
    seq,magic,room,pic,frame,size,overflow = struct.unpack("<7I",h)
    if seq & 1 or magic != 0x31434d46 or room != args.room or pic <= last:
        time.sleep(.001)
        continue
    data = guest.read(address+28,size) if size <= 65536 else None
    if data is None or guest.read(address,28) != h: continue
    if overflow or last + 1 != pic:
        raise SystemExit(f"capture refused at picture {pic}, previous {last}, bytes {size}, overflow {overflow}")
    (ev / f"picture-{pic:03d}.bin").write_bytes(h + data)
    if pic in (1,150,300):
        # Let this scene's asynchronous flip finish within the capture hold.
        time.sleep(.023)
        log = (ev/"flycast.log").read_text(errors="replace")
        vram = re.findall(r"VRAM64\(8 MB\) ([0-9A-Fa-f]+)", log)
        if vram:
            snapshot = guest.read(int(vram[-1],16) - guest.base, 8*1024*1024)
            if snapshot and guest.read(address,28) == h:
                (ev/f"picture-{pic:03d}.vram").write_bytes(snapshot)
    if pic in (1,150,300): print(f"picture {pic}, game frame {frame}, bytes {size}",flush=True)
    last = pic
    if last == 300: break
print(f"captured {last} complete pictures",flush=True)
sys.exit(last != 300)
