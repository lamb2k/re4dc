"""Read D314 UI buffers using the existing D221 VRAM bank/RGB565 method.
Windows/Flycast diagnostic only: requires rend.EmulateFramebuffer=yes, the
matching executable's logged KOS framebuffer pointers, and 640x480 RGB565.
Does not freeze the emulator or establish exact simulation-tick correspondence.
"""
import numpy as np
from PIL import Image
import argparse
import ctypes
import re
from pathlib import Path

VRAM_SIZE = 8 * 1024 * 1024

def framebuffer_offset(pointer):
    # Pinned KOS pvr_get_frame_buffer: PVR_RAM_BASE + frame_offset * 2.
    delta = pointer - 0xa5000000
    if delta < 0 or delta >= 2 * VRAM_SIZE or delta % 8:
        raise ValueError("not an aligned KOS framebuffer pointer")
    return delta // 2

def map_32bit_vram(offset):
    if not 0 <= offset < VRAM_SIZE:
        raise ValueError("offset outside VRAM")
    bank = 1 if offset & 0x400000 else 0
    return (offset & 3) | ((offset & 0x3ffffc) * 2) | (bank * 4)

def decode_rgb565(vram, offset, width=640, height=480):
    size = width * height * 2
    if len(vram) != VRAM_SIZE or offset % 4 or size % 4 or offset + size > VRAM_SIZE:
        raise ValueError("invalid framebuffer extent")
    # Same D221 bank mapping, grouped in four-byte words; no guest memory writes.
    logical = np.arange(offset // 4, (offset + size) // 4, dtype=np.uint32)
    physical = ((logical & 0xfffff) << 1) | (logical >> 20)
    words = np.frombuffer(vram, dtype="<u4")[physical]
    pixels = np.frombuffer(words.tobytes(), dtype="<u2")
    rgb = np.empty((width * height, 3), dtype=np.uint8)
    rgb[:, 0] = ((pixels >> 11) & 31) * 255 // 31
    rgb[:, 1] = ((pixels >> 5) & 63) * 255 // 63
    rgb[:, 2] = (pixels & 31) * 255 // 31
    return rgb.tobytes()


def capture(evidence, output):
    from PIL import Image
    config = (evidence / "emu.cfg").read_text()
    if not re.search(r"(?mi)^rend.EmulateFramebuffer\s*=\s*(yes|true|1)\s*$", config):
        raise ValueError("capture requires rend.EmulateFramebuffer=yes")
    boot = (evidence / "boot.log").read_text(encoding="utf-16")
    front, back = re.findall(r"fb=([0-9a-f]+),([0-9a-f]+)", boot)[-1]
    offsets = [framebuffer_offset(int(s, 16)) for s in (front, back)]
    log = (evidence / "flycast.log").read_text(errors="replace")
    address = int(re.findall(r"VRAM64\(8 MB\) ([0-9A-Fa-f]+)", log)[-1], 16)
    pid = int((evidence / "flycast.pid").read_text())
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        data = ctypes.create_string_buffer(VRAM_SIZE)
        count = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, data, VRAM_SIZE, ctypes.byref(count)) or count.value != VRAM_SIZE:
            raise OSError("incomplete VRAM read")
    finally:
        kernel.CloseHandle(handle)
    # Refuse an existing destination: accepted captures are immutable.
    output.mkdir(parents=True, exist_ok=False)
    for index, offset in enumerate(offsets):
        Image.frombytes("RGB", (640, 480), decode_rgb565(data.raw, offset)).save(output / f"fb{index}.png")
    return offsets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(capture(args.evidence, args.output))
