#!/usr/bin/env python3
"""consoleloop.py: send a program to the Dreamcast over the QA link, run it, collect its report (lane eng-loop,
2026-11-19). Python 3 standard library plus the ssh client. Design: port/dreamcast/docs/engine/CONSOLE_LOOP.md.

The console runs the loader disc (port/dreamcast/engine/loader). It dials the DreamPi and beacons HELLO on UDP 52060.
This tool reaches it through a relay piped to `ssh <pi> python3` (nothing is installed on the Pi; qalink_pi.py on
52040 can keep running), or straight over UDP (--udp: Flycast's modem emulation, a routable console, the host tests).

  python consoleloop.py --pi re4pi status                     the loader's beacon: state, boot count, pending report
  python consoleloop.py --pi re4pi send bench.elf             send and verify only (no run)
  python consoleloop.py --pi re4pi run bench.elf --args "cross farm" --deadline 900 --out results/
  python consoleloop.py --pi re4pi report --out results/      collect a pending report
  python consoleloop.py --udp 127.0.0.1:52062 --bind 52060 run test.elf   (Flycast: LINK.TXT host <PC>, lport 52062)

Program: an ELF (its PT_LOAD segments, loaded at 0x8C010000) or a raw 1ST_READ-style .bin. Deflate level 9 unless
--no-compress. Every run writes <out>/run-<session>.json (timings, rates, retransmits, verdict) and the report.

Controls (tests): --corrupt stream|payload|declared sends a damaged image that the console must refuse, then RUN
anyway; the run must end with the refusal and no EXEC.
"""
import argparse, base64, hashlib, json, os, queue, random, shlex, socket, struct, subprocess, sys, threading, time, zlib

MAGIC = b'CL'
VERSION = 1
HDR = 16
DGRAM_MAX = 1200
CHUNK = 1024
PORT = 52060
LOAD_ADDR = 0x8C010000
HANDOFF_ADDR = 0x8CFE0000
IMAGE_END = HANDOFF_ADDR - 0x11000   # the loader's stack (arch_exec_at's trampoline) sits below the hand-off area

HELLO, ACK, VERDICT, REPORT, EXEC, ERR = 0x01, 0x02, 0x03, 0x04, 0x05, 0x06
LOAD, DATA, RUN, REPQ, REPDONE, PING, ABORT, VERIFY = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17
TYPE_NAMES = {HELLO: 'HELLO', ACK: 'ACK', VERDICT: 'VERDICT', REPORT: 'REPORT', EXEC: 'EXEC', ERR: 'ERR', LOAD: 'LOAD',
              DATA: 'DATA', RUN: 'RUN', REPQ: 'REPQ', REPDONE: 'REPDONE', PING: 'PING', ABORT: 'ABORT',
              VERIFY: 'VERIFY'}
ERRORS = {0: 'ok', 1: 'stream crc', 2: 'inflate', 3: 'raw length', 4: 'sha256', 5: 'size', 6: 'load address',
          7: 'no memory', 8: 'not verified', 9: 'unknown session', 10: 'bad load', 11: 'codec', 12: 'no report',
          13: 'busy'}
STATES = {0: 'IDLE', 1: 'RECEIVING', 2: 'VERIFIED', 3: 'FAILED', 4: 'EXEC'}
RUN_STATES = {0: 'NONE', 1: 'RUNNING', 2: 'DONE', 3: 'CRASHED', 4: 'TIMEOUT', 5: 'LOST'}


# ------------------------------------------------------------------------------------------------ framing
def frame(type_, session, a=0, b=0, payload=b''):
    assert len(payload) <= DGRAM_MAX - HDR - 4
    h = MAGIC + bytes([VERSION, type_]) + struct.pack('<IIHH', session & 0xFFFFFFFF, a & 0xFFFFFFFF, len(payload), b)
    body = h + payload
    return body + struct.pack('<I', zlib.crc32(body) & 0xFFFFFFFF)


