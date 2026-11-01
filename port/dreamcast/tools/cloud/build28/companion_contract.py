#!/usr/bin/env python3
"""Build28 actual-Python companion contract fixtures; no modem or console claim."""
import argparse
import ast
import base64
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import marshal
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[5]
DIR = ROOT / "port/dreamcast/tools/qalink"
BASE = "568c357656efbec468db06a282c1f79caebaa725"
sys.path.insert(0, str(DIR))
import qalink as pc
import qalink_pi as pi
import qalink_review28 as q


def journal(packet, seconds=0):
    stamp = datetime.datetime.fromtimestamp(1700000000 + seconds, datetime.timezone.utc).isoformat()
    return stamp + " X28 " + base64.b64encode(packet.encode("latin-1")).decode("ascii")


def eventually(predicate, timeout=2):
    end = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= end:
            raise AssertionError("fixture deadline")
        time.sleep(.005)


def background(fn):
    result = []
    def run():
        try:
            result.append(fn())
        except BaseException as exc:
            result.append(exc)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


class ReplyCases(unittest.TestCase):
    def test_command_and_datagram_bounds(self):
        self.assertEqual(len(q.command_bytes("X" * q.MAX_COMMAND)), q.MAX_COMMAND)
        self.assertLessEqual(len(b"cffffffff " + q.command_bytes("X" * q.MAX_COMMAND)), 1200)
        for command in ("", "X" * (q.MAX_COMMAND + 1), "PING\nMENU", "PING\0", "PING \u2603"):
            with self.subTest(command=command[:20]), self.assertRaises(ValueError):
                q.command_bytes(command)

    def test_diag_unique_out_of_order_and_duplicate(self):
        reply = q.Reply("c1", "DIAG")
        reply.feed("D c1 2/3\nb")
        reply.feed("D c1 2/3\nb")
        self.assertFalse(reply.event.is_set())
        reply.feed("D c1 3/3\nc")
        self.assertFalse(reply.event.is_set())
        reply.feed("D c1 1/3\na")
        self.assertTrue(reply.event.is_set())
        self.assertEqual(reply.result(), ["D c1 1/3\na", "D c1 2/3\nb", "D c1 3/3\nc"])

    def test_diag_max_supported_and_guard_boundary(self):
        for count in (12, 16):
            with self.subTest(parts=count):
                reply = q.Reply("c1", "DIAG")
                for part in reversed(range(1, count + 1)):
                    reply.feed("D c1 %d/%d\n%s" % (part, count, "x" * 1100))
                self.assertTrue(reply.event.is_set())
                self.assertIsNone(reply.error)
                self.assertEqual(len(reply.parts), count)

    def test_diag_malformed_conflict_and_busy(self):
        for bad in ("D c1 0/2\nx", "D c1 1/0\nx", "D c1 1/17\nx",
                    "D c1 1/x\nx", "D c1 1/2", "D c1 1/2\n" + "x" * 1101):
            with self.subTest(bad=bad[:40]):
                reply = q.Reply("c1", "DIAG")
                reply.feed(bad)
                self.assertTrue(q.response_failed(reply.result()))
        for second in ("D c1 1/2\ny", "D c1 2/3\ny"):
            reply = q.Reply("c1", "DIAG")
            reply.feed("D c1 1/2\nx")
            reply.feed(second)
            self.assertTrue(q.response_failed(reply.result()))
        reply = q.Reply("c1", "DIAG")
        reply.feed("A c1 ERR DIAG busy")
        self.assertTrue(reply.event.is_set())
        self.assertTrue(q.response_failed(reply.result()))

    def test_record_all_1800_values_final_before_data(self):
        reply = q.Reply("c1", "RECORD 1800")
        reply.feed("A c1 OK RECORD ticks=1800 mean_us=33333")
        self.assertFalse(reply.event.is_set())
        for first in reversed(range(0, 1800, 30)):
            row = "R c1 %d\n%s" % (first, "4294967295," * 30)
            reply.feed(row)
            reply.feed(row)
        self.assertTrue(reply.event.is_set())
        self.assertIsNone(reply.error)
        self.assertEqual(sum(reply.records.values()), 1800)
        self.assertLess(reply.bytes, 24000)

    def test_record_partial_malformed_and_conflicting(self):
        reply = q.Reply("c1", "RECORD 31")
        reply.feed("R c1 0\n" + "1," * 30)
        reply.feed("A c1 OK RECORD ticks=31")
        self.assertFalse(reply.event.is_set())
        reply.fail("incomplete response before deadline")
        self.assertTrue(q.response_failed(reply.result()))
        for bad in ("R c1 1\n1,", "R c1 30\nx,", "R c1 30\n4294967296,",
                    "R c1 30\n1,2,", "A c1 OK RECORD ticks=30"):
            with self.subTest(bad=bad):
                reply = q.Reply("c1", "RECORD 31")
                reply.feed(bad)
                self.assertTrue(q.response_failed(reply.result()))
        reply = q.Reply("c1", "RECORD 31")
        reply.feed("R c1 30\n1,")
        reply.feed("R c1 30\n2,")
        self.assertTrue(q.response_failed(reply.result()))

    def test_drive_started_is_not_success_and_terminal_reason_matters(self):
        for verb in ("GOTO", "SCRIPT"):
            for reason, failed in (("arrived", False), ("ok", False), ("marked", False),
                                   ("timeout", True), ("stuck", True), ("cancelled by real pad", True)):
                with self.subTest(verb=verb, reason=reason):
                    reply = q.Reply("c1", verb + " test")
                    reply.feed("A c1 OK " + verb + " started")
                    self.assertFalse(reply.event.is_set())
                    reply.feed("A c1 OK " + verb + " DONE " + reason + " room=103")
                    self.assertTrue(reply.event.is_set())
                    self.assertEqual(q.response_failed(reply.result()), failed)
        reply = q.Reply("c1", "SCRIPT test")
        reply.feed("A c1 OK SCRIPT started")
        reply.fail("deadline")
        self.assertTrue(q.response_failed(reply.result()))

    def test_reply_storage_and_wait_policy(self):
        reply = q.Reply("c1", "SCRIPT test")
        for n in range(q.MAX_REPLY_PACKETS + 1):
            reply.feed("A c1 OK stage%d" % n)
        self.assertTrue(q.response_failed(reply.result()))
        self.assertLessEqual(len(reply.messages), q.MAX_REPLY_PACKETS)
        reply.fail("x" * 1000)
        self.assertLessEqual(len(reply.error), 240)
        self.assertEqual(q.wait_seconds("DIAG"), 30)
        self.assertEqual(q.wait_seconds("GOTO 0 0"), 75)
        self.assertEqual(q.wait_seconds("SCRIPT test"), 290)
        self.assertEqual(q.wait_seconds("RECORD 1800"), 82)
        self.assertLessEqual(q.wait_seconds("RECORD 999999999"), q.MAX_WAIT)


