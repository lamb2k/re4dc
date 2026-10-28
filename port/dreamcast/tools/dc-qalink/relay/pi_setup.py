#!/usr/bin/env python3
"""pi_setup.py: set up a DreamPi (or any Raspberry Pi / Linux box with pppd) as the dc-qalink relay, from a PC on the
same network. Python 3 standard library + the system ssh / ssh-keygen / scp clients. Idempotent; --dry-run prints the
steps without changing anything.

  python pi_setup.py                      find the Pi, ask which one, then key, ssh alias, checks, relay install, verify
  python pi_setup.py --host 192.168.1.16 --user pi --alias dreampi
  python pi_setup.py --dry-run
  python pi_setup.py --wifi-report        report the Pi's Wi-Fi state (never changes it)

Passwords: the Pi's password is typed once into ssh's own prompt while the key is installed; it is never stored or
passed on a command line. Wi-Fi is only reported: changing networks needs a human's explicit OK (a wrong network
strands a headless Pi). If you do change it by hand: pass the passphrase via a file or stdin, never on a shell command
line; some routers refuse the Pi with WPA3/SAE (ASSOC-REJECT status 16): use WPA2 for it; add the new network with
disabled=1 first and keep the working one until the new one is proven.
"""
import argparse, concurrent.futures, ipaddress, os, re, socket, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = ('dreampi.local', 'raspberrypi.local', 'dreampi', 'raspberrypi')
KEY = os.path.join(os.path.expanduser('~'), '.ssh', 'dc_qalink_ed25519')
SSH_CONFIG = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
REMOTE_SRC = 'dc-qalink-src'

ARP_RE = re.compile(r'(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])\S*\s+(?:\S+\s+)?(?:at\s+)?'
                    r'([0-9a-fA-F]{2}[:-](?:[0-9a-fA-F]{2}[:-]){4}[0-9a-fA-F]{2})')
# Raspberry Pi Foundation / Raspberry Pi Ltd MAC prefixes
PI_OUIS = ('b8:27:eb', 'dc:a6:32', 'e4:5f:01', 'd8:3a:dd', '2c:cf:67', '28:cd:c1')


def parse_arp(text):
    """[(ip, mac)] from `arp -a` (Windows or Linux) or `ip neigh` output."""
    out = []
    for line in text.splitlines():
        m = ARP_RE.search(line)
        if not m:
            m2 = re.search(r'^((?:\d{1,3}\.){3}\d{1,3}) .*lladdr ([0-9a-f:]{17})', line)
            if not m2:
                continue
            ip, mac = m2.group(1), m2.group(2)
        else:
            ip, mac = m.group(1), m.group(2)
        mac = mac.lower().replace('-', ':')
        if mac in ('ff:ff:ff:ff:ff:ff',) or ip.endswith('.255') or ip.startswith(('224.', '239.')):
            continue
        out.append((ip, mac))
    return out


def is_pi_mac(mac):
    return mac.lower()[:8] in PI_OUIS


def port_open(ip, port=22, timeout=0.4):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def local_subnets():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:  # the address used for the default route
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('192.0.2.1', 9))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted({str(ipaddress.ip_network(ip + '/24', strict=False)) for ip in ips
                   if not ip.startswith(('127.', '169.254.'))})


def discover(scan=True):
    """Candidates [(ip, why)] in the order a human should consider them."""
    found = {}
    for n in NAMES:
        try:
            ip = socket.gethostbyname(n)
            found.setdefault(ip, 'name %s' % n)
        except OSError:
            pass
    arp = ''
    for cmd in (['arp', '-a'], ['ip', 'neigh']):
        try:
            arp += subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            pass
    for ip, mac in parse_arp(arp):
        if is_pi_mac(mac):
            found.setdefault(ip, 'Raspberry Pi MAC %s' % mac)
    if scan:
        hosts = [str(h) for net in local_subnets() for h in ipaddress.ip_network(net).hosts()]
        with concurrent.futures.ThreadPoolExecutor(64) as ex:
            for ip, ok in zip(hosts, ex.map(port_open, hosts)):
                if ok:
                    found.setdefault(ip, 'ssh open')
    order = {'name': 0, 'Raspberry': 1, 'ssh': 2}
    return sorted(found.items(), key=lambda kv: (order.get(kv[1].split()[0], 3), kv[0]))


def ssh_config_block(alias, host, user, key):
    return ('\n# dc-qalink relay (pi_setup.py)\nHost %s\n    HostName %s\n    User %s\n    IdentityFile %s\n'
            '    IdentitiesOnly yes\n' % (alias, host, user, key))


def update_ssh_config(text, alias, host, user, key):
    """Returns the new config text; unchanged when an identical alias block exists. A different block for the same
    alias is replaced (only the block this tool wrote, marked by its comment)."""
    block = ssh_config_block(alias, host, user, key)
    if block.strip() in text:
        return text
    pat = re.compile(r'\n# dc-qalink relay \(pi_setup\.py\)\nHost %s\n(?:    .*\n)*' % re.escape(alias))
    if pat.search(text):
        return pat.sub(lambda _m: block, text)
    if re.search(r'^Host\s+%s\s*$' % re.escape(alias), text, re.M):
        raise ValueError('~/.ssh/config already has a Host %s that this tool did not write; pick --alias' % alias)
    return text + ('' if text.endswith('\n') or not text else '\n') + block