def unframe(d):
    """(type, session, a, b, payload) or None when the datagram fails its checks."""
    if len(d) < HDR + 4 or len(d) > DGRAM_MAX or d[:2] != MAGIC or d[2] != VERSION:
        return None
    session, a, ln, b = struct.unpack_from('<IIHH', d, 4)
    if HDR + ln + 4 != len(d):
        return None
    if zlib.crc32(d[:HDR + ln]) & 0xFFFFFFFF != struct.unpack_from('<I', d, HDR + ln)[0]:
        return None
    return d[3], session, a, b, d[HDR:HDR + ln]


def parse_hello(p):
    v = struct.unpack_from('<16I', p, 0)
    keys = ('boot_count', 'uptime_ms', 'state', 'session', 'have', 'nchunks', 'rx_bytes', 'rx_bad', 'report_run',
            'report_state', 'report_len', 'report_crc', 'report_exit', 'console_ip', 'max_raw', 'verdict')
    h = dict(zip(keys, v))
    h['report_exit'] = struct.unpack('<i', struct.pack('<I', h['report_exit']))[0]
    h['verdict'] = struct.unpack('<i', struct.pack('<I', h['verdict']))[0]
    h['build'] = p[64:96].split(b'\0', 1)[0].decode('latin-1')
    h['console_ip'] = socket.inet_ntoa(struct.pack('<I', h['console_ip']))
    return h


# ------------------------------------------------------------------------------------------------ program images
def elf_image(data):
    """Flat image of an SH-4 ELF's PT_LOAD file bytes (BSS excluded: KallistiOS clears it): (load address, bytes)."""
    if data[:4] != b'\x7fELF' or data[4] != 1 or data[5] != 1:
        raise ValueError('not a 32-bit little-endian ELF')
    phoff, = struct.unpack_from('<I', data, 28)
    phentsize, phnum = struct.unpack_from('<HH', data, 42)
    segs = []
    for i in range(phnum):
        t, off, va, pa, fs, ms, fl, al = struct.unpack_from('<8I', data, phoff + i * phentsize)
        if t == 1 and fs:
            segs.append((pa & 0x1FFFFFFF | 0x80000000 if pa else va, data[off:off + fs]))
    if not segs:
        raise ValueError('no loadable segment')
    lo = min(s[0] for s in segs)
    hi = max(s[0] + len(s[1]) for s in segs)
    img = bytearray(hi - lo)
    for va, b in segs:
        img[va - lo:va - lo + len(b)] = b
    return lo, bytes(img)


def load_program(path):
    data = open(path, 'rb').read()
    if data[:4] == b'\x7fELF':
        lo, img = elf_image(data)
        if lo != LOAD_ADDR:
            raise ValueError('%s loads at %08x, the loader runs programs at %08x' % (path, lo, LOAD_ADDR))
        return img
    return data


class Image:
    def __init__(self, raw, compress=True, corrupt=None):
        self.raw = raw
        self.sha = hashlib.sha256(raw).digest()
        self.codec = 1 if compress else 0
        self.comp = self._pack(raw)
        self.crc = zlib.crc32(self.comp) & 0xFFFFFFFF
        self.corrupt = corrupt
        if corrupt == 'stream':      # damaged after the stream CRC was taken: the console's stream CRC must refuse it
            self.comp = flip(self.comp)
        elif corrupt == 'payload':   # a self-consistent stream of different bytes under the declared SHA-256
            self.comp = self._pack(flip(raw))
            self.crc = zlib.crc32(self.comp) & 0xFFFFFFFF
        elif corrupt == 'declared':  # the right bytes, the wrong declared hash
            self.sha = hashlib.sha256(raw + b'x').digest()
        elif corrupt:
            raise ValueError('--corrupt stream|payload|declared')
        self.nchunks = (len(self.comp) + CHUNK - 1) // CHUNK

    def _pack(self, raw):
        if not self.codec:
            return raw
        c = zlib.compressobj(9, zlib.DEFLATED, -15, 9)
        return c.compress(raw) + c.flush()

    def chunk(self, i):
        return self.comp[i * CHUNK:(i + 1) * CHUNK]

    def load_payload(self, args='', deadline=0, flags=0):
        a = args.encode('latin-1')[:512]
        p = struct.pack('<IIIIBBHI', len(self.comp), len(self.raw), CHUNK, self.nchunks, self.codec, flags,
                        deadline & 0xFFFF, LOAD_ADDR) + self.sha + struct.pack('<IHH', self.crc, len(a), 0)
        assert len(p) == 64
        return p + a


