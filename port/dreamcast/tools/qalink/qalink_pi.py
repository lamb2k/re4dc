#!/usr/bin/env python3
"""qalink_pi.py: the Pi side of the RE4DC QA remote link (lane qalink27, 2026-10-27). Python 3 standard library only.

A QA disc built with QA_LINK=1 dials the DreamPi through the Dreamcast's modem; once PPP is up it sends UDP datagrams
to this service (port 52040): telemetry once a second (T), new log lines (L), RECORD rows (R), command answers (A) and
DIAG parts (D). This service

  - logs every datagram to a file, one line per text line, each prefixed with a UTC timestamp and the datagram kind;
  - sends commands to the console ("<id> <COMMAND> [args]") and collects their answers;
  - takes commands from a small TCP control port (default 127.0.0.1:52041; SSH to the Pi and use --send) and, when run
    in a terminal, from stdin.

Run:     python3 qalink_pi.py serve [--log /var/log/qalink/qalink.log] [--udp 52040] [--control 127.0.0.1:52041]
Command: python3 qalink_pi.py send PING            (prints the console's answer; RECORD / DIAG wait for all parts)
Tail:    tail -f /var/log/qalink/qalink.log
"""
import argparse, datetime, os, select, socket, sys, threading, time

UDP_PORT = 52040
CONTROL = '127.0.0.1:52041'


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


