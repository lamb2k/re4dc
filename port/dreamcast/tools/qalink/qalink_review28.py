#!/usr/bin/env python3
"""Opt-in Build28 bounds and complete-message handling for QA_LINK companions.

Imported only by --review28. The legacy implementations remain unchanged.
No third-party dependency or console protocol change is required.
"""
import base64
import collections
import datetime
import json
import math
import os
import re
import select
import shlex
import socket
import subprocess
import sys
import threading
import time
import uuid

MAX_DATAGRAM = 1200
MAX_COMMAND = 1184
MAX_PARTS = 16
MAX_PART_BYTES = 1100
MAX_CLIENTS = 8
MAX_WAITERS = 8
MAX_REPLY_BYTES = 128 * 1024
MAX_REPLY_PACKETS = 128
MAX_WAIT = 300.0
CLIENT_IO_TIMEOUT = 5.0
PEER_MAX_AGE = 30.0
LOG_BYTES = 16 * 1024 * 1024
CAPTURE_BYTES = 8 * 1024 * 1024
CAPTURE_LINES = 65536
LOG_LINE_BYTES = 8192
MAX_SNAPSHOTS = 8
SNAPSHOT_SECONDS = 30.0
MAX_FIELDS = 512
UINT = r"(?:0|[1-9][0-9]{0,9})"
PART = re.compile(r"^(T) (" + UINT + r") (" + UINT + r") (" + UINT + r")/(" + UINT + r")$")
DIAG = re.compile(r"^D ([A-Za-z0-9_-]{1,15}) (" + UINT + r")/(" + UINT + r")$")
ANSWER = re.compile(r"^A ([A-Za-z0-9_-]{1,15}) (OK|ERR)(?: (.*))?$", re.S)
RECORD = re.compile(r"^R ([A-Za-z0-9_-]{1,15}) (" + UINT + r")$")
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,23}$")
NUMBER = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")


def command_bytes(command):
    command = command.strip()
    try:
        data = command.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("command must contain printable ASCII")
    if not data or len(data) > MAX_COMMAND or any(c < 32 or c > 126 for c in data):
        raise ValueError("command must be one printable line of at most %d bytes" % MAX_COMMAND)
    return data


def wait_seconds(command, minimum=5.0):
    words = command.split()
    verb = words[0].upper() if words else ""
    wait = minimum
    if verb == "RECORD":
        try:
            wait = max(wait, min(1800, max(0, int(words[1]))) / 25.0 + 10)
        except (IndexError, ValueError):
            pass
    elif verb == "GOTO":
        wait = max(wait, 75.0)
    elif verb == "SCRIPT":
        wait = max(wait, 290.0)
    elif verb == "DIAG":
        wait = max(wait, 30.0)
    return min(MAX_WAIT, max(0.0, wait))


def multipart(text, diag=False):
    head, sep, payload = text.partition("\n")
    match = (DIAG if diag else PART).fullmatch(head)
    if not match or not sep:
        raise ValueError("malformed multipart header")
    fields = match.groups()
    part, total = int(fields[-2]), int(fields[-1])
    if not 1 <= part <= total <= MAX_PARTS or len(payload.encode("latin-1")) > MAX_PART_BYTES:
        raise ValueError("multipart bounds exceeded")
    if not diag and (int(fields[1]) > 0xffffffff or int(fields[2]) > 0xffffffff):
        raise ValueError("telemetry identity exceeds u32")
    return fields, part, total, payload


