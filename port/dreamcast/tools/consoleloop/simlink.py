#!/usr/bin/env python3
"""simlink.py: a bad modem line between consoleloop.py and the loader's host build, for the host tests (lane eng-loop).

A UDP proxy on localhost. The PC side talks to --pc-port, the console side (cl_host --peer) to --console-port; the
proxy forwards to the console at --console-addr. Each direction can lose, corrupt (one bit), duplicate, reorder
(extra random delay), rate-limit (a line of N bytes/s with a bounded queue: tail drop) and go dead for windows of time.

  python3 simlink.py --pc-port 52070 --console-port 52062 --console-addr 127.0.0.1:52061 --drop 0.1 --corrupt 0.05
"""
import argparse, heapq, json, random, select, socket, sys, threading, time


class Direction:
    def __init__(self, drop=0.0, corrupt=0.0, dup=0.0, reorder_ms=0.0, rate=0.0, qcap=8192, latency_ms=0.0,
                 outages=()):
        self.drop, self.corrupt, self.dup, self.reorder_ms = drop, corrupt, dup, reorder_ms
        self.rate, self.qcap, self.latency_ms, self.outages = rate, qcap, latency_ms, list(outages)
        self.line_free = 0.0
        self.counts = {'in': 0, 'out': 0, 'dropped': 0, 'corrupted': 0, 'duplicated': 0, 'outage': 0, 'tail': 0,
                       'bytes': 0}


class SimLink:
    def __init__(self, pc_port, console_port, console_addr, up=None, down=None, seed=1):
        """up = console -> PC, down = PC -> console (Direction)."""
        self.rng = random.Random(seed)
        self.pc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pc.bind(('127.0.0.1', pc_port))
        self.co = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.co.bind(('127.0.0.1', console_port))
        self.console_addr = console_addr
        self.pc_addr = None
        self.up = up or Direction()
        self.down = down or Direction()
        self.heap = []
        self.n = 0
        self.t0 = time.time()
        self.stop = False
        self.th = threading.Thread(target=self.loop, daemon=True)

    def start(self):
        self.th.start()
        return self

    def close(self):
        self.stop = True
        self.th.join(2)
        self.pc.close()
        self.co.close()

    def offer(self, d, data, sock, dst):
        now = time.time()
        d.counts['in'] += 1
        t = now - self.t0
        if any(a <= t < b for a, b in d.outages):
            d.counts['outage'] += 1
            return
        if self.rng.random() < d.drop:
            d.counts['dropped'] += 1
            return
        copies = 2 if self.rng.random() < d.dup else 1
        if copies == 2:
            d.counts['duplicated'] += 1
        for _ in range(copies):
            b = data
            if self.rng.random() < d.corrupt:
                ba = bytearray(b)
                i = self.rng.randrange(len(ba))
                ba[i] ^= 1 << self.rng.randrange(8)
                b = bytes(ba)
                d.counts['corrupted'] += 1
            at = now
            if d.rate:
                start = max(now, d.line_free)
                if (start - now) * d.rate > d.qcap:
                    d.counts['tail'] += 1
                    continue
                d.line_free = start + (len(b) + 36) / d.rate   # + IP/UDP/PPP overhead
                at = d.line_free
            at += d.latency_ms / 1000.0 + (self.rng.random() * d.reorder_ms / 1000.0 if d.reorder_ms else 0.0)
            self.n += 1
            heapq.heappush(self.heap, (at, self.n, id(sock), sock, dst, b, d))

    def loop(self):
        while not self.stop:
            now = time.time()
            while self.heap and self.heap[0][0] <= now:
                _, _, _, sock, dst, b, d = heapq.heappop(self.heap)
                if dst:
                    try:
                        sock.sendto(b, dst)
                        d.counts['out'] += 1
                        d.counts['bytes'] += len(b)
                    except OSError:
                        pass
            wait = min(0.01, max(0.0, self.heap[0][0] - now)) if self.heap else 0.01
            r, _, _ = select.select([self.pc, self.co], [], [], wait)
            for s in r:
                try:
                    data, addr = s.recvfrom(4096)
                except OSError:
                    continue
                if s is self.pc:
                    self.pc_addr = addr
                    self.offer(self.down, data, self.co, self.console_addr)
                else:
                    self.offer(self.up, data, self.pc, self.pc_addr)

    def report(self):
        return {'up': self.up.counts, 'down': self.down.counts}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pc-port', type=int, default=52070)
    ap.add_argument('--console-port', type=int, default=52062)
    ap.add_argument('--console-addr', default='127.0.0.1:52061')
    for k in ('drop', 'corrupt', 'dup', 'reorder_ms', 'rate', 'latency_ms'):
        ap.add_argument('--' + k.replace('_', '-'), type=float, default=0.0)
    ap.add_argument('--outage', action='append', default=[], help='start,end seconds (both directions)')
    a = ap.parse_args()
    h, _, p = a.console_addr.partition(':')
    out = [tuple(map(float, o.split(','))) for o in a.outage]
    mk = lambda: Direction(a.drop, a.corrupt, a.dup, a.reorder_ms, a.rate, 8192, a.latency_ms, out)
    s = SimLink(a.pc_port, a.console_port, (h, int(p)), mk(), mk()).start()
    try:
        while True:
            time.sleep(5)
            print(json.dumps(s.report()), flush=True)
    except KeyboardInterrupt:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