class Service:
    def __init__(self, log_path, udp_port, control):
        self.log_path = log_path
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        self.log = open(log_path, 'a', buffering=1, encoding='utf-8', errors='replace')
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp.bind(('0.0.0.0', udp_port))   # every interface: ppp0 appears only while the console is connected
        host, port = control.rsplit(':', 1)
        self.ctl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ctl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ctl.bind((host, int(port)))
        self.ctl.listen(4)
        self.console = None          # (ip, port) of the last datagram from the console
        self.last_rx = 0.0           # time of that datagram
        self.lock = threading.Lock()
        self.waiters = {}            # command id -> list of answer lines
        self.next_id = 1
        self.write('S', 'qalink_pi listening udp %d control %s log %s' % (udp_port, control, log_path))

    def write(self, kind, text):
        with self.lock:
            ts = stamp()
            for line in text.rstrip('\n').split('\n'):
                self.log.write('%s %s %s\n' % (ts, kind, line))

    def on_datagram(self, data, addr):
        text = data.decode('latin-1')
        kind = text[:1] or '?'
        self.last_rx = time.time()
        if self.console != addr:
            self.console = addr
            self.write('S', 'console at %s:%d' % addr)
            self.udp.sendto(b'h0 HELLO', addr)   # the console learns this address from it (default host = peer)
        self.write(kind, text)
        head = text.split('\n', 1)[0].split(' ')
        if kind in 'ADR' and len(head) > 1:
            with self.lock:
                w = self.waiters.get(head[1])
                if w is not None:
                    w.append(text)

    def send(self, command, wait=5.0):
        """Sends one command; returns the answer lines (A, plus D / R parts) received within wait seconds."""
        if not self.console:
            return ['ERR no console yet (the console has not sent anything; is the link UP?)']
        with self.lock:
            cid = 'c%d' % self.next_id
            self.next_id += 1
            self.waiters[cid] = []
        line = '%s %s' % (cid, command.strip())
        self.udp.sendto(line.encode('latin-1'), self.console)
        self.write('C', line)
        verb = command.split()[0].upper() if command.split() else ''
        if verb == 'RECORD':
            try:
                wait = max(wait, int(command.split()[1]) / 25.0 + 10)   # ticks at >= 25 a second, plus slack
            except (IndexError, ValueError):
                pass
        if verb in ('GOTO', 'SCRIPT'):   # lane linkpad28: wait for the walk's DONE row (or an ERR)
            wait = max(wait, 70.0 if verb == 'GOTO' else 290.0)
        end = time.time() + wait
        while time.time() < end:
            time.sleep(0.05)
            with self.lock:
                got = list(self.waiters[cid])
            finals = [g for g in got if g.startswith('A %s ' % cid)]
            if verb in ('GOTO', 'SCRIPT'):
                if any(' DONE ' in g or ' ERR ' in g for g in finals):
                    break
            elif verb == 'RECORD':
                if any(' RECORD ticks=' in g for g in finals) or any(' ERR ' in g for g in finals):
                    break
            elif verb == 'DIAG':
                parts = [g for g in got if g.startswith('D ')]
                if parts:
                    n = parts[0].split('\n', 1)[0].split(' ')[2].split('/')[1]
                    if len(parts) >= int(n):
                        break
            elif finals:
                break
        with self.lock:
            got = self.waiters.pop(cid)
        return got or ['ERR no answer to %s within %.0f s' % (cid, wait)]

    def control_client(self, conn):
        with conn:
            f = conn.makefile('rw', encoding='latin-1', newline='\n')
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.upper() == 'STATUS':
                    age = time.time() - self.last_rx
                    out = ['console %s' % ('%s:%d last heard %.0f s ago' % (self.console + (age,)) if self.console else 'none'),
                           'log %s' % self.log_path]
                else:
                    out = self.send(line)
                f.write('\n'.join(out).rstrip('\n') + '\n.\n')
                f.flush()

    def serve(self):
        inputs = [self.udp, self.ctl]
        if os.name != 'nt' and sys.stdin.isatty():   # select() takes sockets only on Windows (PC test runs)
            inputs.append(sys.stdin)
            print('qalink_pi: type a command (PING, TELEPORT r103, QA LEON ON, RECORD 300, DIAG, MENU, RESUME)')
        while True:
            r, _, _ = select.select(inputs, [], [], 1.0)
            for s in r:
                if s is self.udp:
                    try:
                        data, addr = self.udp.recvfrom(2048)
                    except OSError as e:   # e.g. Windows reports an ICMP port-unreachable as a reset; keep serving
                        self.write('S', 'udp receive error: %s' % e)
                        continue
                    self.on_datagram(data, addr)
                elif s is self.ctl:
                    conn, _ = self.ctl.accept()
                    threading.Thread(target=self.control_client, args=(conn,), daemon=True).start()
                else:
                    line = sys.stdin.readline()
                    if not line:
                        inputs.remove(sys.stdin)
                    elif line.strip():
                        cmd = line.strip()
                        threading.Thread(target=lambda c=cmd: print('\n'.join(self.send(c))), daemon=True).start()


def send_command(control, command, timeout):
    host, port = control.rsplit(':', 1)
    with socket.create_connection((host, int(port)), timeout=timeout) as s:
        s.sendall((command.strip() + '\n').encode('latin-1'))
        f = s.makefile('r', encoding='latin-1')
        out = []
        for line in f:
            if line.rstrip('\n') == '.':
                break
            out.append(line.rstrip('\n'))
    print('\n'.join(out))
    return 0 if out and not out[0].startswith('ERR') and ' ERR ' not in out[0] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    sv = sub.add_parser('serve')
    sv.add_argument('--log', default=os.path.expanduser('~/qalink/qalink.log'))
    sv.add_argument('--udp', type=int, default=UDP_PORT)
    sv.add_argument('--control', default=CONTROL, help='host:port of the TCP control port (default %s)' % CONTROL)
    sd = sub.add_parser('send')
    sd.add_argument('command', nargs='+')
    sd.add_argument('--control', default=CONTROL)
    sd.add_argument('--timeout', type=float, default=120.0)
    a = ap.parse_args()
    if a.mode == 'serve':
        Service(a.log, a.udp, a.control).serve()
        return 0
    return send_command(a.control, ' '.join(a.command), a.timeout)


if __name__ == '__main__':
    sys.exit(main())