class Reply:
    """One bounded command result; completion is semantic, never packet count."""
    def __init__(self, cid, command):
        self.cid, self.command = cid, command
        self.verb = command.split()[0].upper()
        self.event = threading.Event()
        self.messages = collections.OrderedDict()
        self.bytes = 0
        self.parts = {}
        self.total = None
        self.records = {}
        self.record_total = None
        self.error = None

    def fail(self, message):
        self.error = ("ERR " + message)[:240]
        self.event.set()

    def retain(self, key, text):
        old = self.messages.get(key)
        if old is not None:
            if old != text:
                self.fail("conflicting duplicate response")
            return False
        size = len(text.encode("latin-1"))
        if len(self.messages) >= MAX_REPLY_PACKETS or self.bytes + size > MAX_REPLY_BYTES - 256:
            self.fail("response storage limit exceeded")
            return False
        self.messages[key] = text
        self.bytes += size
        return True

    def feed(self, text):
        if self.event.is_set():
            return
        head = text.partition("\n")[0]
        try:
            if text.startswith("D ") and self.verb == "DIAG":
                fields, part, total, payload = multipart(text, True)
                if fields[0] != self.cid:
                    return
                if self.total is not None and self.total != total:
                    raise ValueError("conflicting DIAG part total")
                self.total = total
                if self.retain(("D", part), text):
                    self.parts[part] = payload
                if not self.error and len(self.parts) == total:
                    self.event.set()
                return
            match = ANSWER.fullmatch(text)
            if match and match[1] == self.cid:
                status, body = match[2], match[3] or ""
                if not self.retain(("A", body), text):
                    return
                if status == "ERR":
                    self.event.set()
                elif self.verb in ("GOTO", "SCRIPT"):
                    done = re.search(r"\bDONE (.+?)(?: room=|$)", body)
                    if done:
                        if done[1] not in ("arrived", "ok", "marked"):
                            self.fail("drive ended: " + done[1])
                        else:
                            self.event.set()
                elif self.verb == "RECORD":
                    final = re.match(r"RECORD ticks=([0-9]{1,4})(?: |$)", body)
                    if final:
                        total = int(final[1])
                        requested = int(self.command.split()[1])
                        if not 1 <= total <= 1800 or total != requested:
                            raise ValueError("RECORD tick count mismatch")
                        self.record_total = total
                        self.finish_record()
                elif self.verb != "DIAG":
                    self.event.set()
                return
            match = RECORD.fullmatch(head)
            if match and match[1] == self.cid and self.verb == "RECORD":
                start = int(match[2])
                payload = text.partition("\n")[2]
                values = payload.rstrip(",").split(",")
                requested = int(self.command.split()[1])
                if not 1 <= requested <= 1800 or start % 30 or not 0 <= start < requested:
                    raise ValueError("invalid RECORD row offset")
                if len(values) != min(30, requested - start) or any(
                        not re.fullmatch(UINT, v) or int(v) > 0xffffffff for v in values):
                    raise ValueError("invalid RECORD row payload")
                if self.retain(("R", start), text):
                    self.records[start] = len(values)
                self.finish_record()
        except (ValueError, IndexError) as exc:
            self.fail(str(exc))

    def finish_record(self):
        if self.record_total and not self.error and sum(self.records.values()) == self.record_total:
            self.event.set()

    def result(self):
        # Preserve original response text; order DIAG parts by their actual index.
        if self.verb == "DIAG":
            lines = [text for key, text in self.messages.items() if key[0] != "D"]
            lines += [self.messages[("D", n)] for n in sorted(self.parts)]
        else:
            lines = list(self.messages.values())
        if self.error:
            lines.append(self.error)
        return lines


