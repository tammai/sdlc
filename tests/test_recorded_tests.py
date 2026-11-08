"""Spec 03 S3: recorded acceptance tests run against the build verify.py starts, and stay read-only (ported
from 3.5.0-rc.2, ff2ac10)."""
import json
import os
import re
import subprocess
import sys
import time
import unittest

from helpers import PLUGIN_ROOT
import test_verify


class VerifyBase(test_verify.VerifyTest):
    """3.4.0's verify fixture; its own tests run in test_verify.py, not again here (load_tests)."""

    def read_state(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()


class TestLockTest:
    RUN = ("python3 -c \"import os, sys; sys.exit(0 if 'weak' in open('tests/t.py').read() "
           "or os.path.exists('done') else 1)\"")


SERVER = """import http.server, json, os, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        built = os.path.exists("built")
        body = json.dumps({"pong": "yes"}).encode()
        self.send_response(200 if built and self.path == "/api/ping" else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body if built else b"{}")
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
"""
HTTP_TEST = ("criterion: F-APP-01.AC1\nsteps:\n  - request: {method: GET, path: /api/ping}\n"
             "    expect: {status: 200, json: [{pointer: /pong, equals: \"yes\"}]}\n")


class AcceptanceBundleTest(VerifyBase):
    """Spec 03 S3: a row bound to an open recorded test runs it against the build verify.py starts."""

    def bundle(self, visibility="open", runner="http", sha=None):
        import hashlib
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.write("server.py", SERVER)
        with open(self.write("acceptance/http/F-APP-01.AC1.yaml", HTTP_TEST), "rb") as f:
            recorded = hashlib.sha256(f.read()).hexdigest()
        entry = {"criterion": "F-APP-01.AC1", "runner": runner, "path": "http/F-APP-01.AC1.yaml",
                 "sha256": sha or recorded, "level": "integration",
                 "visibility": visibility, "recorded_against": {"kind": "oss", "version_or_commit": "v1",
                                                                "base_url_env": "ACCEPT_BASE_URL"},
                 "last_green": {"timestamp": "2026-11-08T10:00:00Z", "target": "reference"}, "normalize": []}
        self.write("acceptance/manifest.json", json.dumps({"contracts": "1.0.0", "tests": [entry]}))
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                    "accept": {"start": f"python3 server.py {self.port}",
                                                               "base_url": f"http://127.0.0.1:{self.port}"}}))
        self.spec("AC-001")
        self.plan([("AC-001", "acceptance/http/F-APP-01.AC1.yaml",
                    "contracts.py run-http acceptance/http/F-APP-01.AC1.yaml")],
                  tasks=["1. t `server.py` `built` `acceptance/manifest.json` `acceptance/http/F-APP-01.AC1.yaml`"],
                  deviations=["- H (server.py) What: the stand-in build. Why: a fixture. Effect: none."])

    def test_a_recorded_http_test_runs_against_the_started_build(self):
        import socket
        self.bundle()
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)  # 404 from the unbuilt feature: a real red
        self.write("built", "")
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.assertNotIn("sha256:", self.read_state())  # a recorded test is guarded by its manifest, not locked
        with socket.socket() as s:  # the build verify.py started is stopped again
            s.settimeout(1)
            self.assertNotEqual(s.connect_ex(("127.0.0.1", self.port)), 0)

    def port_open(self):
        import socket
        with socket.socket() as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def test_the_build_is_stopped_on_a_failure_and_one_that_exits_is_not_run(self):
        self.bundle()
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        code, out, _ = self.verify()  # not built: the recorded test fails against the started build
        self.assertEqual(code, 1, out)
        self.assertIn("AC-001: its test fails", out)
        self.assertFalse(self.port_open())
        config = json.loads(open(self.path(".sdlc/config.json"), encoding="utf-8").read())
        config["accept"]["start"] = 'python3 -c "pass"'
        self.write(".sdlc/config.json", json.dumps(config))
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("not run: accept.start exited", out)

    def test_a_build_already_answering_is_not_taken_for_this_one(self):
        import threading
        import http.server
        self.bundle()
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        other = http.server.HTTPServer(("127.0.0.1", self.port), http.server.BaseHTTPRequestHandler)
        threading.Thread(target=other.serve_forever, daemon=True).start()
        try:
            code, out, _ = self.verify()
        finally:
            other.shutdown()
            other.server_close()
        self.assertEqual(code, 1, out)
        self.assertIn("already answers", out)

    def test_a_proxy_in_the_environment_is_not_taken_for_the_build(self):
        import socket
        import threading
        import http.server
        self.bundle()
        self.write("built", "")
        self.assertEqual(self.verify("red", "AC-001")[0], 1)  # built already: not a red, but the record is stamped
        os.remove(self.path("built"))
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        self.write("built", "")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            proxy_port = s.getsockname()[1]
        proxy = http.server.HTTPServer(("127.0.0.1", proxy_port), http.server.BaseHTTPRequestHandler)
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        saved = {k: os.environ.get(k) for k in ("HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy")}
        try:
            for k in saved:
                os.environ.pop(k, None)
            os.environ["HTTP_PROXY"] = os.environ["http_proxy"] = f"http://127.0.0.1:{proxy_port}"
            code, out, _ = self.verify()
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v
            proxy.shutdown()
            proxy.server_close()
        self.assertNotIn("already answers", out)

    def test_a_folder_named_acceptance_without_a_manifest_is_an_ordinary_test(self):
        self.spec("AC-001")
        self.plan([("AC-001", "acceptance/test_login.py › ok", TestLockTest.RUN.replace("tests/t.py",
                                                                                       "acceptance/test_login.py"))],
                  tasks=["1. t `acceptance/test_login.py` `done`"])
        self.write("acceptance/test_login.py", "x = 1\n")
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        self.write("done", "")
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.write("acceptance/manifest.json", "[]")  # a manifest that isn't an object: a failure, no traceback
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)

    def test_a_maestro_row_runs_maestro_and_is_not_run_without_it(self):
        import shutil
        self.bundle(runner="maestro")
        self.plan([("AC-001", "acceptance/http/F-APP-01.AC1.yaml", "maestro test acceptance/http/F-APP-01.AC1.yaml")],
                  tasks=["1. t `server.py` `built` `acceptance/manifest.json` `acceptance/http/F-APP-01.AC1.yaml`"],
                  deviations=["- H (server.py) What: the stand-in build. Why: a fixture. Effect: none."])
        import tempfile
        empty = tempfile.mkdtemp(prefix="sdlc-bin-")  # outside the project, so it is no drift
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        path = os.environ["PATH"]
        try:
            # maestro missing: only the interpreter's and the shell's folders on PATH
            os.environ["PATH"] = os.pathsep.join([empty, os.path.dirname(sys.executable)] +
                                                 [os.path.dirname(shutil.which(x) or "")
                                                  for x in ("python3", "bash", "git")])
            if not shutil.which("maestro"):
                code, out, _ = self.verify("red", "AC-001")
                self.assertEqual(code, 1, out)
                self.assertIn("not run: maestro not installed", out)
            # a stand-in maestro that fails until the feature is built, as a flow would
            fake = os.path.join(empty, "maestro")
            with open(fake, "w", newline="\n") as f:
                f.write('#!/bin/sh\ntest -f built\n')
            os.chmod(fake, 0o755)
            with open(fake + ".cmd", "w") as f:
                f.write("@if exist built (exit /b 0) else (exit /b 1)\n")
            code, out, _ = self.verify("red", "AC-001")
            self.assertEqual(code, 0, out)
            self.write("built", "")
            code, out, _ = self.verify()
            self.assertEqual(code, 0, out)
        finally:
            os.environ["PATH"] = path

    def test_an_untrusted_bundle_row_fails(self):
        for kwargs, word in (({"visibility": "hidden"}, "hidden"), ({"sha": "0" * 64}, "sha256"),
                             ({"runner": "cli"}, "not run")):
            with self.subTest(word=word):
                self.bundle(**kwargs)
                code, out, _ = self.verify()
                self.assertEqual(code, 1, out)
                self.assertIn(word, out)


