"""Observe real opcode data accesses without inventing cache misses.

Instruction fetches are excluded; PC-relative literal loads are data loads.
The fixture maps cached RAM at low synthetic addresses, which become the
0x8c000000 alias only for the pipeline-model ELF. Distinct 32-byte lines are
working-set/touch counts, not measured fills or hardware bus transactions.
"""
import collections


def region(address):
    if 0xe0000000 <= address < 0xe4000000:
        return "store_queue"
    if address >= 0xe0000000 or address & 0xe0000000 == 0xa0000000:
        return "uncached"
    return "cached"


def summarize(events, prefetches=()):
    """Each event is (instruction ordinal, pc, read/write, address, bytes)."""
    grouped = collections.defaultdict(list)
    for event in events:
        grouped[region(event[3])].append(event)
    result = {}
    for kind in ("cached", "store_queue", "uncached"):
        rows = grouped[kind]
        reads = [row for row in rows if row[2] == "read"]
        writes = [row for row in rows if row[2] == "write"]
        row = dict(load_instructions=len({x[0] for x in reads}),
                   store_instructions=len({x[0] for x in writes}),
                   load_accesses=len(reads), store_accesses=len(writes),
                   load_bytes=sum(x[4] for x in reads),
                   store_bytes=sum(x[4] for x in writes))
        if kind == "cached":
            def lines(items):
                return {(address & 0x1fffffff) >> 5
                        for item in items
                        for address in range(item[3], item[3] + item[4])}
            rlines, wlines = lines(reads), lines(writes)
            row.update(unique_read_lines=len(rlines),
                       unique_write_lines=len(wlines),
                       unique_data_lines=len(rlines | wlines),
                       unique_line_bytes=32 * len(rlines | wlines))
        result[kind] = row
    result["scope"] = __doc__
    cached_prefetches = [x for x in prefetches if region(x[2]) == "cached"]
    result["prefetch"] = dict(requests=len(cached_prefetches),
        unique_requested_lines=len({(x[2] & 0x1fffffff) >> 5 for x in cached_prefetches}),
        sq_flush_requests=sum(region(x[2]) == "store_queue" for x in prefetches),
        scope="PREF requests observed separately; not demand loads, fills or guaranteed useful transfers")
    return result


class Observer:
    """Mixin before a qualified scalar Machine in the method-resolution order.

    Parent interpreters fetch opcodes through fetch(), while the older base
    interpreter's first read is explicitly marked by its immediate caller.
    Bounded control programs separately prove literal loads, double moves,
    delay-slot ownership and wrapped addresses are retained correctly.
    """
    def __init__(self, *args, **kwargs):
        self.memory_events = []
        self.prefetch_events = []
        self.memory_tracking = False
        self.executing_pc = None
        self.executing_ordinal = None
        self._base_fetch_pending = None
        super().__init__(*args, **kwargs)

    def step(self, pc, delay=False):
        previous = self.executing_pc, self.executing_ordinal
        self.executing_pc = pc
        self.executing_ordinal = len(self.instruction_pcs)
        opcode = self.fetch(pc)
        if self.memory_tracking and opcode & 0xf0ff == 0x0083:
            self.prefetch_events.append((self.executing_ordinal, pc,
                self.reg[(opcode >> 8) & 15] & 0xffffffff))
        try:
            return super().step(pc, delay)
        finally:
            self.executing_pc, self.executing_ordinal = previous

    def read(self, address, size):
        address &= 0xffffffff
        opcode_fetch = self._base_fetch_pending == address and size == 2
        if opcode_fetch:
            self._base_fetch_pending = None
        value = super().read(address, size)
        if self.memory_tracking and self.executing_pc is not None and not opcode_fetch:
            self.memory_events.append((self.executing_ordinal,
                self.executing_pc, "read", address, size))
        return value

    def write(self, address, value, size):
        address &= 0xffffffff
        result = super().write(address, value, size)
        if self.memory_tracking and self.executing_pc is not None:
            self.memory_events.append((self.executing_ordinal,
                self.executing_pc, "write", address, size))
        return result

    def observe_start(self):
        self.memory_events = []
        self.prefetch_events = []
        self.memory_tracking = True

    def observe_stop(self):
        self.memory_tracking = False
        return summarize(self.memory_events, self.prefetch_events)
