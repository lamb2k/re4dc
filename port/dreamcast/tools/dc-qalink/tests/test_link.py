"""Relay + PC tool tests with a fake console UDP peer (loss, reorder, a dropped start marker). Standard library only.
Run from the package root: python3 -m unittest discover -s tests"""
import io, os, socket, sys, tempfile, threading, time, unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'relay'), os.path.join(ROOT, 'pc')]
import dc_qalink_relay as relay  # noqa: E402
import dc_qalink as pc  # noqa: E402
import pi_setup  # noqa: E402


class FakeConsole:
    """Answers like lib/dcql.c. drop: set of row kinds to lose for MARK; reorder: send the echoes in reverse."""

    def __init__(self, relay_port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(('127.0.0.1', 0))
        self.s.settimeout(0.1)
        self.dest = ('127.0.0.1', relay_port)
        self.drop, self.reorder, self.lseq, self.tseq = set(), False, 0, 0
        self.run = True
        self.t = threading.Thread(target=self.loop, daemon=True)
        self.t.start()

    def tx(self, text):
        self.s.sendto(text.encode('latin-1'), self.dest)

    def telemetry(self, body):
        self.tseq += 1
        self.tx('T %d %d 1/1\n%s' % (self.tseq, int(time.time() * 1000) & 0xffffffff, body))

    def loop(self):
        while self.run:
            try:
                data, _ = self.s.recvfrom(2048)
            except OSError:
                continue
            cid, verb, *rest = data.decode('latin-1').split(' ', 2) + ['']
            args = rest[0]
            if verb == 'HELLO':
                continue
            if verb == 'PING':
                self.tx('A %s OK PONG %s' % (cid, args))
            elif verb == 'MARK':
                self.lseq += 1
                rows = [('M', 'M 123 %s' % args), ('L', 'L %d 1/1\ndcql-mark: %s\n' % (self.lseq, args)),
                        ('A', 'A %s OK MARK %s' % (cid, args))]
                if self.reorder:
                    rows.reverse()
                for k, r in rows:
                    if k not in self.drop:
                        self.tx(r)
            else:
                self.tx('A %s ERR unknown %s' % (cid, verb))

    def close(self):
        self.run = False
        self.t.join(1)
        self.s.close()


class LinkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = relay.Relay(os.path.join(self.tmp.name, 'relay.log'), 0, '127.0.0.1:0', default_wait=1.0)
        self.rt = threading.Thread(target=self.r.serve, daemon=True)
        self.rt.start()
        self.c = FakeConsole(self.r.udp_addr[1])
        self.c.telemetry('hello n=0')  # the relay learns the console from its first datagram
        time.sleep(0.2)
        self.ctl = '127.0.0.1:%d' % self.r.control_addr[1]
        self.link = pc.Link(relay=self.ctl, timeout=10)

    def tearDown(self):
        self.c.close()
        self.r.close()
        self.rt.join(1)
        self.tmp.cleanup()

    def args(self):
        class A:
            out = os.path.join(self.tmp.name, 'cap')
            settle = 0.3
        return A()

    def test_ping_and_unknown(self):
        self.assertEqual(self.link.request('PING x')[0].split(' ', 2)[2], 'OK PONG x')
        self.assertTrue(pc.failed(self.link.request('NOPE')))

    def test_status_tail_size(self):
        self.assertIn('console 127.0.0.1', self.link.request('!STATUS')[0])
        self.assertTrue(any(' T hello n=0' in l for l in self.link.request('!TAIL 10 T')))
        self.assertGreater(int(self.link.request('!SIZE')[0]), 0)

    def capture(self, drop_start=(), drop_stop=(), reorder=False):
        a = self.args()
        with redirect_stdout(io.StringIO()):
            self.c.drop, self.c.reorder = set(drop_start), reorder
            pc.do_capture(self.link, a, ['start', 'fight'])
            for i in range(5):
                self.c.telemetry('frame fps=%d ms=%d.5' % (50 + i, 20 + i))
            time.sleep(0.2)
            self.c.drop = set(drop_stop)
            rc = pc.do_capture(self.link, a, ['stop', 'fight'])
        with open(os.path.join(a.out, 'fight.summary.txt')) as f:
            summ = f.read()
        return rc, summ

    def test_capture_clean(self):
        rc, summ = self.capture()
        self.assertEqual(rc, 0)
        self.assertIn('frame.fps', summ)
        self.assertIn('52.00  (n=5)', summ)

    def test_capture_dropped_start_marker(self):
        # the console's M, L and A rows for the start marker are all lost: the relay's C line still cuts
        rc, summ = self.capture(drop_start={'M', 'L', 'A'})
        self.assertEqual(rc, 0)
        self.assertIn('(n=5)', summ)

    def test_capture_loss_and_reorder(self):
        rc, summ = self.capture(drop_start={'M'}, drop_stop={'A', 'L'}, reorder=True)
        self.assertEqual(rc, 0)
        self.assertIn('frame.ms', summ)


class CutTest(unittest.TestCase):
    L = ['t S x', 't T T 1 0 1/1', 't T frame fps=10', 't C c1 MARK cap-start:a', 't T T 2 0 1/1',
         't T frame fps=20', 't M M 5 cap-stop:a', 't T frame fps=99']

    def test_only_m_echo_for_stop(self):
        sec = pc.cut(self.L, 'cap-start:a', 'cap-stop:a')
        self.assertEqual(sec[0], 't C c1 MARK cap-start:a')
        self.assertEqual(sec[-1], 't M M 5 cap-stop:a')
        self.assertEqual(pc.summarize(sec)[1].split()[1], '20.00')

    def test_log_echo_only(self):
        lines = ['t L dcql-mark: cap-start:b', 't T frame fps=30', 't A A c9 OK MARK cap-stop:b']
        self.assertEqual(len(pc.cut(lines, 'cap-start:b', 'cap-stop:b')), 3)

    def test_label_prefix_not_matched(self):
        self.assertEqual(pc.cut(['t M M 1 cap-start:ab', 't M M 2 cap-stop:a'], 'cap-start:a', 'cap-stop:a'), [])


class PiSetupTest(unittest.TestCase):
    def test_parse_arp_windows_and_linux(self):
        win = '  192.168.1.16          b8-27-eb-12-34-56     dynamic\n  192.168.1.255         ff-ff-ff-ff-ff-ff     static'
        lin = '? (192.168.1.20) at dc:a6:32:00:11:22 [ether] on wlan0\n192.168.1.30 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE'
        got = pi_setup.parse_arp(win + '\n' + lin)
        self.assertIn(('192.168.1.16', 'b8:27:eb:12:34:56'), got)
        self.assertIn(('192.168.1.20', 'dc:a6:32:00:11:22'), got)
        self.assertIn(('192.168.1.30', '00:11:22:33:44:55'), got)
        self.assertFalse(any(ip.endswith('.255') for ip, _ in got))
        self.assertTrue(pi_setup.is_pi_mac('b8:27:eb:12:34:56'))

    def test_ssh_config_idempotent(self):
        t1 = pi_setup.update_ssh_config('Host other\n    HostName x\n', 'dreampi', '10.0.0.5', 'pi', '/k')
        self.assertEqual(pi_setup.update_ssh_config(t1, 'dreampi', '10.0.0.5', 'pi', '/k'), t1)
        t2 = pi_setup.update_ssh_config(t1, 'dreampi', '10.0.0.6', 'pi', '/k')
        self.assertEqual(t2.count('Host dreampi'), 1)
        self.assertIn('HostName 10.0.0.6', t2)
        self.assertIn('Host other', t2)
        with self.assertRaises(ValueError):
            pi_setup.update_ssh_config('Host dreampi\n    HostName y\n', 'dreampi', '1.2.3.4', 'pi', '/k')

    def test_dry_run_changes_nothing(self):
        home = tempfile.mkdtemp()
        cfg = os.path.join(home, 'config')
        old = pi_setup.SSH_CONFIG
        pi_setup.SSH_CONFIG = cfg
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                pi_setup.main(['--dry-run', '--host', '192.0.2.10', '--key', os.path.join(home, 'k')])
            out = buf.getvalue()
            self.assertIn('ssh-keygen', out)
            self.assertIn('install.sh', out)
            self.assertFalse(os.path.exists(cfg))
            self.assertFalse(os.path.exists(os.path.join(home, 'k')))
        finally:
            pi_setup.SSH_CONFIG = old


if __name__ == '__main__':
    unittest.main()