REMOTE_CHECK = r'''
set -u
echo "os: $(. /etc/os-release 2>/dev/null; echo ${PRETTY_NAME:-unknown})"
echo "pppd: $(command -v pppd || echo MISSING)"
echo "dreampi: $(systemctl is-active dreampi 2>/dev/null || echo absent)"
echo "modem: $(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | tr '\n' ' ' || true)"
echo "python3: $(command -v python3 || echo MISSING)"
echo "relay: $(systemctl is-active dc-qalink-relay 2>/dev/null || echo absent)"
'''

REMOTE_WIFI = r'''
iwgetid -r 2>/dev/null || true
wpa_cli -i wlan0 status 2>/dev/null | grep -E '^(ssid|wpa_state|key_mgmt|ip_address)=' || true
nmcli -t -f active,ssid,security dev wifi 2>/dev/null | grep '^yes' || true
'''


class Runner:
    def __init__(self, dry):
        self.dry = dry

    def run(self, argv, stdin=None, check=True, quiet=False):
        print('$ ' + ' '.join(argv) + (' < (stdin)' if stdin is not None else ''))
        if self.dry:
            return subprocess.CompletedProcess(argv, 0, '', '')
        r = subprocess.run(argv, input=stdin, text=True, capture_output=quiet)
        if check and r.returncode:
            raise SystemExit('failed (%d): %s' % (r.returncode, ' '.join(argv)))
        return r

    def write(self, path, text):
        print('write %s' % path)
        if not self.dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)


def choose(cands, args):
    if args.host:
        return args.host
    if not cands:
        raise SystemExit('no Pi found; give --host <address>')
    for i, (ip, why) in enumerate(cands):
        print('  [%d] %s  (%s)' % (i, ip, why))
    if args.dry_run or args.yes:
        print('using [0] %s' % cands[0][0])
        return cands[0][0]
    pick = input('Which one is the Pi? [0] ').strip() or '0'
    return cands[int(pick)][0] if pick.isdigit() else pick


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--host', default='')
    ap.add_argument('--user', default='pi')
    ap.add_argument('--alias', default='dreampi')
    ap.add_argument('--key', default=KEY)
    ap.add_argument('--no-scan', action='store_true', help='names and ARP only')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--yes', action='store_true', help='take the first candidate without asking')
    ap.add_argument('--wifi-report', action='store_true')
    a = ap.parse_args(argv)
    r = Runner(a.dry_run)
    if a.wifi_report:
        r.run(['ssh', a.alias, 'bash -s'], stdin=REMOTE_WIFI, check=False)
        print('Wi-Fi is reported only. Changing it needs the human\'s explicit OK (see --help for the lessons).')
        return 0
    print('1. find the Pi')
    host = choose(discover(scan=not a.no_scan), a)
    print('2. key-based ssh to %s@%s' % (a.user, host))
    if not os.path.exists(a.key):
        r.run(['ssh-keygen', '-t', 'ed25519', '-N', '', '-C', 'dc-qalink', '-f', a.key])
    target = '%s@%s' % (a.user, host)
    probe = r.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-i', a.key, target, 'true'],
                  check=False, quiet=True)
    if probe.returncode or a.dry_run:
        pub = open(a.key + '.pub').read() if os.path.exists(a.key + '.pub') else '(public key)\n'
        print('   type the Pi\'s password once at ssh\'s prompt (it is not stored)')
        r.run(['ssh', '-o', 'ConnectTimeout=8', target,
               'umask 077; mkdir -p ~/.ssh; k=$(cat); grep -qxF "$k" ~/.ssh/authorized_keys 2>/dev/null || '
               'echo "$k" >> ~/.ssh/authorized_keys'], stdin=pub.strip() + '\n')
    text = open(SSH_CONFIG, encoding='utf-8').read() if os.path.exists(SSH_CONFIG) else ''
    new = update_ssh_config(text, a.alias, host, a.user, a.key)
    if new != text:
        r.write(SSH_CONFIG, new)
    else:
        print('   ~/.ssh/config already has Host %s' % a.alias)
    print('3. check the Pi, install the relay')
    r.run(['ssh', a.alias, 'bash -s'], stdin=REMOTE_CHECK, check=False)
    r.run(['ssh', a.alias, 'mkdir -p ~/%s' % REMOTE_SRC])
    r.run(['scp', '-q', os.path.join(HERE, 'dc_qalink_relay.py'), os.path.join(HERE, 'dc-qalink-relay.service'),
           os.path.join(HERE, 'install.sh'), '%s:%s/' % (a.alias, REMOTE_SRC)])
    print('   sudo may ask for the password on the Pi (DreamPi images allow it without one)')
    r.run(['ssh', '-t', a.alias, 'sudo bash ~/%s/install.sh %s' % (REMOTE_SRC, a.user)])
    print('4. verify')
    r.run(['ssh', a.alias, 'python3 ~/dc-qalink/dc_qalink_relay.py ctl \'!STATUS\''], check=False)
    print('done. Next: dial from the Dreamcast, then: python pc/dc_qalink.py --ssh %s send PING' % a.alias)
    print('Wi-Fi: not changed (pi_setup.py --wifi-report shows it).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
