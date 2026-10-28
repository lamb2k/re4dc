#!/usr/bin/env python3
"""qalink.py: the PC side of the RE4DC QA remote link (Windows or Linux; Python 3 standard library + the ssh client).

Every action is one `ssh <pi>` call; nothing runs on the PC between calls and no input is sent to any PC window.

  python qalink.py --pi pi@192.168.1.50 send PING
  python qalink.py --pi pi@192.168.1.50 send TELEPORT r103
  python qalink.py --pi pi@192.168.1.50 send QA LEON ON
  python qalink.py --pi pi@192.168.1.50 send RECORD 300
  python qalink.py --pi pi@192.168.1.50 tail -n 60          (the last lines of the Pi's log)
  python qalink.py --pi pi@192.168.1.50 fetch qalink.log    (copies the whole log here)
  python qalink.py --pi pi@192.168.1.50 status

Driving Leon and cutting the session into sections (lane linkpad28):

  python qalink.py --pi re4pi teleport r103                 (a QA preset; or: teleport pos <x> <y> <z> [yaw])
  python qalink.py --pi re4pi goto -11000 -1000 run         (autopilot; waits for arrival / timeout / stuck)
  python qalink.py --pi re4pi pad A 0 0 5                   (buttons + stick for N ticks; pad stop clears the queue)
  python qalink.py --pi re4pi script r103-barn              (/cd/dc/qa/pad/r103-barn.txt on the disc)
  python qalink.py --pi re4pi mark doorway
  python qalink.py --pi re4pi capture start barn-inside     (a marker; ...play / wait...)
  python qalink.py --pi re4pi capture stop                  (the Pi log between the two markers ->
                                                             C:\\Flycast-Evidence\\re4-dreamcast\\console-<date>\\<label>.log
                                                             + <label>.summary.txt: the T rows averaged)
  python qalink.py --pi re4pi session sessions/barn.txt     (one command per line, plus `wait <s>`)

--pi defaults to the QALINK_PI environment variable. --dir is where qalink_pi.py lives on the Pi (default ~/qalink).
--local <log> talks to a qalink_pi.py serve on this PC (Flycast's modem emulation tests) instead of ssh.
"""
import argparse, datetime, os, re, shlex, socket, subprocess, sys, time

CAPTURE_STATE = os.path.join(os.path.expanduser('~'), '.qalink-capture')


def ssh(pi, remote, capture=False):
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', pi, remote]
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)


class Link:
    """One action = one ssh call (remote) or one control-port connection (--local)."""

    def __init__(self, a):
        self.a = a

    def send(self, command, timeout=120):
        if self.a.local:
            host, port = '127.0.0.1', 52041
            out = []
            with socket.create_connection((host, port), timeout=timeout + 10) as s:
                s.sendall((command.strip() + '\n').encode('latin-1'))
                f = s.makefile('r', encoding='latin-1')
                for line in f:
                    if line.rstrip('\n') == '.':
                        break
                    out.append(line.rstrip('\n'))
            print('\n'.join(out))
            return 0 if out and not out[0].startswith('ERR') and ' ERR ' not in out[0] else 1
        return ssh(self.a.pi, 'python3 %s/qalink_pi.py send --timeout %d %s' % (
            self.a.dir, timeout, ' '.join(shlex.quote(c) for c in command.split()))).returncode

    def send_and_cut(self, command, start_pat, stop_pat):
        """Sends the stop marker and returns the log lines from the last start marker to the stop marker."""
        if self.a.local:
            self.send(command)
            time.sleep(0.5)
            with open(self.a.local, encoding='utf-8', errors='replace') as f:
                lines = f.read().split('\n')
            return cut(lines, start_pat, stop_pat)
        awk = ("awk -v s=%s -v e=%s '$0 ~ s {buf=\"\"; f=1} f {buf = buf $0 \"\\n\"} $0 ~ e && f {out=buf; f=0} "
               "END {printf \"%%s\", out}' %s/qalink.log") % (shlex.quote(start_pat), shlex.quote(stop_pat), self.a.dir)
        remote = 'python3 %s/qalink_pi.py send %s >&2; sleep 0.5; %s' % (
            self.a.dir, ' '.join(shlex.quote(c) for c in command.split()), awk)
        r = ssh(self.a.pi, remote, capture=True)
        sys.stderr.write(r.stderr)
        return r.stdout.split('\n')


