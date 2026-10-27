"""One read-only RAM snapshot from this run's recorded PID; never pauses the guest."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct
import time

p = argparse.ArgumentParser()
p.add_argument("evidence", type=Path)
p.add_argument("--frame-offset", type=lambda x:int(x, 16), required=True)
p.add_argument("--target-frame", type=int, default=0)
p.add_argument("--timeout", type=float, default=45)
a = p.parse_args()
pid = int((a.evidence / "flycast.pid").read_text().strip())
log = (a.evidence / "flycast.log").read_text(errors="replace")
ram = int(re.findall(r"RAM\(16 MB\) ([0-9A-Fa-f]+)", log)[-1], 16)
k = ctypes.windll.kernel32
k.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong)
k.OpenProcess.restype = ctypes.c_void_p
k.ReadProcessMemory.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t))
k.CloseHandle.argtypes = (ctypes.c_void_p,)
h = k.OpenProcess(0x0010 | 0x0400, False, pid)
assert h, "Recorded run PID is unavailable"
capacity = ctypes.c_ulong(32768)
executable = ctypes.create_unicode_buffer(capacity.value)
k.QueryFullProcessImageNameW.argtypes = (ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong))
assert k.QueryFullProcessImageNameW(h, 0, executable, ctypes.byref(capacity))
assert Path(executable.value).resolve() == (a.evidence / "flycast.exe").resolve(), executable.value
def read(off, size):
    buf = ctypes.create_string_buffer(size)
    count = ctypes.c_size_t()
    assert k.ReadProcessMemory(h, ram + off, buf, size, ctypes.byref(count)) and count.value == size
    return buf.raw
try:
    deadline = time.monotonic() + min(a.timeout, 55)
    while a.target_frame and struct.unpack("<I", read(a.frame_offset, 4))[0] < a.target_frame:
        assert time.monotonic() < deadline, "Target frame was not reached; guest run is not extended"
        time.sleep(.01)
    before = struct.unpack("<I", read(a.frame_offset, 4))[0]
    snapshot = read(0, 16 * 1024 * 1024)
    after = struct.unpack("<I", read(a.frame_offset, 4))[0]
finally:
    k.CloseHandle(h)
out = a.evidence / ("ram-snapshot-%d.bin" % before)
with out.open("xb") as stream:
    stream.write(snapshot)
record = dict(pid=pid, executable=executable.value, host_ram_base=ram, frame_before=before, frame_after=after,
              frame_in_snapshot=struct.unpack_from("<I", snapshot, a.frame_offset)[0],
              same_tick=before == after, sha256=hashlib.sha256(snapshot).hexdigest(),
              bytes=len(snapshot), time_unix=time.time(),
              scope="Single read-only external ReadProcessMemory capture; no pause or guest changes; bytes may race within this tick")
out.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
