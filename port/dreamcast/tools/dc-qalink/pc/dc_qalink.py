#!/usr/bin/env python3
"""dc_qalink.py: the PC side of dc-qalink. Python 3 standard library (+ the ssh client for --ssh).

Talks to the relay's control port, either directly (--relay host:port, e.g. through `ssh -L 52041:127.0.0.1:52041`)
or by running one `ssh <host> python3 ~/dc-qalink/dc_qalink_relay.py ctl ...` per action (--ssh host).

  dc_qalink.py --ssh dreampi send PING
  dc_qalink.py --ssh dreampi send GOTO level-1-boss
  dc_qalink.py --ssh dreampi status            (relay state; `send STATUS` asks the console)
  dc_qalink.py --ssh dreampi tail -n 60 --kind TA
  dc_qalink.py --ssh dreampi capture start boss-fight
  dc_qalink.py --ssh dreampi capture stop      (log section -> <out>/<label>.log + <label>.summary.txt)
  dc_qalink.py --ssh dreampi session my.txt    (one action per line; `wait <s>`; any other line is a command)

Capture cut: UDP can drop any one datagram, so a marker counts if ANY of its echoes is in the log: the relay's own
command line (C cN MARK x), the console's M row, its A answer (A cN OK MARK x) or its log line (dcql-mark: x).
"""
import argparse, json, os, re, shlex, subprocess, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'relay'))
CAPTURE_STATE = os.path.join(os.path.expanduser('~'), '.dc-qalink-capture.json')


class Link:
    def __init__(self, relay='', ssh='', remote_dir='~/dc-qalink', timeout=120.0):
        self.relay, self.ssh, self.remote_dir, self.timeout = relay, ssh, remote_dir, timeout

    def request(self, line):
        if self.ssh:
            cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', self.ssh,
                   'python3 %s/dc_qalink_relay.py ctl --timeout %d %s' % (
                       self.remote_dir, self.timeout, shlex.quote(line))]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='latin-1')
            if r.returncode not in (0, 1):
                return ['ERR ssh: %s' % r.stderr.strip()]
            return r.stdout.rstrip('\n').split('\n') if r.stdout else []
        from dc_qalink_relay import control_request
        return control_request(self.relay, line, self.timeout)


def failed(lines):
    return not lines or lines[0].startswith('ERR') or (lines[0].startswith('A ') and ' ERR ' in lines[0])


def marker_re(label):
    q = re.escape(label)
    return re.compile(r' (?:C \S+ MARK %s|M \d+ %s|A \S+ OK MARK %s|L dcql-mark: %s)$' % (q, q, q, q))


def cut(lines, start_label, stop_label):
    """Lines from the first echo of the last start marker to the last echo of the stop marker that follows it."""
    s_re, e_re = marker_re(start_label), marker_re(stop_label)
    starts = [i for i, l in enumerate(lines) if s_re.search(l)]
    stops = [i for i, l in enumerate(lines) if e_re.search(l)]
    if not starts or not stops:
        return []
    last_stop = stops[-1]
    before = [i for i in starts if i < last_stop]
    if not before:
        return []
    # the start group: echoes of one start marker sit close together; take the earliest of the last group
    s = before[-1]
    for i in reversed(before[:-1]):
        if not any(i < j < s for j in stops) and s - i < 400:
            s = i
        else:
            break
    return lines[s:last_stop + 1]


NUM = re.compile(r'^-?\d+(\.\d+)?$')
THEAD = re.compile(r'^T \d+ \d+ \d+/\d+$')


def summarize(lines):
    """Averages every numeric key=value of the T rows, per row name ("name k=v ..." -> name.k)."""
    sums, counts, order, seconds = {}, {}, [], 0
    for ln in lines:
        p = ln.split(' ', 2)
        if len(p) < 3 or p[1] != 'T':
            continue
        body = p[2]
        if THEAD.match(body):
            if body.endswith(' 1/' + body.rsplit('/', 1)[1]):
                seconds += 1
            continue
        toks = body.split()
        if not toks:
            continue
        row = toks[0] if '=' not in toks[0] else ''
        for t in toks:
            if '=' not in t:
                continue
            k, v = t.split('=', 1)
            if not NUM.match(v):
                continue
            key = '%s.%s' % (row, k) if row else k
            if key not in sums:
                order.append(key)
                sums[key], counts[key] = 0.0, 0
            sums[key] += float(v)
            counts[key] += 1
    out = ['telemetry rows: %d' % seconds]
    out += ['%-28s %12.2f  (n=%d)' % (k, sums[k] / counts[k], counts[k]) for k in order]
    return out