import test_role_guard  # noqa: E402
from helpers import run_hook  # noqa: E402

HOOK = test_role_guard.HOOK


class RecordedTestGuardTest(test_role_guard.RoleGuardTest):
    def bundle(self):
        self.write("acceptance/manifest.json", '{"contracts": "1.0.0", "tests": [{"criterion": "F-APP-01.AC1", '
                   '"runner": "http", "path": "http/F-APP-01.AC1.yaml", "visibility": "open"}]}')
        self.write("acceptance/http/F-APP-01.AC1.yaml", "criterion: F-APP-01.AC1\n")

    def bash(self, command, tool="Bash"):
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": tool,
                   "tool_input": {"command": command}}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_recorded_tests_are_read_only_for_file_tools(self):
        self.assertIsNone(self.call("Edit", "acceptance/http/F-APP-01.AC1.yaml"))  # no manifest: not a bundle
        self.bundle()
        for tool in ("Edit", "Write", "MultiEdit"):
            self.assertEqual(self.call(tool, "acceptance/http/F-APP-01.AC1.yaml"), "deny")
        self.assertEqual(self.call("Write", "acceptance/manifest.json"), "deny")
        self.assertEqual(self.call("Edit", "acceptance/http/F-APP-01.AC1.yaml", "general-purpose"), "deny")
        self.assertIsNone(self.call("Edit", "src/app.py"))
        self.assertIsNone(self.call("Read", "acceptance/http/F-APP-01.AC1.yaml"))

    def test_recorded_tests_are_read_only_for_shell_writes(self):
        self.bundle()
        test = "acceptance/http/F-APP-01.AC1.yaml"
        for cmd in (f"echo x > {test}", f"echo x >> ./{test}", f"sed -i s/a/b/ {test}", f"rm -f {test}",
                    f"cp /tmp/other.yaml {test}", f"mv x.yaml '{test}'", "rm -rf acceptance", f"echo x | tee {test}",
                    f"git checkout -- {test}", f"cd . && truncate -s 0 {test}", "echo {} > acceptance/manifest.json"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "deny")
        self.assertEqual(self.bash(f"Set-Content -Path {test} -Value x", tool="PowerShell"), "deny")
        for cmd in (f"cat {test}", f"cp {test} /tmp/copy.yaml", f"python3 contracts.py run-http {test}",
                    "git status", "echo x > notes.txt"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.bash(cmd))

    def test_shell_writes_are_caught_in_every_spelling_and_ordinary_commands_are_not(self):
        self.bundle()
        test = "acceptance/http/F-APP-01.AC1.yaml"
        denied = [f"mv {test} /tmp/", "Remove-Item acceptance\\manifest.json", f"Move-Item {test} C:\\tmp",
                  f"sed -Ei s/a/b/ {test}", f"sed --in-place=.bak s/a/b/ {test}", f"git -C . checkout -- {test}",
                  "cd acceptance && rm manifest.json", "bash -c 'rm acceptance/manifest.json'", "rm -r *",
                  f"xargs rm < list.txt; rm {test}"]
        for cmd in denied:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd, tool="PowerShell" if "-Item" in cmd else "Bash"), "deny")
        for cmd in ("git checkout main -- acceptance/", "git restore acceptance"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "deny")
        os.makedirs(self.path("src"), exist_ok=True)
        for cmd in ("cp x.txt .", "cp seed.yaml acceptance/", "rm *", 'git commit -m "a > acceptance/manifest.json"',
                    "mv a.txt ..", "echo x 2>&1", "mv x.txt .", "cd src && mv a.txt ..", "chmod -R +x .",
                    "Remove-Item x.txt -Force", "rm -r acceptance\\ old", "git checkout main", "git checkout -- ."):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.bash(cmd))

    @unittest.skipUnless(os.name == "nt", "only Windows has paths no relative path reaches (another drive)")
    def test_a_git_operand_on_another_drive_doesnt_hide_the_next_one(self):
        self.bundle()
        other = "D:/x" if not self.root.upper().startswith("D:") else "E:/x"
        self.assertEqual(self.bash(f"git checkout -- {other} acceptance/manifest.json"), "deny")

    def test_file_tools_are_caught_in_every_spelling(self):
        self.bundle()
        for rel in ("acceptance/manifest.json.", "acceptance/manifest.json::$DATA", "acceptance/./http/../manifest.json"):
            with self.subTest(rel=rel):
                self.assertEqual(self.call("Write", rel), "deny")
        if os.path.normcase("A") == "a":  # a case-insensitive file system (Windows)
            self.assertEqual(self.call("Write", "ACCEPTANCE/Manifest.json"), "deny")

    def test_recorded_tests_are_read_only(self):
        test = "acceptance/http/F-APP-01.AC1.yaml"
        self.assertIsNone(self.bash(f"echo x > {test}"))  # no manifest: an ordinary folder, 3.4.0's answer
        self.assertIsNone(self.call("Write", test))
        self.bundle()
        self.assertEqual(self.call("Write", test), "deny")
        self.assertEqual(self.bash(f"echo x > {test}"), "deny")


def load_tests(loader, tests, pattern):
    """Only the tests this file defines: the fixture classes it extends run in their own files."""
    suite = unittest.TestSuite()
    for cls in (AcceptanceBundleTest, RecordedTestGuardTest):
        for name in loader.getTestCaseNames(cls):
            if name in vars(cls):
                suite.addTest(cls(name))
    return suite


if __name__ == "__main__":
    unittest.main()