def cut(lines, start_pat, stop_pat):
    s, e = re.compile(start_pat), re.compile(stop_pat)
    buf, out, on = [], [], False
    for ln in lines:
        if s.search(ln):
            buf, on = [], True
        if on:
            buf.append(ln)
        if on and e.search(ln):
            out, on = buf, False
    return out


NUM = re.compile(r'^-?\d+(\.\d+)?$')


def summarize(lines):
    """Averages every numeric key=value of the telemetry rows (T) over the section, per row name."""
    sums, counts, order = {}, {}, []
    tparts = 0
    for ln in lines:
        p = ln.split(' ', 2)
        if len(p) < 3 or p[1] != 'T':
            continue
        body = p[2]
        if re.match(r'^T \d+ \d+ \d+/\d+$', body):
            tparts += 1
            continue
        toks = body.split()
        if not toks:
            continue
        row = toks[0].split('=')[0] if '=' in toks[0] else toks[0]
        for t in toks:
            if '=' not in t:
                continue
            k, v = t.split('=', 1)
            if not NUM.match(v):
                continue
            key = '%s.%s' % (row, k) if row != k else k
            if key not in sums:
                order.append(key)
                sums[key] = 0.0
                counts[key] = 0
            sums[key] += float(v)
            counts[key] += 1
    out = ['telemetry seconds: %d' % tparts]
    for k in order:
        out.append('%-28s %10.2f  (n=%d)' % (k, sums[k] / counts[k], counts[k]))
    return out


