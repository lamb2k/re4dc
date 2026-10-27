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

--pi defaults to the QALINK_PI environment variable. --dir is where qalink_pi.py lives on the Pi (default ~/qalink).
"""
import argparse, os, shlex, subprocess, sys


def ssh(pi, remote, capture=False):
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', pi, remote]
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pi', default=os.environ.get('QALINK_PI', ''), help='user@host of the DreamPi')
    ap.add_argument('--dir', default='~/qalink', help='qalink_pi.py and the log on the Pi (default ~/qalink)')
    sub = ap.add_subparsers(dest='mode', required=True)
    sd = sub.add_parser('send')
    sd.add_argument('command', nargs='+')
    tl = sub.add_parser('tail')
    tl.add_argument('-n', type=int, default=40)
    tl.add_argument('--kind', default='', help='only these datagram kinds, e.g. TA (telemetry + answers)')
    fe = sub.add_parser('fetch')
    fe.add_argument('dest', nargs='?', default='qalink.log')
    sub.add_parser('status')
    a = ap.parse_args()
    if not a.pi:
        ap.error('--pi user@host (or set QALINK_PI)')
    d = a.dir
    if a.mode == 'send':
        r = ssh(a.pi, 'python3 %s/qalink_pi.py send %s' % (d, ' '.join(shlex.quote(c) for c in a.command)))
        return r.returncode
    if a.mode == 'status':
        return ssh(a.pi, 'python3 %s/qalink_pi.py send STATUS' % d).returncode
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


if __name__ == '__main__':
    sys.exit(main())