def service_class(base):
    class Service28(base):
        def __init__(self, log_path, udp_port, control):
            for path in (log_path, log_path + ".1"):
                if os.path.exists(path) and os.path.getsize(path) > LOG_BYTES:
                    raise ValueError("existing log exceeds review28 limit; preserve it and choose a new --log")
            self.log_bytes = os.path.getsize(log_path) if os.path.exists(log_path) else 0
            self.stop_event = threading.Event()
            self.client_slots = threading.BoundedSemaphore(MAX_CLIENTS)
            self.clients = set()
            self.dropped = 0
            super().__init__(log_path, udp_port, control)
            self.udp.setblocking(False)
            self.ctl.setblocking(False)

        def write(self, kind, text):
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            chunk = "".join("%s %s %s\n" % (ts, kind, line) for line in text.rstrip("\n").split("\n"))
            size = len(chunk.encode("utf-8"))
            if size > LOG_BYTES:
                raise ValueError("log record exceeds limit")
            with self.lock:
                if self.stop_event.is_set():
                    return
                if self.log_bytes + size > LOG_BYTES:
                    self.log.close()
                    os.replace(self.log_path, self.log_path + ".1")
                    self.log = open(self.log_path, "w", buffering=1, encoding="utf-8", errors="replace")
                    self.log_bytes = 0
                self.log.write(chunk)
                self.log_bytes += size

        def on_datagram(self, data, addr):
            if self.stop_event.is_set():
                return
            if not data or len(data) > MAX_DATAGRAM:
                self.dropped += 1
                return
            text = data.decode("latin-1")
            kind = text[:1]
            head = text.partition("\n")[0]
            if kind not in ("T", "L", "B", "A", "D", "R", "M") or not text.startswith(kind + " "):
                self.dropped += 1
                return
            now = time.monotonic()
            hello = False
            with self.lock:
                if self.console != addr:
                    for reply in self.waiters.values():
                        reply.fail("console endpoint changed before command completed")
                    self.console = addr
                    hello = True
                self.last_rx = now
                fields = head.split(" ", 2)
                if kind in ("A", "D", "R") and len(fields) > 1:
                    reply = self.waiters.get(fields[1])
                    if reply is not None:
                        reply.feed(text)
            if hello:
                self.write("S", "console at %s:%d" % addr)
                try:
                    self.udp.sendto(b"h0 HELLO", addr)
                except OSError:
                    pass
            # Exact packet journal is necessary: human line logging loses the
            # newline at a byte-split boundary in multipart telemetry.
            self.write("X28", base64.b64encode(data).decode("ascii"))
            self.write(kind, text)

        def send(self, command, wait=5.0):
            try:
                payload = command_bytes(command)
            except ValueError as exc:
                return ["ERR " + str(exc)]
            command = payload.decode("ascii")
            with self.lock:
                if self.stop_event.is_set():
                    return ["ERR service stopped"]
                if not self.console:
                    return ["ERR no console endpoint yet"]
                if time.monotonic() - self.last_rx > PEER_MAX_AGE and command.split()[0].upper() not in ("PING", "HELLO"):
                    return ["ERR console has been quiet; send PING to probe the known endpoint first"]
                if len(self.waiters) >= MAX_WAITERS:
                    return ["ERR command waiters busy"]
                cid = "c%08x" % (self.next_id & 0xffffffff)
                self.next_id = (self.next_id + 1) & 0xffffffff
                if cid in self.waiters:
                    return ["ERR command identity still pending"]
                reply = Reply(cid, command)
                self.waiters[cid] = reply
                peer = self.console
            try:
                wire = cid.encode("ascii") + b" " + payload
                assert len(wire) <= MAX_DATAGRAM
                self.udp.sendto(wire, peer)
                self.write("C", wire.decode("ascii"))
                if not reply.event.wait(wait_seconds(command, wait)):
                    with self.lock:
                        reply.fail("incomplete response to %s before deadline; driving status may be unknown" % cid)
                with self.lock:
                    return reply.result()
            except (OSError, ValueError) as exc:
                return ["ERR command transport failed: " + str(exc)]
            finally:
                with self.lock:
                    self.waiters.pop(cid, None)

        def control_client(self, conn):
            try:
                conn.settimeout(CLIENT_IO_TIMEOUT)
                with conn, conn.makefile("rb") as stream:
                    line = stream.readline(MAX_COMMAND + 7)
                    framed = line.startswith(b"@28 ")
                    if framed:
                        line = line[4:]
                    if not line.endswith(b"\n") or len(line) > MAX_COMMAND + 1:
                        out = ["ERR control line exceeds limit"]
                    else:
                        command = line[:-1].decode("latin-1")
                        if command.strip().upper() == "STATUS":
                            age = time.monotonic() - self.last_rx
                            out = ["review28 enabled", "console %s age=%.1fs" % (self.console, age),
                                   "log %s" % self.log_path]
                        else:
                            out = self.send(command)
                    payload = "\n".join(out).rstrip("\n").encode("latin-1", "replace")
                    if len(payload) > MAX_REPLY_BYTES:
                        payload = b"ERR control response exceeds limit"
                    wire = (b"Q28 %d\n" % len(payload) + payload + b"\n.\n") if framed else payload + b"\n.\n"
                    conn.sendall(wire)
            except (OSError, ValueError):
                pass
            finally:
                with self.lock:
                    self.clients.discard(conn)
                self.client_slots.release()

        def admit(self, conn):
            if not self.client_slots.acquire(False):
                conn.setblocking(False)
                try:
                    conn.send(b"ERR control clients busy\n.\n")
                except OSError:
                    pass
                conn.close()
                return False
            with self.lock:
                if self.stop_event.is_set():
                    self.client_slots.release()
                    conn.close()
                    return False
                self.clients.add(conn)
            try:
                threading.Thread(target=self.control_client, args=(conn,), daemon=True).start()
            except (RuntimeError, MemoryError):
                with self.lock:
                    self.clients.discard(conn)
                self.client_slots.release()
                conn.close()
                return False
            return True

        def close(self):
            self.stop_event.set()
            with self.lock:
                for reply in self.waiters.values():
                    reply.fail("service stopped before response completed")
                clients = list(self.clients)
            for conn in clients:
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                conn.close()
            self.udp.close()
            self.ctl.close()
            with self.lock:
                self.log.close()

        def serve(self):
            inputs = [self.udp, self.ctl]
            while not self.stop_event.is_set():
                try:
                    ready, _, _ = select.select(inputs, [], [], .2)
                    for sock in ready:
                        if sock is self.udp:
                            data, addr = self.udp.recvfrom(MAX_DATAGRAM + 1)
                            self.on_datagram(data, addr)
                        else:
                            conn, _ = self.ctl.accept()
                            self.admit(conn)
                except OSError:
                    if not self.stop_event.is_set():
                        self.dropped += 1
                except ValueError:
                    if not self.stop_event.is_set():
                        raise
    return Service28