def size_of(link):
    r = link.request('!SIZE')
    return int(r[0]) if r and r[0].isdigit() else 0


def do_capture(link, a, words):
    if not words or words[0] not in ('start', 'stop'):
        print('capture start <label> | capture stop [label]')
        return 2
    if words[0] == 'start':
        if len(words) < 2:
            print('capture start <label>')
            return 2
        label = words[1]
        st = {'label': label, 'offset': size_of(link)}
        with open(CAPTURE_STATE, 'w') as f:
            json.dump(st, f)
        r = link.request('MARK cap-start:' + label)
        print('\n'.join(r))
        return 0  # the relay's C line is the marker of record even if the console's answer is lost
    st = {}
    if os.path.exists(CAPTURE_STATE):
        with open(CAPTURE_STATE) as f:
            st = json.load(f)
    label = words[1] if len(words) > 1 else st.get('label', '')
    if not label:
        print('capture stop: no open capture (give the label)')
        return 2
    print('\n'.join(link.request('MARK cap-stop:' + label)))
    time.sleep(a.settle)  # late echoes (M / L rows) of the stop marker
    off = st.get('offset', 0) if st.get('label') == label else 0
    lines = []
    while True:
        chunk = link.request('!READ %d' % off)
        if not chunk:
            break
        lines += chunk
        off += sum(len(l.encode('utf-8')) + 1 for l in chunk)
    sec = cut(lines, 'cap-start:' + label, 'cap-stop:' + label)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, label + '.log')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(sec) + ('\n' if sec else ''))
    summ = summarize(sec)
    with open(os.path.join(a.out, label + '.summary.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(['section %s: %d lines' % (label, len(sec))] + summ) + '\n')
    print('%s: %d lines' % (p, len(sec)))
    print('\n'.join(summ[:30]))
    return 0 if sec else 1


def action(link, a, words):
    if not words:
        return 0
    v, rest = words[0].lower(), words[1:]
    if v == 'wait':
        time.sleep(float(rest[0]) if rest else 1.0)
        return 0
    if v == 'capture':
        return do_capture(link, a, rest)
    if v == 'status':
        out = link.request('!STATUS')
    elif v == 'tail':
        n, kinds = 40, ''
        i = 0
        while i < len(rest):
            if rest[i] == '-n' and i + 1 < len(rest):
                n, i = int(rest[i + 1]), i + 2
            elif rest[i] == '--kind' and i + 1 < len(rest):
                kinds, i = rest[i + 1], i + 2
            else:
                i += 1
        out = link.request('!TAIL %d %s' % (n, kinds))
        print('\n'.join(out))
        return 0
    elif v == 'send':
        out = link.request(' '.join(rest))
    else:  # a session line that is a console command
        out = link.request(' '.join(words))
    print('\n'.join(out))
    return 1 if failed(out) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--relay', default=os.environ.get('DCQL_RELAY', '127.0.0.1:52041'), help='control host:port')
    ap.add_argument('--ssh', default=os.environ.get('DCQL_SSH', ''), help='ssh host of the relay (instead of --relay)')
    ap.add_argument('--dir', default='~/dc-qalink', help='relay folder on the ssh host')
    ap.add_argument('--out', default='captures', help='capture folder')
    ap.add_argument('--timeout', type=float, default=120.0)
    ap.add_argument('--settle', type=float, default=1.5, help='seconds to wait for late stop-marker echoes')
    sub = ap.add_subparsers(dest='mode', required=True)
    sub.add_parser('send').add_argument('command', nargs='+')
    sub.add_parser('status')
    tl = sub.add_parser('tail')
    tl.add_argument('-n', type=int, default=40)
    tl.add_argument('--kind', default='')
    sub.add_parser('capture').add_argument('args', nargs='+')
    se = sub.add_parser('session')
    se.add_argument('file')
    se.add_argument('--keep-going', action='store_true')
    a = ap.parse_args(argv)
    link = Link(a.relay, a.ssh, a.dir, a.timeout)
    if a.mode == 'send':
        return action(link, a, ['send'] + a.command)
    if a.mode == 'status':
        return action(link, a, ['status'])
    if a.mode == 'tail':
        return action(link, a, ['tail', '-n', str(a.n)] + (['--kind', a.kind] if a.kind else []))
    if a.mode == 'capture':
        return do_capture(link, a, a.args)
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


if __name__ == '__main__':
    sys.exit(main())
