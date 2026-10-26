"""Read the game's RAM boot log (platform/mem.cpp re4dc_logbuf) out of the
running Flycast process.

    read_log.py <logbuf-offset> <head-offset> <stage-offset> [poll-seconds]

Offsets are RAM offsets (symbol address - 0x8C000000, from `sh-elf-nm`).
Polls until the process exits or the poll time is over, printing new text as
it appears and the stage word at the end.
"""
import ctypes, os, re, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PID = int(open(os.path.join(HERE, "flycast.pid"), encoding="utf-8").read())
LOG_SIZE = 0x10000

def ram_base():
    for _ in range(6000):
        try:
            log = open(os.path.join(HERE, "flycast.log"), encoding="utf-8", errors="ignore").read()
            m = re.findall(r"RAM\(16 MB\) ([0-9A-Fa-f]+)", log)
            if m:
                return int(m[-1], 16)
        except OSError:
            pass
        time.sleep(0.005)
    raise SystemExit("no RAM base in flycast.log")

RAM = ram_base()
k32 = ctypes.windll.kernel32
handle = k32.OpenProcess(0x0010 | 0x0400, False, PID)
nread = ctypes.c_size_t(0)

def read(offset, count):
    b = ctypes.create_string_buffer(count)
    ok = k32.ReadProcessMemory(handle, ctypes.c_void_p(RAM + offset), b, count, ctypes.byref(nread))
    return b.raw if ok else None

buf_off = int(sys.argv[1], 0)
# LOG_PLAY_KB play images (platform/mem.cpp RE4DC_LOG_RING_HDR): 32 bytes before the ring hold "LGSZ", its complement
# and the ring size, written with the first log byte. Absent (older images, test builds): the 64 KB ring.
def ring_size():
    w = read(buf_off - 32, 12)
    if w:
        m, nm, size = struct.unpack("<III", w)
        if m == 0x5A53474C and nm == (~m & 0xFFFFFFFF) and 0 < size <= 0x10000:
            return size
    return 0x10000
head_off = int(sys.argv[2], 0)
stage_off = int(sys.argv[3], 0)
poll = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
# RE4DC_LOG_STOP=<frame-word-offset>:<frame> (hwtrace-run.ps1 -Tail): stop once the guest's frame word
# (re4dc_pcs LAST_FRAME) reaches <frame>, after one more full drain of the log, so the records written
# after the hwtrace window's last frame are kept (the emulator's own exit lost the last tick).
stop_off = stop_frame = None
if os.environ.get("RE4DC_LOG_STOP"):
    a, b = os.environ["RE4DC_LOG_STOP"].split(":")
    stop_off, stop_frame = int(a, 0), int(b, 0)
stopping = False
started = time.time()
end = started + poll
reason = "deadline"
print("[capture start=%s budget=%s]" % (started,poll),flush=True)
shown = 0
last_stage = None
# Only whole lines are printed: the guest may be mid-append when the head is read, and the
# "[stage N]" marker printed below would otherwise land inside that line (a false STRICT REJECT).
pending = ""
# RE4DC_LOG_STOP_TICK=N (logic-trace runs, dettrace 2026-10-13): end the capture once tick N's records are
# complete (the LT line of tick N+1 was read), so every run covers the same emulated window under any host load.
stop_tick = int(os.environ["RE4DC_LOG_STOP_TICK"]) if os.environ.get("RE4DC_LOG_STOP_TICK") else None
overruns = 0
ring_known = False
while time.time() < end:
    h = read(head_off, 4)
    if h is None:
        # Not yet committed (the guest has not touched the page) or gone.
        code = ctypes.c_ulong(0)
        k32.GetExitCodeProcess(handle, ctypes.byref(code))
        if code.value != 259:  # STILL_ACTIVE
            reason = "process-exited"
            print("[process exited, code %d elapsed=%.3f]" % (code.value,time.time()-started))
            break
        time.sleep(0.05)
        continue
    head = struct.unpack("<I", h)[0]
    if head < shown:
        print("[log head decreased: reset or process teardown; not proof of guest reboot]")
        shown = 0
        pending = ""
    if head and not ring_known:
        LOG_SIZE = ring_size(); ring_known = True
        if LOG_SIZE != 0x10000:
            print("[log ring %d bytes]" % LOG_SIZE, flush=True)
    if head > shown:
        if head - shown > LOG_SIZE:
            # The guest lapped the ring before it was read: text is lost and a trace run is invalid.
            print("[LOG OVERRUN lost=%d bytes at head=%d]" % (head - shown - LOG_SIZE, head), flush=True)
            overruns += 1
            shown = head - LOG_SIZE
            pending = ""
        data = read(buf_off, LOG_SIZE)
        h2 = read(head_off, 4)
        if h2 is not None and struct.unpack("<I", h2)[0] - shown > LOG_SIZE:
            # the guest overwrote the oldest unread bytes while the ring was being copied
            print("[LOG OVERRUN during copy at head=%d]" % struct.unpack("<I", h2)[0], flush=True)
            overruns += 1
        chunk = bytes(data[i % LOG_SIZE] for i in range(shown, head))
        text = pending + chunk.decode("ascii", "replace")
        cut = text.rfind("\n") + 1
        pending = text[cut:]
        if cut:
            sys.stdout.write(text[:cut])
            sys.stdout.flush()
            if stop_tick is not None and ("\nLT t=%d " % (stop_tick + 1)) in ("\n" + text[:cut]):
                reason = "stop-tick"
                print("[stop tick %d complete]" % stop_tick, flush=True)
                shown = head
                break
        shown = head
    s = read(stage_off, 4)
    stage = struct.unpack("<I", s)[0] if s else None
    if stage != last_stage:
        print("[stage %s]" % stage)
        last_stage = stage
    if stopping:
        reason = "stop-frame"
        break
    if stop_off is not None:
        f = read(stop_off, 4)
        if f is not None and struct.unpack("<I", f)[0] >= stop_frame:
            stopping = True
            print("[stop frame %d reached; final drain]" % stop_frame)
            time.sleep(0.05)
            continue
    time.sleep(0.005)
if pending:
    print(pending)  # the last, unterminated line
print("[end: head=%d stage=%s overruns=%d]" % (shown, last_stage, overruns))

print("[capture stop reason=%s elapsed=%.3f]" % (reason,time.time()-started),flush=True)