def response_failed(lines):
    return not lines or any(line.startswith("ERR") or re.match(r"^A \S+ ERR(?: |$)", line) for line in lines)


def control_exchange(control, command, timeout, framed=True):
    host, port = control.rsplit(":", 1)
    payload = command_bytes(command)
    with socket.create_connection((host, int(port)), timeout=timeout) as conn:
        conn.sendall((b"@28 " if framed else b"") + payload + b"\n")
        with conn.makefile("rb") as stream:
            if framed:
                head = stream.readline(40)
                match = re.fullmatch(rb"Q28 ([0-9]{1,6})\n", head)
                if not match or int(match[1]) > MAX_REPLY_BYTES:
                    raise ValueError("review28 framed control response required")
                size = int(match[1])
                data = stream.read(size)
                if len(data) != size or stream.read(3) != b"\n.\n":
                    raise ValueError("truncated control response")
                return data.decode("latin-1").split("\n")
            lines, size = [], 0
            while True:
                line = stream.readline(MAX_DATAGRAM + 2)
                if not line or len(line) > MAX_DATAGRAM + 1:
                    raise ValueError("invalid status response")
                if line == b".\n":
                    return lines
                size += len(line)
                if size > 4096:
                    raise ValueError("status response exceeds limit")
                lines.append(line.decode("latin-1").rstrip("\n"))


def send_control(control, command, timeout=120.0):
    try:
        if not math.isfinite(timeout) or not 0 < timeout <= MAX_WAIT:
            raise ValueError("timeout must be finite and in 0..300 seconds")
        command_bytes(command)
        status = control_exchange(control, "STATUS", min(timeout, CLIENT_IO_TIMEOUT), False)
        if "review28 enabled" not in status:
            return ["ERR start qalink_pi.py serve with --review28 first"]
        if command.strip().upper() == "STATUS":
            return status
        return control_exchange(control, command, max(timeout, wait_seconds(command) + 5.0))
    except (OSError, ValueError) as exc:
        return ["ERR " + str(exc)]