def do_capture(link, a, words):
    if not words or words[0] not in ('start', 'stop'):
        print('capture start <label> | capture stop [label]')
        return 2
    if words[0] == 'start':
        if len(words) < 2:
            print('capture start <label>')
            return 2
        label = words[1]
        with open(CAPTURE_STATE, 'w') as f:
            f.write(label)
        return link.send('MARK cap-start:%s' % label)
    label = words[1] if len(words) > 1 else (open(CAPTURE_STATE).read().strip() if os.path.exists(CAPTURE_STATE) else '')
    if not label:
        print('capture stop: no open capture (give the label)')
        return 2
    # Any echo of the marker counts (the M datagram, the A answer, the qamark log line, or the Pi C line when the console never echoed): UDP can drop one.
    mk = r'( M [0-9]+| OK MARK| qamark:| C c[0-9]+ MARK) cap-%s:' + re.escape(label) + '$'
    sec = link.send_and_cut('MARK cap-stop:%s' % label, mk % 'start', mk % 'stop')
    sec = [s for s in sec if s]
    out = a.out or os.path.join(r'C:\Flycast-Evidence\re4-dreamcast', 'console-' + datetime.date.today().strftime('%Y%m%d'))
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, label + '.log')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(sec) + '\n')
    summ = summarize(sec)
    with open(os.path.join(out, label + '.summary.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(['section %s: %d lines' % (label, len(sec))] + summ) + '\n')
    print('%s: %d lines' % (p, len(sec)))
    print('\n'.join(summ[:24]))
    return 0 if sec else 1


def action(link, a, words):
    """One action (a CLI subcommand or a session line). Returns the exit code."""
    if not words:
        return 0
    v, rest = words[0].lower(), words[1:]
    q = ' '.join(rest)
    if v == 'send':
        return link.send(q, timeout=300 if rest and rest[0].upper() in ('GOTO', 'SCRIPT') else 120)
    if v == 'teleport':
        return link.send('TELEPORT ' + q)
    if v == 'goto':
        return link.send('GOTO ' + q, timeout=75)
    if v == 'pad':
        return link.send('PAD ' + q)
    if v == 'script':
        return link.send('SCRIPT ' + q, timeout=300)
    if v == 'mark':
        return link.send('MARK ' + q)
    if v == 'record':
        return link.send('RECORD ' + q)
    if v == 'diag':
        return link.send('DIAG')
    if v == 'qa':
        return link.send('QA ' + q)
    if v == 'capture':
        return do_capture(link, a, rest)
    if v == 'wait':
        time.sleep(float(rest[0]) if rest else 1.0)
        return 0
    print('unknown action: %s' % ' '.join(words))
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pi', default=os.environ.get('QALINK_PI', ''), help='user@host of the DreamPi')
    ap.add_argument('--dir', default='~/qalink', help='qalink_pi.py and the log on the Pi (default ~/qalink)')
    ap.add_argument('--local', default='', help='log of a qalink_pi.py serve on this PC (Flycast tests): no ssh')
    ap.add_argument('--out', default='', help='capture folder (default C:\\Flycast-Evidence\\re4-dreamcast\\console-<date>)')
    ap.add_argument('--review28', action='store_true', help='opt in to bounded Build28 replies and complete-snapshot captures')
    sub = ap.add_subparsers(dest='mode', required=True)
    sd = sub.add_parser('send')
    sd.add_argument('command', nargs='+')
    tl = sub.add_parser('tail')
    tl.add_argument('-n', type=int, default=40)
    tl.add_argument('--kind', default='', help='only these datagram kinds, e.g. TA (telemetry + answers)')
    fe = sub.add_parser('fetch')
    fe.add_argument('dest', nargs='?', default='qalink.log')
    sub.add_parser('status')
    for name in ('teleport', 'goto', 'pad', 'script', 'mark', 'capture', 'record', 'wait'):
        sp = sub.add_parser(name)
        sp.add_argument('args', nargs='*')
    se = sub.add_parser('session', help='a file of actions, one per line (# comments; wait <s>)')
    se.add_argument('file')
    se.add_argument('--keep-going', action='store_true', help='do not stop at a failed action')
    a = ap.parse_args()
    if not a.pi and not a.local:
        ap.error('--pi user@host (or set QALINK_PI), or --local <log>')
    if a.review28:
        import qalink_review28
        return qalink_review28.client_main(sys.modules[__name__], a)
    link = Link(a)
    d = a.dir
    if a.mode == 'send':
        return action(link, a, ['send'] + a.command)
    if a.mode == 'status':
        return link.send('STATUS')
    if a.mode == 'tail':
        if a.kind:
            pat = '^[^ ]* [%s] ' % ''.join(k for k in a.kind if k.isalpha())
            return ssh(a.pi, 'grep -a %s %s/qalink.log | tail -n %d' % (shlex.quote(pat), d, a.n)).returncode
        return ssh(a.pi, 'tail -n %d %s/qalink.log' % (a.n, d)).returncode
    if a.mode == 'fetch':
        r = ssh(a.pi, 'cat %s/qalink.log' % d, capture=True)
        if r.returncode:
            sys.stderr.write(r.stderr)
            return r.returncode
        with open(a.dest, 'w', encoding='utf-8', newline='\n') as f:
            f.write(r.stdout)
        print('%s: %d lines' % (a.dest, r.stdout.count('\n')))
        return 0
    if a.mode == 'session':
        rc = 0
        with open(a.file, encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                line = line.split('#', 1)[0].strip()
                if not line:
                    continue
                print('== %s:%d %s (%s)' % (os.path.basename(a.file), n, line, time.strftime('%H:%M:%S')))
                r = action(link, a, line.split())
                if r:
                    rc = r
                    print('== failed (rc %d)' % r)
                    if not a.keep_going:
                        return r
        return rc
    return action(link, a, [a.mode] + a.args)


if __name__ == '__main__':
    sys.exit(main())