class SummaryCases(unittest.TestCase):
    def test_crlf_file_journal_summary(self):
        packets = ["T 1 99 1/2\nFA35 count=", "T 1 99 2/2\n7\n"]
        expected = q.summarize([journal(packet) for packet in packets])
        self.assertEqual(expected[0], "complete telemetry snapshots: 1")
        with tempfile.TemporaryDirectory() as folder:
            for ending in ("\n", "\r\n"):
                with self.subTest(ending=repr(ending)):
                    path = Path(folder) / "qalink.log"
                    path.write_bytes(ending.join(journal(packet) for packet in packets).encode() + ending.encode())
                    self.assertEqual(q.summarize(q.log_lines(str(path))), expected)

    def test_crlf_journal_retains_datagram_and_capture_identity(self):
        token = "abcdef012345:barn"
        payload = "T 1 99 1/1\nvalue=7\r\n"
        lines = [journal(packet) + "\r\n" for packet in
                 ("M 1 cap-start:" + token, payload, "M 2 cap-stop:" + token)]
        self.assertEqual(q.journal_packet(lines[1])[1], payload)
        self.assertEqual(q.capture_cut(lines, token), lines)
        self.assertEqual(q.summarize(lines)[0], "complete telemetry snapshots: 1")

    def test_crlf_journal_keeps_strict_payload_validation(self):
        valid = journal("T 1 99 1/1\nx=7")
        stamp, kind, encoded = valid.split(" ", 2)
        for bad in (encoded[:4] + "\r" + encoded[4:], encoded + "*", "!!!!"):
            with self.subTest(bad=bad):
                self.assertIsNone(q.journal_packet(stamp + " " + kind + " " + bad + "\r\n"))
        oversized = journal("T 1 99 1/1\n" + "x" * q.MAX_DATAGRAM) + "\r\n"
        self.assertIsNone(q.journal_packet(oversized))

    def test_exact_split_numeric_token_and_newline(self):
        payload = "fps=6\n" + " " * 1088 + "ms10 total=51.2\ndrv q=2\n"
        parts = [payload[i:i + 1100] for i in range(0, len(payload), 1100)]
        lines = [journal("T 1 99 %d/%d\n%s" % (i + 1, len(parts), part)) for i, part in enumerate(parts)]
        out = q.summarize(list(reversed(lines)) + lines)
        self.assertEqual(out[0], "complete telemetry snapshots: 1")
        self.assertTrue(any("ms10.total" in row and "51.20" in row for row in out))
        self.assertTrue(any("drv.q" in row and "2.00" in row for row in out))

    def test_partial_expiry_conflict_and_pending_limit(self):
        lines = [journal("T 1 1 1/2\nfps=100\n", 0), journal("T 2 2 1/1\nfps=6\n", 31)]
        out = q.summarize(lines)
        self.assertEqual(out[0], "complete telemetry snapshots: 1")
        self.assertIn("1; duplicate", out[1])
        self.assertTrue(any("6.00" in row and "n=1" in row for row in out))
        conflict = [journal("T 3 3 1/2\nfps=1\n"), journal("T 3 3 1/2\nfps=2\n"),
                    journal("T 3 3 2/2\nx=1\n")]
        self.assertEqual(q.summarize(conflict)[0], "complete telemetry snapshots: 0")
        flood = [journal("T %d %d 1/2\nfps=7\n" % (i, i)) for i in range(100)]
        out = q.summarize(flood)
        self.assertEqual(out[0], "complete telemetry snapshots: 0")
        self.assertIn("100; duplicate", out[1])

    def test_summary_rejects_malformed_parts_and_field_growth(self):
        lines = [journal("T 4294967296 1 1/1\nx=1"), journal("T 1 1 1/17\nx=1"), "bad X28 ***"]
        self.assertEqual(q.summarize(lines)[0], "complete telemetry snapshots: 0")
        with mock.patch.object(q, "MAX_FIELDS", 2), self.assertRaises(ValueError):
            q.summarize([journal("T 1 1 1/1\nx=1 y=2 z=3")])

    def test_capture_exact_identity_complete_markers_and_bounds(self):
        token = "abcdef012345:barn"
        lines = [journal("M 1 cap-start:wrong"), journal("M 2 cap-start:" + token),
                 journal("T 1 1 1/1\nfps=6"), journal("M 3 cap-stop:" + token)]
        cut = q.capture_cut(lines, token)
        self.assertEqual(len(cut), 3)
        self.assertEqual(q.summarize(cut)[0], "complete telemetry snapshots: 1")
        with self.assertRaises(ValueError):
            q.capture_cut(lines[:-1], token)
        with mock.patch.object(q, "CAPTURE_BYTES", 16), self.assertRaises(ValueError):
            q.capture_cut(lines, token)
        with mock.patch.object(q, "CAPTURE_LINES", 2), self.assertRaises(ValueError):
            q.capture_cut(lines, token)

    def test_log_line_and_file_read_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "log"
            Path(str(path) + ".1").write_text("old\n")
            path.write_text("new\n")
            self.assertEqual(list(q.log_lines(str(path))), ["old", "new"])
            with mock.patch.object(q, "LOG_BYTES", 3), self.assertRaises(ValueError):
                list(q.log_lines(str(path)))
            with mock.patch.object(q, "LOG_LINE_BYTES", 2), self.assertRaises(ValueError):
                list(q.log_lines(str(path)))
            self.assertFalse(q.log_kind("malformed", "T"))


