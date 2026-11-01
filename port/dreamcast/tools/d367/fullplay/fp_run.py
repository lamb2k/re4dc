"""fp_run.py: one bounded Flycast run of a GDI disc for the full-play gate (Windows Python; tools/d367/fullplay).

    python fp_run.py --disc <dir with disc.gdi + tracks> --cap <new evidence dir> --syms "<log> <head> <stage>"
                     [--seconds N] [--vmu <A1 image>] [--keys <key script>] [--stop REGEX] [--grace S]
                     [--period S] [--name NAME]

Same isolation as the playability harness (run-emulator.py / zipboot.py): a fresh capture dir from the harness
template (flycast.exe, emu.cfg, read_log.py, data/), its own GDB port, vsync off, the game's RAM log read by
read_log.py into run-output.txt. Disc tracks are hard-linked into the capture dir (no copy; delete only the links).
--keys drives the emulated controller from the host for a disc that has no padscript (the unmodified release):
each line `REGEX | DELAY_S | KEY[+KEY] [HOLD_S]` waits until REGEX appears in the log (after the previous step),
waits DELAY_S, then holds the keys (start a b x y up down left right). Keys are posted to Flycast's window
(WM_KEYDOWN/UP with scan codes, Flycast's default keyboard map), so the window need not have focus.
--stop ends the run GRACE seconds after REGEX first appears in the log (the segment's goal was reached).
"""
from pathlib import Path
import argparse, csv, ctypes, datetime, hashlib, json, os, re, shutil, socket, subprocess, sys, time
from ctypes import wintypes as W

TEMPLATE = Path(r'C:\Flycast-Evidence\re4-dreamcast\d367-harness-par')
FLOOR = 15 * 1024**3
CAPTURE_LIMIT = 768 * 1024**2
TRACKS = ('disc.gdi', 'track01.bin', 'track01.iso', 'track02.raw', 'track03.bin', 'track03.iso')
# Flycast default keyboard map (SDL scancodes via the window's WM_KEYDOWN scan code): set-1 scan code, extended
KEYS = dict(f5=(0x3F, 0), su=(0x17, 0), sd=(0x25, 0), sl=(0x24, 0), sr=(0x26, 0), lt=(0x21, 0), rt=(0x2F, 0),
            a=(0x2D, 0), b=(0x2E, 0), x=(0x1F, 0), y=(0x20, 0), start=(0x1C, 0),
            up=(0x48, 1), down=(0x50, 1), left=(0x4B, 1), right=(0x4D, 1))
VK = dict(f5=0x74, su=0x49, sd=0x4B, sl=0x4A, sr=0x4C, lt=0x46, rt=0x56, a=0x58, b=0x43, x=0x53, y=0x44, start=0x0D, up=0x26, down=0x28, left=0x25, right=0x27)

