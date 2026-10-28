#!/usr/bin/env python3
"""dc_qalink_relay.py: the relay side of dc-qalink (runs on a DreamPi or any Linux box whose pppd answers the console).

The console (built with lib/dcql.c) dials in; once PPP is up it sends UDP datagrams to this relay (port 52040). The
relay
  - appends every datagram to a log, one line per text line: "<UTC time> <kind> <text>";
  - sends commands to the console ("<id> <VERB> [args]") and waits for the matching "A <id> ..." answer;
  - serves a small line protocol on a TCP control port (default 127.0.0.1:52041) for dc_qalink.py.

Control protocol: one request line, answered by lines and a final "." line.
  !STATUS            relay state (console address, last heard, log path and size)
  !TAIL <n> [kinds]  last n log lines (optionally only these kinds, e.g. TA)
  !SIZE              log size in bytes
  !READ <off> [max]  log bytes from offset off (at most max, default 4 MiB), whole lines
  anything else      a console command; the answer rows (or "ERR no answer ...")

Run:   python3 dc_qalink_relay.py serve [--log ~/dc-qalink/relay.log] [--udp 52040] [--control 127.0.0.1:52041]
                                        [--wait VERB=seconds ...]
Send:  python3 dc_qalink_relay.py ctl PING           (one control request through the local control port)
Python 3 standard library only. MIT licence.
"""
import argparse, datetime, os, select, socket, sys, threading, time

UDP_PORT = 52040
CONTROL = '127.0.0.1:52041'
DATAGRAM_MAX = 1200
READ_MAX = 4 << 20


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


class Relay:
    def __init__(self, log_path, udp_port=UDP_PORT, control=CONTROL, waits=None, default_wait=5.0):
        self.log_path = os.path.abspath(os.path.expanduser(log_path))
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.log = open(self.log_path, 'a', buffering=1, encoding='utf-8', errors='replace', newline='\n')
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp.bind(('0.0.0.0', udp_port))  # every interface: ppp0 exists only while the console is connected
        host, port = control.rsplit(':', 1)
        self.ctl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ctl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ctl.bind((host, int(port)))
        self.ctl.listen(8)
        self.control_addr = self.ctl.getsockname()
        self.udp_addr = self.udp.getsockname()
        self.console = None
        self.last_rx = 0.0
        self.lock = threading.Lock()
        self.waiters = {}
        self.next_id = 1
        self.waits = dict(waits or {})
        self.default_wait = default_wait
        self.running = True
        self.write('S', 'relay listening udp %d control %s:%d log %s' % (
            self.udp_addr[1], self.control_addr[0], self.control_addr[1], self.log_path))

    def write(self, kind, text):
        with self.lock:
            ts = stamp()
            for line in text.rstrip('\n').split('\n'):
                self.log.write('%s %s %s\n' % (ts, kind, line))

    def on_datagram(self, data, addr):
        if not data or len(data) > DATAGRAM_MAX:
            self.write('S', 'dropped datagram of %d bytes from %s:%d' % ((len(data),) + addr))
            return
        text = data.decode('latin-1')
        kind = text[:1]
        self.last_rx = time.time()
        if self.console != addr:
            self.console = addr
            self.write('S', 'console at %s:%d' % addr)
            self.udp.sendto(b'h0 HELLO', addr)  # the console learns the relay's address from it
        self.write(kind, text)
        head = text.split('\n', 1)[0].split(' ')
        if kind == 'A' and len(head) > 1:
            with self.lock:
                w = self.waiters.get(head[1])
                if w is not None:
                    w.append(text)

    def send(self, command, wait=None):
        command = command.strip()
        if not self.console:
            return ['ERR no console yet (has it dialled in?)']
        verb = command.split()[0].upper() if command.split() else ''
        wait = wait if wait is not None else self.waits.get(verb, self.default_wait)
        with self.lock:
            cid = 'c%d' % self.next_id
            self.next_id += 1
            self.waiters[cid] = []
        line = '%s %s' % (cid, command)
        data = line.encode('latin-1', 'replace')[:DATAGRAM_MAX]
        self.udp.sendto(data, self.console)
        self.write('C', line)
        end = time.time() + wait
        while time.time() < end:
            time.sleep(0.02)
            with self.lock:
                if self.waiters[cid]:
                    break
        with self.lock:
            got = self.waiters.pop(cid)
        return got or ['ERR no answer to %s within %.0f s' % (cid, wait)]

    def read_from(self, off, limit):
        with open(self.log_path, 'rb') as f:
            f.seek(max(0, off))
            data = f.read(limit)
        cut = data.rfind(b'\n')
        return data[:cut + 1].decode('utf-8', 'replace') if cut >= 0 else ''

    def handle(self, line):
        if not line.startswith('!'):
            return self.send(line)
        words = line[1:].split()
        op = words[0].upper() if words else ''
        if op == 'STATUS':
            age = time.time() - self.last_rx
            return ['console %s' % ('%s:%d last heard %.0f s ago' % (self.console + (age,)) if self.console else 'none'),
                    'log %s %d bytes' % (self.log_path, os.path.getsize(self.log_path)),
                    'udp %d' % self.udp_addr[1]]
        if op == 'SIZE':
            return [str(os.path.getsize(self.log_path))]
        if op == 'TAIL':
            n = int(words[1]) if len(words) > 1 else 40
            kinds = words[2] if len(words) > 2 else ''
            size = os.path.getsize(self.log_path)
            lines = self.read_from(max(0, size - READ_MAX), READ_MAX).split('\n')[:-1]
            if kinds:
                lines = [l for l in lines if len(l.split(' ', 2)) > 1 and l.split(' ', 2)[1] in kinds]
            return lines[-n:]
        if op == 'READ':
            off = int(words[1]) if len(words) > 1 else 0
            lim = min(int(words[2]) if len(words) > 2 else READ_MAX, READ_MAX)
            return self.read_from(off, lim).split('\n')[:-1]
        return ['ERR unknown request %s' % op]

    def control_client(self, conn):
        with conn:
            f = conn.makefile('rw', encoding='latin-1', newline='\n')
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out = self.handle(line)
                # a lone "." inside the reply would end it early: escape it
                f.write('\n'.join('..' if l == '.' else l for l in out) + ('\n' if out else '') + '.\n')
                f.flush()

    def serve(self):
        while self.running:
            try:
                r, _, _ = select.select([self.udp, self.ctl], [], [], 0.2)
            except (OSError, ValueError):
                break  # closed
            for s in r:
                if not self.running:
                    return
                if s is self.udp:
                    try:
                        data, addr = self.udp.recvfrom(4096)
                    except OSError as e:
                        if not self.running:
                            return
                        self.write('S', 'udp receive error: %s' % e)
                        continue
                    self.on_datagram(data, addr)
                else:
                    conn, _ = self.ctl.accept()
                    threading.Thread(target=self.control_client, args=(conn,), daemon=True).start()

    def close(self):
        self.running = False
        for s in (self.udp, self.ctl):
            try:
                s.close()
            except OSError:
                pass
        self.log.close()


