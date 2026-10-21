"""Read-only, non-atomic context samples for an already byte-bound QA program."""
import ctypes
import json
import os
from pathlib import Path
import re
import struct
import time


class Observer:
    @staticmethod
    def qa_safe(row):
        if not row or row.get("qa_frames", 0) < 30:
            return False
        game = row.get("global", {})
        player = row.get("player", {})
        return (game.get("rno", [])[:2] == [3, 0]
                and not (game.get("status", [0, 0])[1] & 0x10000000)
                and not row.get("event_start_cnt", 1) and not row.get("subscreen_type", 1)
                and player.get("rno", [1])[0] == 0 and bool(player.get("alive", 0) & 1))

    def __init__(self, cap, binding, layout):
        self.cap = cap
        self.binding = json.loads(binding.read_text())
        self.layout = json.loads(layout.read_text())
        if self.layout["elf_sha256"] != self.binding["elf_sha256"]:
            raise ValueError("layout and byte-bound program ELF differ")
        if self.binding["disc_program_sha256"] != self.binding["elf_binary_sha256"]:
            raise ValueError("program bytes were not bound")
        self.symbols = {k: int(v, 0) for k, v in self.binding["symbols"].items()}
        self.handle = None
        self.ram = None
        self.started = time.monotonic()
        self.last = None
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                          ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]

    def offset(self, typename, field):
        matches = [x for x in self.layout["found"][typename]["members"]
                   if x["name"].split(".")[-1] == field]
        if len(matches) != 1:
            raise ValueError(f"ambiguous or absent DWARF field {typename}.{field}")
        return matches[0]["offset"]

    @staticmethod
    def valid(address, size=1):
        return 0x8c000000 <= address and address + size <= 0x8d000000

    def read(self, address, fmt):
        size = struct.calcsize("<" + fmt)
        if not self.valid(address, size):
            raise ValueError(f"outside guest main RAM: {address:08x}+{size}")
        data = ctypes.create_string_buffer(size)
        count = ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, self.ram + address - 0x8c000000,
                                              data, size, ctypes.byref(count)) or count.value != size:
            raise OSError("incomplete read-only guest sample")
        values = struct.unpack("<" + fmt, data.raw)
        return values[0] if len(values) == 1 else list(values)

    def field(self, address, typename, field, fmt):
        return self.read(address + self.offset(typename, field), fmt)

    def model(self, address):
        return dict(ptr=hex(address), id=self.field(address, "cModel", "id", "B"),
                    type=self.field(address, "cModel", "type", "B"),
                    alive=self.field(address, "cModel", "be_flag", "I"),
                    rno=self.read(address + self.offset("cModel", "r_no_0"), "4B"),
                    pos=self.field(address, "cModel", "pos", "3f"),
                    ang=self.field(address, "cModel", "ang", "3f"),
                    hp=self.field(address, "cEm", "hp", "h"),
                    motion_ptr=hex(self.field(address + self.offset("cModel", "Motion"), "MotionWork", "pMot", "I")),
                    motion_frame=self.field(address + self.offset("cModel", "Motion"), "MotionWork", "Mot_frame", "f"))

    def sample(self):
        if self.handle is None:
            pidpath = self.cap / "flycast.pid"
            logpath = self.cap / "flycast.log"
            if not pidpath.exists() or not logpath.exists():
                return
            matches = re.findall(r"RAM\(16 MB\) ([0-9A-Fa-f]+)", logpath.read_text(errors="replace"))
            if not matches:
                return
            self.ram = int(matches[-1], 16)
            self.handle = self.kernel.OpenProcess(0x0010 | 0x0400, False, int(pidpath.read_text()))
            if not self.handle:
                raise OSError("cannot open owned emulator for read-only observation")
            path = ctypes.create_unicode_buffer(32768)
            length = ctypes.c_ulong(len(path))
            if not self.kernel.QueryFullProcessImageNameW(self.handle, 0, path, ctypes.byref(length)):
                raise OSError("cannot verify observer process identity")
            if os.path.normcase(os.path.abspath(path.value)) != os.path.normcase(str((self.cap / "flycast.exe").resolve())):
                raise ValueError("observer PID is not this evidence executable")
        row = dict(host_s=round(time.monotonic() - self.started, 3), non_atomic=True,
                   qa_frames=self.read(self.symbols["qa_frames"], "I"),
                   qa_flags=self.read(self.symbols["qa_flags"], "I"))
        pg = self.read(self.symbols["pG"], "I")
        if self.valid(pg, self.layout["found"]["GlobalWork"]["bytes"]):
            row["global"] = dict(ptr=hex(pg), rno=self.read(pg + self.offset("GlobalWork", "Rno0"), "4B"),
                                 frame=self.field(pg, "GlobalWork", "Frame_cnt", "I"),
                                 stop=self.field(pg, "GlobalWork", "Stop_flg", "I"),
                                 player_life=self.field(pg, "GlobalWork", "pl_life", "H"),
                                 player_life_max=self.field(pg, "GlobalWork", "pl_life_max", "H"),
                                 room=self.field(pg, "GlobalWork", "room_id", "H"),
                                 status=self.field(pg, "GlobalWork", "Status_flg", "4I"))
        pl = self.read(self.symbols["pPL"], "I")
        if self.valid(pl, self.layout["found"]["cPlayer"]["bytes"]):
            row["player"] = self.model(pl)
        row["pad"] = dict(button=self.field(self.symbols["Pad_data"], "PADStatus", "button", "H"),
                          stick=self.read(self.symbols["Pad_data"] + self.offset("PADStatus", "stickX"), "4b"),
                          triggers=self.read(self.symbols["Pad_data"] + self.offset("PADStatus", "triggerLeft"), "2B"))
        row["joy"] = dict(on=self.field(self.symbols["Joy"], "JOY", "on", "I"),
                          stick=self.read(self.symbols["Joy"] + self.offset("JOY", "stickX"), "4b"),
                          triggers=self.read(self.symbols["Joy"] + self.offset("JOY", "triggerLeft"), "2B"))
        row["event_start_cnt"] = self.field(self.symbols["SceSys"], "cSceSys", "event_start_cnt", "B")
        row["subscreen_type"] = self.field(self.symbols["SubScreenWk"], "SUB_SCREEN", "type", "i")
        current = self.field(self.symbols["EmMgr"], "cEmMgr", "pAlive", "I")
        seen = set()
        row["mendez"] = []
        while self.valid(current, self.layout["found"]["cEm"]["bytes"]) and current not in seen and len(seen) < 64:
            seen.add(current)
            if self.field(current, "cModel", "id", "B") == 0x35:
                row["mendez"].append(self.model(current))
            current = self.field(current, "cModel", "pNext", "I")
        row["manager_nodes_seen"] = len(seen)
        self.last = row
        with (self.cap / "read-only-state.jsonl").open("a") as out:
            out.write(json.dumps(row, allow_nan=False) + "\n")

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