def flip(b):
    b = bytearray(b)
    i = len(b) // 2
    b[i] ^= 0x5A
    return bytes(b)


# ------------------------------------------------------------------------------------------------ transports
RELAY = r'''
import base64, os, select, socket, sys
port = int(sys.argv[1]) if len(sys.argv) > 1 else 52060
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', port))
peer = None
w = sys.stdout
w.write('I relay up udp %d\n' % port); w.flush()
buf = b''
while True:
    r, _, _ = select.select([s, 0], [], [], 5.0)
    if s in r:
        d, a = s.recvfrom(4096)
        if a != peer:
            peer = a
            w.write('I console %s:%d\n' % a)
        w.write('R ' + base64.b64encode(d).decode() + '\n'); w.flush()
    if 0 in r:
        c = os.read(0, 65536)
        if not c:
            break
        buf += c
        while b'\n' in buf:
            line, buf = buf.split(b'\n', 1)
            if line.startswith(b'S ') and peer:
                s.sendto(base64.b64decode(line[2:]), peer)
'''


class UdpTransport:
    def __init__(self, remote, bind_port):
        host, _, port = remote.partition(':')
        self.remote = (host, int(port or PORT))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1' if host.startswith('127.') else '0.0.0.0', bind_port))
        self.peer = None

    def send(self, d):
        self.s.sendto(d, self.peer or self.remote)

    def recv(self, timeout):
        self.s.settimeout(max(timeout, 0.001))
        try:
            d, a = self.s.recvfrom(4096)
            return d
        except (socket.timeout, BlockingIOError):
            return None
        except ConnectionResetError:   # Windows: ICMP port unreachable
            return None

    def close(self):
        self.s.close()


class SshRelayTransport:
    def __init__(self, pi, port, log):
        code = base64.b64encode(RELAY.encode()).decode()
        remote = 'python3 -u -c %s %d' % (shlex.quote('import base64;exec(base64.b64decode("%s"))' % code), port)
        self.p = subprocess.Popen(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o',
                                   'ServerAliveInterval=15', pi, remote],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
        self.q = queue.Queue()
        self.log = log
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        for line in self.p.stdout:
            line = line.rstrip(b'\r\n')
            if line.startswith(b'R '):
                self.q.put(base64.b64decode(line[2:]))
            elif line.startswith(b'I '):
                self.log('relay: ' + line[2:].decode('latin-1'))
        self.q.put(None)

    def send(self, d):
        self.p.stdin.write(b'S ' + base64.b64encode(d) + b'\n')
        self.p.stdin.flush()

    def recv(self, timeout):
        try:
            d = self.q.get(timeout=max(timeout, 0.001))
        except queue.Empty:
            return None
        if d is None:
            raise RuntimeError('the ssh relay ended (is the Pi reachable, and python3 on it?)')
        return d

    def close(self):
        try:
            self.p.stdin.close()
            self.p.terminate()
        except OSError:
            pass