def control_request(control, line, timeout=120.0):
    """One request over the control port; returns the reply lines."""
    host, port = control.rsplit(':', 1)
    out = []
    with socket.create_connection((host, int(port)), timeout=timeout) as s:
        s.sendall((line.strip() + '\n').encode('latin-1', 'replace'))
        f = s.makefile('r', encoding='latin-1', newline='\n')
        for l in f:
            l = l.rstrip('\n')
            if l == '.':
                break
            out.append('.' if l == '..' else l)
    return out


def failed(lines):
    return not lines or lines[0].startswith('ERR') or (lines[0].startswith('A ') and ' ERR ' in lines[0])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    sv = sub.add_parser('serve')
    sv.add_argument('--log', default='~/dc-qalink/relay.log')
    sv.add_argument('--udp', type=int, default=UDP_PORT)
    sv.add_argument('--control', default=CONTROL)
    sv.add_argument('--wait', action='append', default=[], metavar='VERB=SECONDS',
                    help='answer timeout for a slow command (default 5 s)')
    ct = sub.add_parser('ctl')
    ct.add_argument('request', nargs='+')
    ct.add_argument('--control', default=CONTROL)
    ct.add_argument('--timeout', type=float, default=120.0)
    a = ap.parse_args(argv)
    if a.mode == 'serve':
        waits = {}
        for w in a.wait:
            k, v = w.split('=', 1)
            waits[k.upper()] = float(v)
        r = Relay(a.log, a.udp, a.control, waits)
        try:
            r.serve()
        except KeyboardInterrupt:
            pass
        finally:
            r.close()
        return 0
    out = control_request(a.control, ' '.join(a.request), a.timeout)
    print('\n'.join(out))
    return 1 if failed(out) else 0


if __name__ == '__main__':
    sys.exit(main())