# RE4DC_EMU=console (opt-in): run flycast-console (GD-ROM/GDEMU DMA timing + optional SH-4 cache model) instead of the
# harness flycast.exe. CRASH REPRO ONLY, never timing. RE4DC_GD_* pass through the environment; RE4DC_CONSOLE_DYNAREC=no
# runs the interpreter (needed for the operand/instruction cache model). See docs/tools/flycast-console.md.
CONSOLE_EXE = Path(os.environ.get('RE4DC_CONSOLE_EXE',
                                  r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe'))

def emu_exe():
    if os.environ.get('RE4DC_EMU', '') == 'console':
        assert CONSOLE_EXE.exists(), 'RE4DC_EMU=console: no %s' % CONSOLE_EXE
        return CONSOLE_EXE
    return TEMPLATE / 'flycast.exe'

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def usage(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and p.name not in TRACKS + ('flycast.exe',))

def count_flycasts():
    t = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq flycast.exe', '/FO', 'CSV', '/NH'], text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    return sum(1 for r in csv.reader(t.splitlines()) if r and r[0].lower() == 'flycast.exe')

user32 = ctypes.WinDLL('user32', use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

def windows_of(pid):
    out = []
    def cb(h, _):
        p = W.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out

def press(pid, names, hold):
    hs = windows_of(pid)
    if not hs:
        return 0
    WM_KEYDOWN, WM_KEYUP = 0x100, 0x101
    for n in names:
        sc, ext = KEYS[n]
        lp = 1 | (sc << 16) | (ext << 24)
        for h in hs:
            user32.PostMessageW(h, WM_KEYDOWN, VK[n], lp)
    time.sleep(hold)
    for n in names:
        sc, ext = KEYS[n]
        lp = 1 | (sc << 16) | (ext << 24) | (1 << 30) | (1 << 31)
        for h in hs:
            user32.PostMessageW(h, WM_KEYUP, VK[n], lp)
    return len(hs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disc'); ap.add_argument('--cap', required=True); ap.add_argument('--syms', required=True)
    ap.add_argument('--seconds', type=int, default=300); ap.add_argument('--vmu'); ap.add_argument('--keys')
    ap.add_argument('--stop'); ap.add_argument('--grace', type=float, default=20); ap.add_argument('--period', type=int, default=0)
    ap.add_argument('--name', default='fullplay')
    ap.add_argument('--base', help='fp_master.sh base dir instead of --disc: its track03 + this segment fixtures')
    ap.add_argument('--warp'); ap.add_argument('--pad')
    ap.add_argument('--w11', help='/cd/dc/w11.txt fixture (W11_FIXTURE twin: die / save / file / mes)')
    ap.add_argument('--align', action='store_true',
                    help='hwmodel Flycast (HW_FLYCAST), interpreter + HWTRACE_ALIGN=1: misaligned guest accesses '
                         '(an address error on a Dreamcast, performed silently by Flycast) go to hwtrace.log')
    # Savestate chaining (lane castle31 10-26, opt-in; both off = the run is unchanged). A state bundle is a directory:
    # disc.state (Flycast's own savestate of disc.gdi, slot 0), vmu_A1.bin and state.json (the image key: track03 sha256
    # of the base and the syms of its program). --state-in refuses a bundle of another image.
    ap.add_argument('--state-in', help='restore this state bundle at boot (Dreamcast.AutoLoadState)')
    ap.add_argument('--state-out', help='close Flycast cleanly at the end and save a state bundle here (AutoSaveState)')
    a = ap.parse_args()
    assert 30 <= a.seconds <= 4000
    assert not (a.state_in or a.state_out) or a.base, '--state-in / --state-out need --base (the image key)'
    cap = Path(a.cap)
    maxfc = int(os.environ.get('RE4DC_MAX_FLYCASTS', '10'))
    cap.mkdir(parents=True, exist_ok=False)
    linked = {}
    fixtures = {}
    if a.base:
        base = Path(a.base); meta = json.loads((base / 'base.json').read_text())
        t1 = bytearray((base / 'track01-template.iso').read_bytes())
        assert not a.w11 or 'w11_lba' in meta, 'base %s has no w11.txt slot (fp_master.sh before 2026-10-14)' % base
        for key, src, lba in (('warp', a.warp, meta['warp_lba']), ('pad', a.pad, meta['pad_lba'])) + (
                (('w11', a.w11, meta['w11_lba']),) if 'w11_lba' in meta else ()):
            data = Path(src).read_bytes().replace(bytes([13]), b'') if src else b''
            limit = {'warp': 2047, 'pad': 4095, 'w11': 511}[key]   # dbgwarp_bridge / pad / sscrn_bridge buffers
            assert len(data) <= limit, '%s fixture %s is %d bytes (max %d)' % (key, src, len(data), limit)
            blob = data + bytes(meta['fixture_bytes'] - len(data))
            t1[lba * 2048:lba * 2048 + len(blob)] = blob
            fixtures[key] = dict(src=src, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            if src:
                shutil.copyfile(src, cap / ('fixture-' + key + '.txt'))
        (cap / 'track01.iso').write_bytes(bytes(t1))
        (cap / 'disc.gdi').write_text(meta['gdi'])
        for name in ('track02.raw', 'track03.iso'):
            os.link(base / name, cap / name)
        disc = base
        linked = dict(base=str(base), kind=meta['kind'], track03_sha256=(base / 'track03.sha256').read_text().strip())
    else:
        disc = Path(a.disc)
    for name in TRACKS if not a.base else ():
        if (disc / name).exists():
            if name == 'disc.gdi':
                shutil.copyfile(disc / name, cap / name)
            else:
                os.link(disc / name, cap / name)
            linked[name] = os.path.getsize(cap / name)
    assert a.base or 'disc.gdi' in linked, 'no disc.gdi in %s' % disc
    for name in ('emu.cfg', 'read_log.py', 'capture_ui_vram.py'):
        shutil.copyfile(TEMPLATE / name, cap / name)
    shutil.copyfile(emu_exe(), cap / 'flycast.exe')  # the template exe is at the NTFS 1024-link limit
    for src in (TEMPLATE / 'data').rglob('*'):
        if src.is_file():
            d = cap / src.relative_to(TEMPLATE); d.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, d)
    (cap / 'data').mkdir(exist_ok=True)
    assert a.vmu or (cap / 'data' / 'T0000_vmu_save_A1.bin').exists(), 'harness template %s has no data/T0000_vmu_save_A1.bin' % TEMPLATE
    if a.vmu:
        shutil.copyfile(a.vmu, cap / 'data' / 'T0000_vmu_save_A1.bin')
    state_key = None
    if a.state_in or a.state_out:
        state_key = dict(track03_sha256=linked['track03_sha256'], syms=a.syms.split()[:3])
    if a.state_in:
        sb = Path(a.state_in); sk = json.loads((sb / 'state.json').read_text())
        assert sk['track03_sha256'] == state_key['track03_sha256'] and sk['syms'] == state_key['syms'], \
            'state %s belongs to another image (%s / %s)' % (sb, sk['track03_sha256'][:16], ' '.join(sk['syms']))
        sd = cap / sk.get('state_file', 'data/disc.state'); sd.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sb / 'disc.state', sd)
        if not a.vmu:
            shutil.copyfile(sb / 'vmu_A1.bin', cap / 'data' / 'T0000_vmu_save_A1.bin')
    syms = a.syms.split()[:3]
    assert len(syms) == 3, syms
    (cap / 'syms.txt').write_text(' '.join(syms) + '\n')
    port = None
    for c in range(3263, 3400):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', c)); port = c; break
            except OSError:
                pass
    cfg = (cap / 'emu.cfg').read_text()
    cfg = re.sub(r'(?m)^Debug.GDBPort = \d+', 'Debug.GDBPort = %d' % port, cfg)
    cfg = cfg.replace('rend.vsync = yes', 'rend.vsync = no')
    if os.environ.get('FP_NOLIMIT') == '1':  # unthrottled JIT (emulated time unchanged; movies stay wall-timed)
        cfg = re.sub(r'(?m)^aica\.LimitFPS = \w+\n', '', cfg).replace('[config]\n', '[config]\naica.LimitFPS = no\n', 1)
    env = None
    if a.align:  # as hwready/mk-run-variant.py align (route-hw.sh): hwmodel exe, interpreter, HWTRACE_ALIGN=1
        hw = Path(os.environ.get('HW_FLYCAST', r'C:\Game Dev\Emulators\flycast-hwmodel\build-hwtrace\flycast.exe'))
        shutil.copyfile(hw, cap / 'flycast.exe')
        cfg = re.sub(r'(?m)^Dynarec\.Enabled = \w+\n', '', cfg).replace('[config]\n', '[config]\nDynarec.Enabled = no\n', 1)
        assert 'Dynarec.Enabled = no' in cfg
        env = dict(os.environ, HWTRACE_DIR=str(cap), HWTRACE_ALIGN='1')
    if os.environ.get('RE4DC_EMU', '') == 'console' and os.environ.get('RE4DC_CONSOLE_DYNAREC', 'yes') == 'no':
        cfg = cfg.replace('[config]\n', '[config]\nDynarec.Enabled = no\n', 1)
    if a.state_in:
        cfg = cfg.replace('[config]\n', '[config]\nDreamcast.AutoLoadState = yes\nDreamcast.SavestateSlot = 0\n', 1)
    if a.state_out or a.keys:  # --keys needs this map too: the stock map drives no analog (Leon only aims)
        # This capture's own keyboard map: Flycast's defaults (analog I/J/K/L = su/sl/sd/sr, triggers F/V) plus the
        # quick save (btn_quick_save) on F5, which fp_run posts to its own window at the end (never global input).
        if not a.state_in:
            cfg = cfg.replace('[config]\n', '[config]\nDreamcast.SavestateSlot = 0\n', 1)
        binds = [(27, 'btn_a'), (6, 'btn_b'), (22, 'btn_x'), (7, 'btn_y'), (40, 'btn_start'), (82, 'btn_dpad1_up'),
                 (81, 'btn_dpad1_down'), (80, 'btn_dpad1_left'), (79, 'btn_dpad1_right'), (9, 'btn_trigger_left'),
                 (25, 'btn_trigger_right'), (12, 'btn_analog_up'), (14, 'btn_analog_down'), (13, 'btn_analog_left'),
                 (15, 'btn_analog_right'), (43, 'btn_menu'), (62, 'btn_quick_save')]
        (cap / 'mappings').mkdir(exist_ok=True)
        (cap / 'mappings' / 'SDL_Keyboard.cfg').write_text(
            '[digital]\n' + ''.join('bind%d = %d:%s\n' % (i, k, n) for i, (k, n) in enumerate(binds)) +
            '\n[emulator]\nmapping_name = Keyboard\nversion = 3\n')
    if os.environ.get('RE4DC_MODEM_PPP') == '1':  # QA_LINK runs (lane link28): Flycast's own PPP peer, not DCNet
        cfg = re.sub(r'(?ms)^\[network\]\n(?:(?!\[).*\n)*', '', cfg) + '\n[network]\nDCNet = no\n'
    (cap / 'emu.cfg').write_text(cfg)
    steps = []
    if a.keys:
        for line in Path(a.keys).read_text().splitlines():
            line = line.split('#')[0].strip()
            if not line:
                continue
            rx, delay, key = [x.strip() for x in line.split('|')]
            k = key.split()
            steps.append(dict(rx=re.compile(rx if rx != '-' else ''), delay=float(delay), keys=k[0].split('+'), hold=float(k[1]) if len(k) > 1 else 0.15))
    stop = re.compile(a.stop) if a.stop else None
    rep = dict(name=a.name, status='STARTING', start_utc=now(), disc=str(disc), tracks=linked, seconds=a.seconds,
               vmu=a.vmu, keys=a.keys, stop=a.stop, fixtures=fixtures, errors=[], key_log=[], align=a.align,
               emu=os.environ.get('RE4DC_EMU', 'harness'),
               emu_env={k: v for k, v in os.environ.items() if k.startswith('RE4DC_GD_') or k.startswith('RE4DC_CONSOLE_')})
    while count_flycasts() >= maxfc:
        time.sleep(5)
    startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    serial = open(cap / 'serial.txt', 'xb'); log = open(cap / 'run-output.txt', 'xb'); logerr = open(cap / 'read-log.err', 'xb')
    proc = reader = None
    t0 = time.monotonic(); last_growth = t0; stop_at = None; lastshot = t0; pos = 0; text = ''; ktext = ''
    try:
        proc = subprocess.Popen([str(cap / 'flycast.exe'), 'disc.gdi'], cwd=cap, stdout=serial, stderr=subprocess.STDOUT,
                                startupinfo=startup, env=env)
        (cap / 'flycast.pid').write_text(str(proc.pid))
        reader = subprocess.Popen([sys.executable, str(cap / 'read_log.py'), *syms, str(a.seconds)], cwd=cap, stdout=log,
                                  stderr=logerr, creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps(dict(status='RUNNING', name=a.name, pid=proc.pid, cap=str(cap))), flush=True)
        si = 0; since = 0; matched_at = None
        while time.monotonic() - t0 < a.seconds + 30:
            free = shutil.disk_usage(cap).free
            if free < FLOOR:
                raise RuntimeError('disk floor: %d bytes free' % free)
            if usage(cap) > CAPTURE_LIMIT:
                raise RuntimeError('capture over %d bytes' % CAPTURE_LIMIT)
            if proc.poll() is not None:
                rep['early_emulator_exit'] = proc.returncode; break
            if reader.poll() is not None:
                rep['reader_exit'] = reader.returncode; break
            with open(cap / 'run-output.txt', 'rb') as f:
                f.seek(pos); new = f.read().decode('ascii', 'replace'); pos += len(new)
            if new:
                last_growth = time.monotonic()
            text = (text + new)[-200000:]
            ktext = (ktext + new)[-200000:]
            el = time.monotonic() - t0
            if si < len(steps):
                s = steps[si]
                if matched_at is None:
                    m = s['rx'].search(ktext)
                    if m:  # later steps only see log text after this match
                        matched_at = time.monotonic()
                        ktext = ktext[m.end():]
                if matched_at is not None and time.monotonic() - matched_at >= s['delay']:
                    n = press(proc.pid, s['keys'], s['hold'])
                    rep['key_log'].append(dict(step=si, keys=s['keys'], host_s=round(el, 1), windows=n))
                    si += 1; matched_at = None
            if stop is not None and stop_at is None and stop.search(text):
                stop_at = time.monotonic() + a.grace
                rep['stop_matched_s'] = round(el, 1)
            if stop_at is not None and time.monotonic() >= stop_at:
                rep['stopped'] = 'goal'; break
            if a.period and time.monotonic() - lastshot >= a.period:
                lastshot = time.monotonic()
                try:
                    sys.path.insert(0, str(cap))
                    import importlib.util
                    spec = importlib.util.spec_from_file_location('cap_ui', cap / 'capture_ui_vram.py')
                    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                    full = (cap / 'run-output.txt').read_text(errors='replace')
                    fb = re.findall(r'fb=[0-9a-f]+,[0-9a-f]+', full)
                    if fb:
                        shot = cap / 'shots' / ('t%04d' % int(el)); shot.mkdir(parents=True)
                        for nm in ('emu.cfg', 'flycast.log', 'flycast.pid'):
                            if (cap / nm).exists():
                                shutil.copyfile(cap / nm, shot / nm)
                        (shot / 'boot.log').write_text(fb[-1] + '\n', encoding='utf-16')
                        mod.capture(shot, shot / 'frames')
                except Exception as exc:
                    rep['errors'].append(dict(kind='screenshot', error=str(exc)))
            time.sleep(0.5)
        rep['status'] = 'RUN_COMPLETE'
        if si < len(steps):
            rep['keys_pending'] = len(steps) - si
    except Exception as exc:
        rep['status'] = 'RUN_FAILED'; rep['errors'].append(dict(kind='run', error=str(exc)))
    finally:
        if a.state_out and proc is not None and proc.poll() is None:
            # Quick save (F5 in this capture's own keyboard map, posted to its own window), then wait for the file.
            before = {q: q.stat().st_mtime for q in cap.rglob('*.state')}
            press(proc.pid, ['f5'], 0.2)
            st, t1 = None, time.monotonic()
            while time.monotonic() - t1 < 30 and st is None:
                time.sleep(1)
                for q in cap.rglob('*.state'):
                    if before.get(q) != q.stat().st_mtime and time.time() - q.stat().st_mtime > 1.5:
                        st = q
            if st is not None:
                ob = Path(a.state_out); ob.mkdir(parents=True, exist_ok=False)
                shutil.copyfile(st, ob / 'disc.state')
                shutil.copyfile(cap / 'data' / 'T0000_vmu_save_A1.bin', ob / 'vmu_A1.bin')
                (ob / 'state.json').write_text(json.dumps(dict(state_key, run=a.name, state_file=str(st.relative_to(cap)),
                                                               state_sha256=sha(ob / 'disc.state'), saved_utc=now()),
                                                          indent=1) + '\n')
                rep['state_out'] = str(ob)
            else:
                rep['errors'].append(dict(kind='state', error='no savestate file within 30 s of the quick save'))
        for c in (reader, proc):
            if c is not None and c.poll() is None:
                c.terminate()
                try:
                    c.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    c.kill(); c.wait(timeout=5)
        for f in (serial, log, logerr):
            f.close()
        for name in TRACKS[1:]:
            p = cap / name
            if p.exists():
                p.unlink()
        rep['log_idle_s'] = round(time.monotonic() - last_growth, 1)
        rep.update(end_utc=now(), elapsed_s=round(time.monotonic() - t0, 1), emulator_exited=proc is None or proc.poll() is not None)
        (cap / 'run-result.json').write_text(json.dumps(rep, indent=2) + '\n')
        print(json.dumps({k: rep.get(k) for k in ('name', 'status', 'elapsed_s', 'stopped', 'errors')}), flush=True)

if __name__ == '__main__':
    main()