# ------------------------------------------------------------------------------------------------ the session
class Loop:
    def __init__(self, transport, log=print, verbose=False):
        self.t = transport
        self.log = log
        self.verbose = verbose
        self.hello = None
        self.stats = {'tx_pkts': 0, 'tx_bytes': 0, 'rx_pkts': 0, 'rx_bytes': 0, 'rx_bad': 0}

    def send(self, type_, session, a=0, b=0, payload=b''):
        d = frame(type_, session, a, b, payload)
        self.t.send(d)
        self.stats['tx_pkts'] += 1
        self.stats['tx_bytes'] += len(d)

    def recv(self, timeout):
        d = self.t.recv(timeout)
        if d is None:
            return None
        self.stats['rx_pkts'] += 1
        self.stats['rx_bytes'] += len(d)
        m = unframe(d)
        if m is None:
            self.stats['rx_bad'] += 1
            return None
        if m[0] == HELLO and len(m[4]) >= 96:
            self.hello = parse_hello(m[4])
            self.hello['at'] = time.time()
        if self.verbose:
            self.log('  <- %s s=%08x a=%d b=%d len=%d' % (TYPE_NAMES.get(m[0], m[0]), m[1], m[2], m[3], len(m[4])))
        return m

    def wait(self, pred, timeout, every=None, poke=None):
        """Receives until pred(msg) returns non-None; calls poke() every `every` seconds."""
        end = time.time() + timeout
        last = 0.0
        while time.time() < end:
            if poke and every and time.time() - last >= every:
                poke()
                last = time.time()
            m = self.recv(min(0.2, max(0.0, end - time.time())))
            if m is not None:
                r = pred(m)
                if r is not None:
                    return r
        return None

    def wait_hello(self, timeout, pred=lambda h: True):
        def p(m):
            if m[0] == HELLO and self.hello and pred(self.hello):
                return self.hello
            return None
        return self.wait(p, timeout, every=5.0, poke=lambda: self.send(PING, 0))

    # -------------------------------------------------------------------------------------------- transfer
    def transfer(self, img, session, args='', deadline=0, link_wait=180.0):
        t0 = time.time()
        acked = bytearray(img.nchunks)
        sent_at, sent_n, sent_seq = {}, {}, {}
        inflight = set()
        retx = []                 # chunks to send again, oldest first
        seq = 0                   # send order, for loss detection from the ack bitmap
        window, wmax, wmin = 4.0, 16.0, 2.0
        srtt, rto, min_rtt = None, 2.0, 1e9
        resent = fast = timeouts = 0
        cut_at = 0.0
        last_ack = time.time()
        ack_info = {}
        load = img.load_payload(args, deadline)

        def handshake(wait_s):
            return self.wait(lambda m: m if m[1] == session and m[0] in (ACK, VERDICT, ERR) else None, wait_s,
                             every=2.0, poke=lambda: self.send(LOAD, session, payload=load))

        def cut(now):
            nonlocal window, cut_at
            if now - cut_at > (srtt or 1.0):
                window = max(wmin, window / 2)
                cut_at = now

        m = handshake(30.0)
        if m is None:
            raise RuntimeError('no answer to LOAD within 30 s')
        pending = [m]
        nxt = 0
        verdict = None
        while True:
            for m in pending:
                if m[0] == ERR:
                    raise RuntimeError('console refused the load: %s' % ERRORS.get(m[2], m[2]))
                if m[0] == VERDICT:
                    verdict = (m[2], m[4].decode('latin-1'))
                if m[0] == ACK and m[1] == session:
                    last_ack = time.time()
                    cum = m[2]
                    have, bad, dup, n = struct.unpack_from('<IIII', m[4], 0)
                    ack_info = {'have': have, 'bad_crc': bad, 'dup': dup}
                    bm = m[4][16:16 + m[3]]
                    if have < sum(acked):
                        # the console holds less than it acknowledged before (it rebooted): start from its view
                        self.log('console holds %d chunks, %d were acknowledged: restarting from its view' %
                                 (have, sum(acked)))
                        acked = bytearray(img.nchunks)
                        inflight.clear()
                        retx.clear()
                        sent_n.clear()
                        nxt = 0
                    newly = [i for i in range(min(cum, img.nchunks)) if not acked[i]]
                    for k in range(len(bm) * 8):
                        i = cum + k
                        if i < img.nchunks and (bm[k >> 3] >> (k & 7)) & 1 and not acked[i]:
                            newly.append(i)
                    now = time.time()
                    top = -1
                    for i in newly:
                        acked[i] = 1
                        inflight.discard(i)
                        top = max(top, sent_seq.get(i, -1))
                        if sent_n.get(i) == 1:
                            sample = now - sent_at[i]
                            srtt = sample if srtt is None else 0.875 * srtt + 0.125 * sample
                            min_rtt = min(min_rtt, sample)
                        # grow while the line's queue stays under 1 s; shrink past 2 s (a modem line has a deep
                        # queue: filling it only delays the acks and ends in tail drops)
                        queue_s = (srtt or 0.0) - min_rtt
                        if queue_s < 1.0:
                            window = min(wmax, window + 1.0 / window)
                        elif queue_s > 2.0:
                            window = max(wmin, window - 1.0 / window)
                    if srtt is not None:
                        rto = max(1.5, 2.5 * srtt)
                    # a chunk sent 3 or more sends before one now acknowledged was lost: send it again now
                    for i in sorted(inflight, key=lambda j: sent_seq[j]):
                        if sent_seq[i] + 3 <= top:
                            inflight.discard(i)
                            retx.append(i)
                            fast += 1
                            cut(now)
            pending = []
            if verdict is not None:
                break
            now = time.time()
            for i in sorted(inflight, key=lambda j: sent_seq[j]):
                if now - sent_at[i] > rto:
                    inflight.discard(i)
                    retx.append(i)
                    timeouts += 1
                    cut(now)
            if all(acked):
                m = self.wait(lambda m: m if m[1] == session and m[0] in (VERDICT, ERR) else None, 10.0,
                              every=2.0, poke=lambda: self.send(VERIFY, session))
                if m is None:
                    raise RuntimeError('all chunks acknowledged but no verdict')
                pending = [m]
                continue
            while len(inflight) < int(window):
                i = None
                while retx:
                    j = retx.pop(0)
                    if not acked[j] and j not in inflight:
                        i = j
                        break
                if i is None:
                    while nxt < img.nchunks and (acked[nxt] or nxt in inflight or sent_n.get(nxt)):
                        nxt += 1
                    if nxt >= img.nchunks:
                        break
                    i = nxt
                    nxt += 1
                if sent_n.get(i):
                    resent += 1
                self.send(DATA, session, i, 0, img.chunk(i))
                sent_at[i] = time.time()
                sent_n[i] = sent_n.get(i, 0) + 1
                sent_seq[i] = seq
                seq += 1
                inflight.add(i)
            if time.time() - last_ack > 10.0:
                # quiet line: the console may be redialling. Wait for its beacon, then resume with LOAD
                self.log('no ack for 10 s (have %d/%d): waiting for the loader, then resuming' % (sum(acked), img.nchunks))
                if self.wait_hello(link_wait) is None:
                    raise RuntimeError('the loader did not come back within %.0f s' % link_wait)
                m = handshake(30.0)
                if m is None:
                    raise RuntimeError('no answer to the resume LOAD')
                retx.extend(sorted(i for i in inflight))
                inflight.clear()
                pending = [m]
                last_ack = time.time()
                continue
            m = self.recv(0.05)
            if m is not None:
                pending = [m]
        t1 = time.time()
        res = {'session': '%08x' % session, 'raw_bytes': len(img.raw), 'comp_bytes': len(img.comp),
               'chunks': img.nchunks, 'resent': resent, 'fast_resends': fast, 'timeouts': timeouts, 'seconds': round(t1 - t0, 3),
               'goodput_Bps': round(len(img.comp) / max(t1 - t0, 1e-6), 1),
               'raw_Bps': round(len(img.raw) / max(t1 - t0, 1e-6), 1),
               'srtt_s': round(srtt or 0, 3), 'min_rtt_s': round(min_rtt if min_rtt < 1e9 else 0, 3), 'final_window': round(window, 2), 'console_ack': ack_info,
               'verdict': verdict[0], 'verdict_text': verdict[1]}
        return res

    def run_verified(self, session):
        r = self.wait(lambda m: m if m[1] == session and m[0] in (EXEC, ERR) else None, 15.0,
                      every=2.0, poke=lambda: self.send(RUN, session))
        if r is None:
            return 'no answer'
        return 'exec' if r[0] == EXEC else 'refused: %s' % ERRORS.get(r[2], r[2])

    def fetch_report(self, h, out_dir):
        run, length, crc = h['report_run'], h['report_len'], h['report_crc']
        blocks = {}
        need = [o for o in range(0, max(length, 1), CHUNK)] if length else []
        tries = 0
        while need and tries < 30:
            tries += 1
            first = need[0]
            count = min(8, len(need))
            self.send(REPQ, run, first, count)
            end = time.time() + 3.0 + count * 1.0
            last = None
            while time.time() < end:
                m = self.recv(0.2)
                if m and m[0] == REPORT and m[1] == run:
                    blocks[m[2]] = m[4]
                    last = time.time()
                    if all(o in blocks for o in need[:count]):
                        break
                elif last and time.time() - last > 2.5:
                    break   # the rest of this request was lost: ask again
                if m and m[0] == ERR and m[1] == run:
                    raise RuntimeError('console: %s' % ERRORS.get(m[2], m[2]))
            need = [o for o in need if o not in blocks]
        if need:
            raise RuntimeError('report incomplete after %d requests' % tries)
        data = b''.join(blocks[o] for o in sorted(blocks))[:length]
        ok = (zlib.crc32(data) & 0xFFFFFFFF) == crc and len(data) == length
        path = None
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, 'report-%08x.txt' % run)
            open(path, 'wb').write(data)
        if ok:
            self.wait(lambda m: m if m[0] == HELLO and self.hello['report_state'] == 0 else None, 10.0,
                      every=2.0, poke=lambda: self.send(REPDONE, run))
        return {'run': '%08x' % run, 'state': RUN_STATES.get(h['report_state'], h['report_state']),
                'exit': h['report_exit'], 'bytes': len(data), 'crc_ok': ok, 'path': path,
                'text_head': data[:400].decode('latin-1')}