class NetworkCases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = q.service_class(pi.Service)(str(Path(self.temp.name) / "log"), 0, "127.0.0.1:0")
        self.address = ("127.0.0.1", self.service.udp.getsockname()[1])
        self.control = "127.0.0.1:%d" % self.service.ctl.getsockname()[1]
        self.console = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.console.bind(("127.0.0.1", 0))
        self.console.settimeout(.1)
        self.worker_stop = threading.Event()
        self.workers = []
        self.loop, self.loop_result = background(self.service.serve)
        self.console.sendto(b"L 1 0\nready", self.address)
        eventually(lambda: self.service.console is not None)

    def tearDown(self):
        self.worker_stop.set()
        self.service.close()
        for thread in self.workers:
            thread.join(1)
        self.console.close()
        self.loop.join(1)
        eventually(lambda: not self.service.clients)
        self.assertFalse(self.loop.is_alive())
        self.assertFalse(any(isinstance(x, BaseException) for x in self.loop_result), self.loop_result)
        self.temp.cleanup()

    def respond(self, callback):
        def run():
            while not self.worker_stop.is_set():
                try:
                    raw, _ = self.console.recvfrom(1201)
                except socket.timeout:
                    continue
                except OSError:
                    break
                cid, command = raw.decode("ascii").split(" ", 1)
                if cid == "h0":
                    continue
                for reply in callback(cid, command):
                    self.console.sendto(reply.encode("latin-1"), self.address)
        thread, result = background(run)
        self.workers.append(thread)
        return result

    def test_real_socket_complete_diag_framing_preserves_dot_line(self):
        result = self.respond(lambda cid, command: ["D %s 2/2\ntail" % cid,
                               "D %s 2/2\ntail" % cid, "D %s 1/2\nfirst\n.\n" % cid])
        lines = q.send_control(self.control, "DIAG", 1)
        self.assertFalse(q.response_failed(lines), lines)
        self.assertIn(".", lines)
        self.assertTrue(lines[0].startswith("D c00000001 1/2"))
        eventually(lambda: not self.service.waiters)
        self.assertEqual(result, [])

    def test_real_socket_started_then_timeout_is_error_and_cleanup(self):
        self.respond(lambda cid, command: ["A %s OK SCRIPT started" % cid])
        with mock.patch.object(q, "wait_seconds", return_value=.08):
            lines = q.send_control(self.control, "SCRIPT walk", 1)
        self.assertTrue(q.response_failed(lines), lines)
        self.assertTrue(any("incomplete response" in row for row in lines))
        self.assertEqual(self.service.waiters, {})

    def test_slow_complete_diag_uses_30_second_policy(self):
        seen = []
        real_wait = q.wait_seconds
        def policy(command, minimum=5):
            seen.append(real_wait(command, minimum))
            return .5
        def slow(cid, command):
            for n in range(1, 13):
                time.sleep(.01)
                yield "D %s %d/12\n%s" % (cid, n, "x" * 1100)
        self.respond(slow)
        with mock.patch.object(q, "wait_seconds", side_effect=policy):
            lines = q.send_control(self.control, "DIAG", 1)
        self.assertFalse(q.response_failed(lines), lines)
        self.assertTrue(all(value >= 30 for value in seen), seen)

    def test_quiet_bulk_peer_can_probe_and_resume(self):
        self.service.last_rx = time.monotonic() - q.PEER_MAX_AGE - 10
        self.assertIn("send PING", self.service.send("MENU")[0])
        self.respond(lambda cid, command: ["A %s OK %s" % (cid, command)])
        for command in ("PING", "HELLO"):
            self.service.last_rx = time.monotonic() - q.PEER_MAX_AGE - 10
            self.assertFalse(q.response_failed(self.service.send(command, .2)))
        self.assertFalse(q.response_failed(self.service.send("MENU", .2)))

    def test_idle_client_flood_is_bounded_and_udp_still_drains(self):
        held = []
        try:
            for n in range(q.MAX_CLIENTS):
                held.append(socket.create_connection(self.service.ctl.getsockname(), timeout=1))
                eventually(lambda: len(self.service.clients) == n + 1)
            with socket.create_connection(self.service.ctl.getsockname(), timeout=1) as extra:
                self.assertIn(b"busy", extra.recv(100))
            old = self.service.last_rx
            self.console.sendto(b"L 2 0\nstill alive", self.address)
            eventually(lambda: self.service.last_rx > old)
            self.assertEqual(len(self.service.clients), q.MAX_CLIENTS)
        finally:
            for conn in held:
                conn.close()

    def test_slow_reader_is_closed_and_client_slot_released(self):
        server, client = socket.socketpair()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        with mock.patch.object(q, "CLIENT_IO_TIMEOUT", .08), mock.patch.object(
                self.service, "send", return_value=["x" * (q.MAX_REPLY_BYTES - 1)]):
            try:
                self.assertTrue(self.service.admit(server))
                client.sendall(b"@28 PING\n")
                eventually(lambda: server not in self.service.clients)
            finally:
                client.close()

    def test_thread_start_failure_releases_admission(self):
        for error in (RuntimeError("cannot start thread"), MemoryError("allocation failed")):
            server, client = socket.socketpair()
            try:
                with mock.patch.object(threading.Thread, "start", side_effect=error):
                    self.assertFalse(self.service.admit(server))
                self.assertNotIn(server, self.service.clients)
                self.assertEqual(server.fileno(), -1)
                for _ in range(q.MAX_CLIENTS):
                    self.assertTrue(self.service.client_slots.acquire(False))
                self.assertFalse(self.service.client_slots.acquire(False))
                for _ in range(q.MAX_CLIENTS):
                    self.service.client_slots.release()
            finally:
                client.close()

    def test_waiter_cap_send_error_and_teardown(self):
        pending = [background(lambda: self.service.send("PING", 2)) for _ in range(q.MAX_WAITERS)]
        eventually(lambda: len(self.service.waiters) == q.MAX_WAITERS)
        self.assertIn("busy", self.service.send("PING")[0])
        self.service.close()
        for thread, result in pending:
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertTrue(q.response_failed(result[0]), result)
        self.assertEqual(self.service.waiters, {})
        self.assertIn("stopped", self.service.send("PING")[0])

    def test_transport_send_failure_cleans_waiter(self):
        udp = self.service.udp
        class Broken:
            def sendto(self, *args):
                raise OSError("fixture send failure")
        try:
            self.service.udp = Broken()
            out = self.service.send("PING", .1)
            self.assertTrue(q.response_failed(out))
            self.assertEqual(self.service.waiters, {})
        finally:
            self.service.udp = udp

    def test_oversize_datagram_and_control_line(self):
        dropped = self.service.dropped
        self.console.sendto(b"T " + b"x" * 1200, self.address)
        eventually(lambda: self.service.dropped > dropped)
        with socket.create_connection(self.service.ctl.getsockname(), timeout=1) as conn:
            conn.sendall(b"X" * (q.MAX_COMMAND + 10) + b"\n")
            self.assertIn(b"exceeds limit", conn.recv(200))

    def test_log_rotation_and_original_oversize_preserved(self):
        with mock.patch.object(q, "LOG_BYTES", 256):
            for n in range(12):
                self.service.write("S", "x" * 80)
            self.assertLessEqual(os.path.getsize(self.service.log_path), 256)
            self.assertLessEqual(os.path.getsize(self.service.log_path + ".1"), 256)
            oversized = str(Path(self.temp.name) / "oversized")
            Path(oversized).write_bytes(b"x" * 257)
            with self.assertRaises(ValueError):
                q.service_class(pi.Service)(oversized, 0, "127.0.0.1:0")
            self.assertEqual(Path(oversized).read_bytes(), b"x" * 257)