def send_command(control, command, timeout):
    lines = send_control(control, command, timeout)
    print("\n".join(lines))
    return int(response_failed(lines))


def journal_packet(line):
    # The service text log uses CRLF on Windows; the base64 datagram stays exact.
    fields = line.rstrip("\r\n").split(" ", 2)
    if len(fields) != 3 or fields[1] != "X28":
        return None
    try:
        raw = base64.b64decode(fields[2], validate=True)
        if not raw or len(raw) > MAX_DATAGRAM:
            return None
        now = datetime.datetime.fromisoformat(fields[0].replace("Z", "+00:00")).timestamp()
        return now, raw.decode("latin-1")
    except (ValueError, TypeError):
        return None


def log_lines(path):
    """Read retained files in order, with a bound on both file and line size."""
    for name in (path + ".1", path):
        if not os.path.exists(name):
            continue
        with open(name, "rb") as stream:
            if os.fstat(stream.fileno()).st_size > LOG_BYTES:
                raise ValueError("log exceeds review28 file limit")
            read = 0
            while True:
                line = stream.readline(LOG_LINE_BYTES + 1)
                if not line:
                    break
                read += len(line)
                if len(line) > LOG_LINE_BYTES or read > LOG_BYTES:
                    raise ValueError("log grew beyond review28 read bound")
                yield line.decode("utf-8", "replace").rstrip("\n")


def capture_cut(lines, token):
    start, stop = "cap-start:" + token, "cap-stop:" + token
    buf, used, active = [], 0, False
    for line in lines:
        packet = journal_packet(line)
        marker = packet[1].split(" ", 2) if packet and packet[1].startswith("M ") else []
        label = marker[2] if len(marker) == 3 else None
        if label == start:
            if active:
                raise ValueError("duplicate capture start marker")
            active = True
        if active:
            used += len(line.encode("utf-8")) + 1
            if used > CAPTURE_BYTES or len(buf) >= CAPTURE_LINES:
                raise ValueError("capture exceeds byte/line bound")
            buf.append(line)
        if active and label == stop:
            return buf
    raise ValueError("complete capture markers not present in retained log")


def summarize(lines):
    pending = collections.OrderedDict()
    completed = collections.deque(maxlen=64)
    sums, counts = collections.OrderedDict(), {}
    snapshots = discarded = duplicates = 0
    for line in lines:
        packet = journal_packet(line)
        if not packet or not packet[1].startswith("T "):
            continue
        now, text = packet
        for key in list(pending):
            if now - pending[key][0] > SNAPSHOT_SECONDS:
                del pending[key]
                discarded += 1
        try:
            fields, part, total, payload = multipart(text)
        except ValueError:
            discarded += 1
            continue
        key = (fields[1], fields[2])
        if key in completed:
            duplicates += 1
            continue
        if key not in pending:
            if len(pending) >= MAX_SNAPSHOTS:
                pending.popitem(last=False)
                discarded += 1
            pending[key] = [now, total, {}]
        state = pending[key]
        if total != state[1] or (part in state[2] and state[2][part] != payload):
            del pending[key]
            completed.append(key)
            discarded += 1
            continue
        if part in state[2]:
            duplicates += 1
        state[2][part] = payload
        if len(state[2]) != total:
            continue
        body = "".join(state[2][i] for i in range(1, total + 1))
        del pending[key]
        completed.append(key)
        snapshots += 1
        for row in body.splitlines():
            tokens = row.split()
            if not tokens:
                continue
            name = tokens[0].split("=", 1)[0]
            for token in tokens:
                if "=" not in token:
                    continue
                field, value = token.split("=", 1)
                if not NUMBER.fullmatch(value):
                    continue
                number = float(value)
                if not math.isfinite(number):
                    continue
                key = name + "." + field if name != field else field
                if key not in sums:
                    if len(sums) >= MAX_FIELDS:
                        raise ValueError("telemetry numeric field limit exceeded")
                    sums[key], counts[key] = 0.0, 0
                sums[key] += number
                counts[key] += 1
    discarded += len(pending)
    out = ["complete telemetry snapshots: %d" % snapshots,
           "incomplete/conflicting/expired snapshots or malformed parts: %d; duplicate parts: %d" % (discarded, duplicates)]
    out += ["%-28s %10.2f  (n=%d)" % (key, value / counts[key], counts[key]) for key, value in sums.items()]
    return out