def describe(h):
    return ('loader "%s" boot %d up %.0f s ip %s state %s session %08x %d/%d chunks; last run %08x %s, report %d bytes' %
            (h['build'], h['boot_count'], h['uptime_ms'] / 1000.0, h['console_ip'], STATES.get(h['state'], h['state']),
             h['session'], h['have'], h['nchunks'], h['report_run'], RUN_STATES.get(h['report_state'], '?'),
             h['report_len']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pi', default=os.environ.get('QALINK_PI'), help='ssh target of the DreamPi (relay mode)')
    ap.add_argument('--udp', help='host:port of the console (direct mode, no relay)')
    ap.add_argument('--bind', type=int, default=PORT, help='local UDP port in direct mode (default %d)' % PORT)
    ap.add_argument('--port', type=int, default=PORT, help='the loader port on the Pi (relay mode)')
    ap.add_argument('-v', '--verbose', action='store_true')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    for name in ('send', 'run'):
        s = sub.add_parser(name)
        s.add_argument('program')
        s.add_argument('--args', default='')
        s.add_argument('--deadline', type=int, default=0, help='seconds the client library allows the program')
        s.add_argument('--no-compress', action='store_true')
        s.add_argument('--corrupt', choices=('stream', 'payload', 'declared'))
        s.add_argument('--session', type=lambda x: int(x, 16), help='hex; default random (same value resumes)')
        s.add_argument('--out', default='.')
        s.add_argument('--wait', type=float, default=900.0, help='seconds to wait for the console after EXEC')
        s.add_argument('--no-collect', action='store_true')
    r = sub.add_parser('report')
    r.add_argument('--out', default='.')
    sub.add_parser('relay', help='print the relay program the ssh mode runs on the Pi')
    a = ap.parse_args(argv)
    if a.cmd == 'relay':
        print(RELAY)
        return 0
    stamp = lambda s: print('%s %s' % (time.strftime('%H:%M:%S'), s), flush=True)
    if a.udp:
        t = UdpTransport(a.udp, a.bind)
    elif a.pi:
        t = SshRelayTransport(a.pi, a.port, stamp)
    else:
        ap.error('--pi or --udp')
    loop = Loop(t, stamp, a.verbose)
    try:
        return session_main(a, loop, stamp)
    except RuntimeError as e:
        stamp('error: %s' % e)
        return 3
    finally:
        t.close()


def session_main(a, loop, stamp):
    if True:
        h = loop.wait_hello(60.0)
        if h is None:
            stamp('no beacon from the loader in 60 s (is it UP on the console screen?)')
            return 2
        stamp(describe(h))
        if a.cmd == 'status':
            return 0
        if a.cmd == 'report':
            if h['report_state'] in (0, 1):
                stamp('no report pending')
                return 1
            rep = loop.fetch_report(h, a.out)
            stamp('report %s' % json.dumps(rep))
            return 0 if rep['crc_ok'] else 1
        if h['report_state'] not in (0, 1) and not a.corrupt:
            rep = loop.fetch_report(h, a.out)
            stamp('earlier report collected first: %s %s' % (rep['state'], rep['path']))
        raw = load_program(a.program)
        if LOAD_ADDR + len(raw) + 4 > IMAGE_END:
            stamp('program too large: %d bytes' % len(raw))
            return 2
        img = Image(raw, not a.no_compress, a.corrupt)
        session = a.session if a.session is not None else random.getrandbits(32) | 1
        stamp('image %d bytes -> %d (%s), %d chunks, sha256 %s, session %08x' % (
            len(raw), len(img.comp), 'deflate' if img.codec else 'raw', img.nchunks, hashlib.sha256(raw).hexdigest(),
            session))
        res = loop.transfer(img, session, a.args, a.deadline)
        stamp('transfer %s' % json.dumps(res))
        result = {'transfer': res, 'program': os.path.abspath(a.program), 'args': a.args, 'corrupt': a.corrupt}
        rc = 0 if res['verdict'] == 0 else 3
        if a.cmd == 'run' and (res['verdict'] == 0 or a.corrupt):
            r = loop.run_verified(session)
            stamp('run: %s' % r)
            result['run'] = r
            if r == 'exec' and not a.no_collect:
                b0 = (loop.hello or {}).get('boot_count')
                t0 = time.time()
                hb = loop.wait_hello(a.wait, lambda h: h['boot_count'] != b0 or h['uptime_ms'] < 1000 * (time.time() - t0))
                if hb is None:
                    stamp('the loader did not come back within %.0f s' % a.wait)
                    result['report'] = None
                    rc = 4
                elif hb['report_run'] != session or hb['report_state'] in (0, 1):
                    stamp('loader back after %.1f s without this run (power cycle?): %s' % (time.time() - t0, describe(hb)))
                    result['report'] = None
                    result['back_after_s'] = round(time.time() - t0, 1)
                    rc = 4
                else:
                    stamp('loader back after %.1f s: %s' % (time.time() - t0, describe(hb)))
                    rep = loop.fetch_report(hb, a.out)
                    result['report'] = rep
                    result['back_after_s'] = round(time.time() - t0, 1)
                    stamp('report %s %s exit %d, %d bytes, crc %s -> %s' % (rep['run'], rep['state'], rep['exit'],
                                                                         rep['bytes'], rep['crc_ok'], rep['path']))
                    if not rep['crc_ok'] or rep['state'] != 'DONE':
                        rc = 5
            elif r != 'exec':
                rc = 3
        result['link'] = loop.stats
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, 'run-%08x.json' % session), 'w') as f:
            json.dump(result, f, indent=2)
        return rc


if __name__ == '__main__':
    sys.exit(main())