class ClientCases(unittest.TestCase):
    def args(self, **kwargs):
        return types.SimpleNamespace(pi="pi@example", dir="~/qa link", local="", out="", **kwargs)

    def test_service_version_probe_and_script_socket_deadline(self):
        with mock.patch.object(q, "control_exchange", side_effect=[["legacy" ]]) as call:
            self.assertTrue(q.response_failed(q.send_control("x:1", "PING")))
            self.assertEqual(call.call_count, 1)
        with mock.patch.object(q, "control_exchange", side_effect=[["review28 enabled"], ["A c1 OK SCRIPT DONE ok"]]) as call:
            self.assertFalse(q.response_failed(q.send_control("x:1", "SCRIPT walk", 120)))
            self.assertGreaterEqual(call.call_args.args[2], 295)
        for timeout in (float("nan"), float("inf"), 0, -1, 301):
            self.assertTrue(q.response_failed(q.send_control("x:1", "PING", timeout)))

    def test_remote_flag_propagation_quoted_path_and_capture_helper(self):
        args = self.args()
        link = q.client_link(pc, args)
        with mock.patch.object(subprocess, "run", return_value=types.SimpleNamespace(returncode=0)) as run:
            self.assertEqual(link.send("SCRIPT look-around"), 0)
            remote = run.call_args.args[0][-1]
            self.assertIn("send --review28", remote)
            self.assertIn('"$HOME"/\'qa link\'/qalink_pi.py', remote)
            self.assertGreaterEqual(run.call_args.kwargs["timeout"], 310)
        with mock.patch.object(q, "bounded_output", return_value=(0, "line\n", "")) as run:
            self.assertEqual(link.cut_capture("abcdef012345:barn"), ["line"])
            self.assertIn("qalink_review28.py cut", run.call_args.args[0][-1])
            self.assertEqual(run.call_args.args[1], q.CAPTURE_BYTES)

    def test_bounded_child_output_deadline_and_both_pipes(self):
        command = [sys.executable, "-c", "import sys;sys.stdout.write('x'*4096);sys.stderr.write('ok')"]
        result, out, err = q.bounded_output(command, 4096, 2)
        self.assertEqual((result, len(out), err), (0, 4096, "ok"))
        with self.assertRaises(ValueError):
            q.bounded_output(command, 100, 2)
        with self.assertRaises(ValueError):
            q.bounded_output([sys.executable, "-c", "import sys;sys.stderr.write('x'*4097)"], 100, 2)
        with self.assertRaises(subprocess.TimeoutExpired):
            q.bounded_output([sys.executable, "-c", "import time;time.sleep(1)"], 100, .05)

    def test_capture_start_failure_stop_failure_and_unique_success(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(pc, "CAPTURE_STATE", str(Path(folder) / "state")):
            args = self.args()
            args.out = str(Path(folder) / "out")
            state = Path(pc.CAPTURE_STATE + ".review28")
            link = mock.Mock()
            link.send.return_value = 1
            self.assertEqual(q.capture(pc, link, args, ["start", "barn"]), 1)
            self.assertFalse(state.exists())
            link.send.return_value = 0
            self.assertEqual(q.capture(pc, link, args, ["start", "barn"]), 0)
            saved = json.loads(state.read_text())
            token = saved["token"]
            self.assertIn(token, link.send.call_args.args[0])
            link.send.return_value = 1
            self.assertEqual(q.capture(pc, link, args, ["stop"]), 1)
            self.assertTrue(state.exists())
            self.assertFalse(Path(args.out).exists())
            link.send.return_value = 0
            link.cut_capture.return_value = [journal("M 1 cap-start:" + token),
                journal("T 1 1 1/1\nfps=6"), journal("M 2 cap-stop:" + token)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(q.capture(pc, link, args, ["stop"]), 0)
            self.assertFalse(state.exists())
            self.assertEqual(len(list(Path(args.out).glob("barn-*.log"))), 1)
            self.assertEqual(len(list(Path(args.out).glob("barn-*.summary.txt"))), 1)

    def test_capture_labels_endpoint_and_session_line_bounds(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(pc, "CAPTURE_STATE", str(Path(folder) / "state")):
            args = self.args()
            link = mock.Mock()
            for label in ("../escape", "x" * 25, "bad space"):
                with self.assertRaises(ValueError):
                    q.capture(pc, link, args, ["start", label])
            self.assertFalse(link.send.called)
            args.mode, args.keep_going = "session", False
            args.file = str(Path(folder) / "session")
            Path(args.file).write_text("x" * 100000)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(q.client_main(pc, args), 1)

    def test_cli_dispatch_defaults_and_opt_in(self):
        with mock.patch.object(sys, "argv", ["qalink_pi.py", "send", "PING"]), mock.patch.object(pi, "send_command", return_value=7) as old:
            self.assertEqual(pi.main(), 7)
            old.assert_called_once()
        with mock.patch.object(sys, "argv", ["qalink_pi.py", "send", "--review28", "PING"]), mock.patch.object(q, "send_command", return_value=8) as new:
            self.assertEqual(pi.main(), 8)
            new.assert_called_once()
        with mock.patch.object(sys, "argv", ["qalink_pi.py", "serve", "--review28"]), mock.patch.object(q, "service_class") as factory:
            self.assertEqual(pi.main(), 0)
            service = factory.return_value.return_value
            service.serve.assert_called_once()
            service.close.assert_called_once()
        with mock.patch.object(sys, "argv", ["qalink.py", "--pi", "p", "--review28", "status"]), mock.patch.object(q, "client_main", return_value=9) as new:
            self.assertEqual(pc.main(), 9)
            new.assert_called_once()

    def test_legacy_definitions_exact_ast_and_code_identity(self):
        for name in ("qalink.py", "qalink_pi.py"):
            relative = str((DIR / name).relative_to(ROOT))
            old = subprocess.run(["git", "show", BASE + ":" + relative], cwd=ROOT, check=True, capture_output=True, text=True).stdout
            new = (DIR / name).read_text()
            old_ast = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(old).body
                       if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name != "main"}
            new_ast = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(new).body
                       if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name != "main"}
            self.assertEqual(old_ast, new_ast)
            old_code = {code.co_name: marshal.dumps(code) for code in compile(old, name, "exec").co_consts
                        if isinstance(code, types.CodeType) and code.co_name != "main"}
            new_code = {code.co_name: marshal.dumps(code) for code in compile(new, name, "exec").co_consts
                        if isinstance(code, types.CodeType) and code.co_name != "main"}
            self.assertEqual(old_code, new_code)


def main():
    global BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    BASE = args.base
    start = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if args.receipt:
        files = [DIR / name for name in ("qalink.py", "qalink_pi.py", "qalink_review28.py", "README.md")]
        files.append(Path(__file__).resolve())
        receipt = {"base": BASE, "scope": "Actual companion Python functions plus loopback TCP/UDP and child-process fixtures; no modem, console, SSH-server or hardware run",
                   "python": sys.version, "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                   "pass": result.wasSuccessful(), "host_elapsed_seconds": round(time.monotonic() - start, 3),
                   "identity": "All pre-existing non-main class/function ASTs and marshalled code objects exactly equal the named base; CLI main/help intentionally add default-off dispatch",
                   "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
                   "bounds": {name: getattr(q, name) for name in ("MAX_DATAGRAM", "MAX_COMMAND", "MAX_PARTS", "MAX_PART_BYTES", "MAX_CLIENTS", "MAX_WAITERS", "MAX_REPLY_BYTES", "MAX_REPLY_PACKETS", "LOG_BYTES", "CAPTURE_BYTES", "CAPTURE_LINES", "MAX_SNAPSHOTS", "SNAPSHOT_SECONDS", "MAX_FIELDS")}}
        path = Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + "\n")
    return int(not result.wasSuccessful())


if __name__ == "__main__":
    sys.exit(main())