def remote_dir(path):
    if path == "~":
        return '"$HOME"'
    if path.startswith("~/"):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


def log_kind(line, kinds):
    fields = line.split(" ", 2)
    return not kinds or len(fields) == 3 and fields[1] in kinds


def bounded_output(argv, limit, timeout):
    """Drain both SSH pipes without an unbounded communicate() allocation."""
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    chunks = [[], []]
    overflow = threading.Event()
    def read_pipe(stream, index, bound):
        used = 0
        while True:
            data = stream.read(min(8192, bound + 1 - used))
            if not data:
                return
            if used + len(data) > bound:
                overflow.set()
                proc.kill()
                return
            chunks[index].append(data)
            used += len(data)
    readers = [threading.Thread(target=read_pipe, args=(proc.stdout, 0, limit), daemon=True),
               threading.Thread(target=read_pipe, args=(proc.stderr, 1, 4096), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        result = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
        raise
    finally:
        for reader in readers:
            reader.join(timeout=1)
        if not any(reader.is_alive() for reader in readers):
            proc.stdout.close()
            proc.stderr.close()
    if any(reader.is_alive() for reader in readers):
        raise ValueError("remote output did not close before deadline")
    if overflow.is_set():
        raise ValueError("remote capture output exceeds bound")
    return result, b"".join(chunks[0]).decode("utf-8", "replace"), b"".join(chunks[1]).decode("utf-8", "replace")


def client_link(legacy, args):
    class Link28(legacy.Link):
        def send(self, command, timeout=120):
            try:
                command_bytes(command)
            except ValueError as exc:
                print("ERR " + str(exc))
                return 1
            if self.a.local:
                return send_command("127.0.0.1:52041", command, timeout)
            remote = "python3 %s/qalink_pi.py send --review28 --timeout %s %s" % (
                remote_dir(self.a.dir), timeout, " ".join(shlex.quote(w) for w in command.split()))
            try:
                result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", self.a.pi, remote],
                                        timeout=max(timeout, wait_seconds(command) + 5) + 15)
                return result.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                print("ERR " + str(exc))
                return 1

        def cut_capture(self, token):
            if self.a.local:
                return capture_cut(log_lines(self.a.local), token)
            remote = "python3 %s/qalink_review28.py cut %s/qalink.log %s" % (
                remote_dir(self.a.dir), remote_dir(self.a.dir), shlex.quote(token))
            result, out, err = bounded_output(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", self.a.pi, remote], CAPTURE_BYTES, 20)
            if result:
                raise ValueError(err.strip() or "remote capture failed")
            return out.splitlines()
    return Link28(args)


def capture(legacy, link, args, words):
    state_path = legacy.CAPTURE_STATE + ".review28"
    endpoint = [args.pi, args.dir, args.local]
    if not words or words[0] not in ("start", "stop"):
        raise ValueError("capture start <label> | capture stop [label]")
    if words[0] == "start":
        if len(words) != 2 or not LABEL.fullmatch(words[1]):
            raise ValueError("capture label: 1..24 letters/digits/underscore/hyphen, starting with a letter/digit")
        if os.path.exists(state_path):
            raise ValueError("a review28 capture is already open")
        label = words[1]
        token = uuid.uuid4().hex[:12] + ":" + label
        if link.send("MARK cap-start:" + token):
            return 1
        with open(state_path, "x", encoding="utf-8") as stream:
            json.dump(dict(label=label, token=token, endpoint=endpoint), stream)
        return 0
    with open(state_path, encoding="utf-8") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError("capture state exceeds bound")
    state = json.loads(raw)
    if state.get("endpoint") != endpoint or (len(words) > 1 and words[1] != state.get("label")):
        raise ValueError("capture label/endpoint differs from open capture")
    label, token = state["label"], state["token"]
    if not LABEL.fullmatch(label) or not re.fullmatch(r"[0-9a-f]{12}:[A-Za-z0-9][A-Za-z0-9_-]{0,23}", token):
        raise ValueError("invalid capture identity")
    if link.send("MARK cap-stop:" + token):
        return 1
    end = time.monotonic() + 3.0
    while True:
        try:
            lines = link.cut_capture(token)
            break
        except ValueError:
            if time.monotonic() >= end:
                raise
            time.sleep(.1)
    summary = summarize(lines)
    folder = args.out or os.path.join(r"C:\Flycast-Evidence\re4-dreamcast", "console-" + datetime.date.today().strftime("%Y%m%d"))
    os.makedirs(folder, exist_ok=True)
    stem = label + "-" + token.split(":", 1)[0]
    path = os.path.join(folder, stem + ".log")
    with open(path, "x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    with open(os.path.join(folder, stem + ".summary.txt"), "x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(summary) + "\n")
    os.unlink(state_path)
    print(path)
    print("\n".join(summary[:24]))
    return 0


def client_main(legacy, args):
    link = client_link(legacy, args)
    def action(words):
        if words and words[0].lower() == "capture":
            return capture(legacy, link, args, words[1:])
        return legacy.action(link, args, words)
    try:
        if args.mode == "session":
            result = 0
            with open(args.file, encoding="utf-8") as stream:
                while True:
                    line = stream.readline(MAX_COMMAND + 2)
                    if not line:
                        break
                    if len(line.encode("utf-8")) > MAX_COMMAND:
                        raise ValueError("session line exceeds command bound")
                    words = line.split("#", 1)[0].split()
                    if words:
                        code = action(words)
                        if code:
                            result = code
                            if not args.keep_going:
                                return code
            return result
        if args.mode == "status":
            return link.send("STATUS")
        if args.mode == "send":
            return action(["send"] + args.command)
        if args.mode in ("fetch", "tail"):
            if args.local:
                lines = log_lines(args.local)
                if args.mode == "tail":
                    if not 0 <= args.n <= 10000:
                        raise ValueError("tail count must be 0..10000")
                    chosen = (line for line in lines if log_kind(line, args.kind))
                    print("\n".join(collections.deque(chosen, maxlen=args.n)))
                else:
                    with open(args.dest, "w", encoding="utf-8", newline="\n") as stream:
                        for line in lines:
                            stream.write(line + "\n")
                return 0
            remote = "python3 %s/qalink_review28.py %s %s/qalink.log" % (
                remote_dir(args.dir), args.mode, remote_dir(args.dir))
            if args.mode == "tail":
                remote += " %s %s" % (args.n, shlex.quote(args.kind))
                return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.pi, remote], timeout=30).returncode
            with open(args.dest, "w", encoding="utf-8", newline="\n") as stream:
                return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.pi, remote],
                                      stdout=stream, timeout=60).returncode
        return action([args.mode] + args.args)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print("ERR " + str(exc), file=sys.stderr)
        return 1


def main():
    # Internal, explicitly named review28 helper; callers supply exact argv.
    try:
        mode, path = sys.argv[1:3]
        if mode == "cut":
            for line in capture_cut(log_lines(path), sys.argv[3]):
                print(line)
        elif mode == "fetch":
            for line in log_lines(path):
                print(line)
        elif mode == "tail":
            count, kinds = int(sys.argv[3]), sys.argv[4]
            if not 0 <= count <= 10000:
                raise ValueError("tail count must be 0..10000")
            chosen = (line for line in log_lines(path) if log_kind(line, kinds))
            for line in collections.deque(chosen, maxlen=count):
                print(line)
        else:
            raise ValueError("unknown review28 helper")
        return 0
    except (OSError, ValueError, IndexError) as exc:
        print("ERR " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
