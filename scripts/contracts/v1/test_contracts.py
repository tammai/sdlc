# contracts-version: 1.3.0
"""test_contracts.py — unit tests for contracts.py, one class per contract (C1–C7) plus the YAML subset.

  python3 contracts/v1/test_contracts.py                 # all
  python3 contracts/v1/test_contracts.py TestC5Departures

WHY IT SHIPS INSIDE contracts/v1/. The spec asks for a test of every rule and error message, and the
folder is vendored byte-identical into each consumer, so the tests travel with the code they prove
and any consumer can run them. Stdlib unittest only, like contracts.py.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contracts as C  # noqa: E402


def errors(issues):
    return [m for sev, m in issues if sev != "warning"]


def warnings(issues):
    return [m for sev, m in issues if sev == "warning"]


def has(messages, text):
    return any(text in m for m in messages)


SPEC_LINE = ('- [ ] **F-ISS-01.AC2** Given team ENG with 11 issues, when a member creates "Fix login", '
             'then it is shown as ENG-12. `[observed]`')

HTTP_EXAMPLE = """criterion: F-ISS-01.AC2
seed: [seed/team-eng-11-issues.yaml]
steps:
  - request: {method: POST, path: /api/teams/ENG/issues, account: MEMBER, json: {title: "Fix login"}}
    expect:
      status: 201
      json:
        - {pointer: /key, equals: "ENG-12"}
        - {pointer: /id, rule: uuid, capture: issue_id}
  - request: {method: GET, path: "/api/issues/{issue_id}", account: MEMBER}
    expect: {status: 200, json: [{pointer: /title, equals: "Fix login"}]}
"""

DEPARTURES_EXAMPLE = """- id: D-004
  kind: simplification        # simplification | deliberate-change | reference-defect-not-copied | environment | branding
  criteria: [F-ISS-07.AC3]
  features: [F-ISS-07]
  summary: Issue keys use 2–4 letters; the reference allows 1–5.
  match:                      # how automated diffs recognise it; empty = human-only
    - {runner: http, pointer: /key, rule: "regex:^[A-Z]{2,4}-\\\\d+$"}
  decided_by: "Tam Mai, features approval 2026-11-08"
  adr: decisions/0007-issue-keys.md
"""


def criteria(lines, profile="rspec", domain=None):
    return C.check_criteria("## Acceptance criteria\n\n" + "\n".join(lines) + "\n", profile, domain)


class TestC1Criteria(unittest.TestCase):
    def test_spec_example_passes(self):
        self.assertEqual(criteria([SPEC_LINE]), [])

    def test_id_format(self):
        self.assertEqual(C.check_id("F-ISS-01.AC2", "rspec"), [])
        self.assertTrue(has(errors(C.check_id("FISS01.AC2", "rspec")), "not a criterion ID"))
        self.assertTrue(has(errors(C.check_id("F-ISS-01.AC0", "rspec")), "numbered from 1"))
        self.assertTrue(has(errors(C.check_id("AC-001", "rspec")), "spec-backed"))
        self.assertEqual(C.check_id("AC-001", "sdlc-m"), [])
        self.assertTrue(has(errors(C.check_id("AC-000", "sdlc-m")), "numbered from 1"))

    def test_duplicate_id(self):
        self.assertTrue(has(errors(criteria([SPEC_LINE, SPEC_LINE])), "duplicate"))

    def test_grammar(self):
        line = '- [ ] **F-ISS-01.AC3** When a member creates "Fix login", it is shown as ENG-12. `[observed]`'
        self.assertTrue(has(errors(criteria([line])), "Given …, when …, then …."))
        line = ('- [ ] **F-ISS-01.AC3** Given a team, when a member creates "x", then it is ENG-1, '
                'then it is ENG-2. `[observed]`')
        self.assertTrue(has(errors(criteria([line])), "one observable behaviour"))

    def test_example_data_by_profile(self):
        line = '- [ ] **F-ISS-01.AC4** Given a team, when a member creates an issue, then it is shown. `[observed]`'
        self.assertTrue(has(errors(criteria([line])), "example data"))
        sdlc = line.replace("F-ISS-01.AC4", "AC-004").replace("[observed]", "[request]")
        self.assertTrue(has(warnings(criteria([sdlc], "sdlc-m")), "example data"))
        self.assertEqual(errors(criteria([sdlc], "sdlc-s")), [])
        self.assertTrue(has(errors(criteria([sdlc], "sdlc-l")), "example data"))
        manual = line.replace("`[observed]`", "`[observed]` `[manual: needs a printer]`")
        self.assertEqual(criteria([manual]), [])
        bare = line.replace("`[observed]`", "`[observed]` `[manual]`")
        self.assertTrue(has(errors(criteria([bare])), "[manual] needs a reason"))

    def test_named_state_from_domain(self):
        line = '- [ ] **F-ISS-01.AC5** Given an issue, when it is closed, then it is `archived`. `[docs]`'
        self.assertEqual(criteria([line], domain="States: `open`, `archived`."), [])
        self.assertTrue(has(errors(criteria([line], domain="States: `open`.")), "not a state in domain.md"))

    def test_source_tag(self):
        base = '- [ ] **F-ISS-01.AC6** Given a team, when a member creates "x", then it is ENG-1.'
        self.assertTrue(has(errors(criteria([base])), "no source tag"))
        self.assertTrue(has(errors(criteria([base + " `[docs]` `[api]`"])), "exactly one source tag"))
        self.assertTrue(has(errors(criteria([base + " `[request]`"])), "not allowed"))
        self.assertTrue(has(errors(criteria([base + " `[guess]`"])), "unknown tag"))
        fwd = base.replace("F-ISS-01.AC6", "AC-006") + " `[observed]`"
        self.assertTrue(has(errors(criteria([fwd], "sdlc-m")), "not allowed"))

    def test_removed_criterion(self):
        self.assertEqual(criteria(["- [ ] ~~**F-ISS-01.AC7** Given x, when y, then z.~~ removed: merged into AC2"]), [])
        self.assertTrue(has(errors(criteria(["- [ ] ~~**F-ISS-01.AC7** Given x, when y, then z.~~"])), "reason"))

    def test_malformed_lines_are_errors_not_crashes(self):
        line = '- [ ] **F-ISS-01.AC1 Given a team, when x, then "y". `[docs]`'
        self.assertTrue(has(errors(criteria([line])), "must be **bold**"))
        self.assertTrue(has(errors(criteria(['- [ ] AC-001 Given a, when b, then "c". `[request]`'], "sdlc-m")),
                            "no criterion line"))

    def test_only_the_acceptance_section_is_read(self):
        text = "## Story\n\n- **Note** free text\n\n## Acceptance criteria\n\n" + SPEC_LINE + "\n"
        self.assertEqual(C.check_criteria(text, "rspec"), [])


STORY = """# F-ISS-01 Create issue

## Story

As a member, I create an issue so the team sees it.

## Acceptance criteria

""" + SPEC_LINE + """

## Failure modes

- Title empty → F-ISS-01.AC2
- Two creates at once → MNB-1

## Must never break

- **MNB-1** Two issues never share a key — test: acceptance/http/F-ISS-01.AC2.yaml

## Differences from the original

- Keys use 2–4 letters → D-004

## Sources

- docs: https://example.invalid/issues
"""


class TestC2Story(unittest.TestCase):
    def test_valid_story(self):
        self.assertEqual(errors(C.check_story(STORY)), [])

    def test_missing_section(self):
        self.assertTrue(has(errors(C.check_story(STORY.split("## Sources")[0])), "missing section: Sources"))

    def test_edge_cases_removed(self):
        self.assertTrue(has(errors(C.check_story(STORY + "\n## Edge cases\n\n- x\n")), "Edge cases"))

    def test_failure_mode_arrow(self):
        self.assertTrue(has(errors(C.check_story(STORY.replace("Title empty → F-ISS-01.AC2", "Title empty"))),
                            "must end with → <criterion ID> or → MNB-<n>"))
        self.assertTrue(has(errors(C.check_story(STORY.replace("→ F-ISS-01.AC2", "→ F-ISS-01.AC9"))),
                            "unknown ID F-ISS-01.AC9"))

    def test_mnb_names_a_test(self):
        bad = STORY.replace(" — test: acceptance/http/F-ISS-01.AC2.yaml", "")
        self.assertTrue(has(errors(C.check_story(bad)), "names no test or check"))

    def test_difference_arrow(self):
        self.assertTrue(has(errors(C.check_story(STORY.replace(" → D-004", ""))), "→ D-<nnn>"))

    def test_criteria_checked(self):
        bad = STORY.replace("Given team ENG", "Team ENG")
        self.assertTrue(has(errors(C.check_story(bad)), "Given …, when …, then …."))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CRIT_TEXT = ('Given team ENG with 11 issues, when a member creates "Fix login", then it is shown as ENG-12. '
             '`[observed]`')


def make_lock(**over):
    entry = {"id": "F-ISS-01.AC2", "feature": "F-ISS-01", "file": "features/F-ISS-01-create-issue.md",
             "text_sha256": sha(CRIT_TEXT), "tag": "observed", "priority": "MVP", "level": 2,
             "test": "acceptance/http/F-ISS-01.AC2.yaml", "departures": []}
    entry.update(over)
    return {"contracts": "1.0.0", "spec": "docs/specs/trackr", "generated": "2026-11-08T10:00:00Z",
            "criteria": [entry]}


class TestC3Lock(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        feat = os.path.join(self.root, "docs", "specs", "trackr", "features")
        os.makedirs(feat)
        with open(os.path.join(feat, "F-ISS-01-create-issue.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("## Acceptance criteria\n\n" + SPEC_LINE + "\n")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_valid_lock(self):
        self.assertEqual(C.check_lock(make_lock(), self.root), [])

    def test_text_hash_is_line_after_id(self):
        self.assertEqual(C.criterion_text_sha256(SPEC_LINE), sha(CRIT_TEXT))
        self.assertEqual(C.criterion_text_sha256(SPEC_LINE.replace("[ ]", "[x]")), sha(CRIT_TEXT))

    def test_schema(self):
        lock = make_lock()
        del lock["criteria"][0]["text_sha256"]
        self.assertTrue(has(errors(C.check_lock(lock, self.root)), "text_sha256"))
        self.assertTrue(has(errors(C.check_lock(make_lock(level=3), self.root)), "level"))
        self.assertTrue(has(errors(C.check_lock(make_lock(tag="[observed]"), self.root)), "tag"))

    def test_inferred_never_at_level_1(self):
        self.assertTrue(has(errors(C.check_lock(make_lock(tag="inferred", level=1, test=None), self.root)),
                            "inferred"))
        self.assertEqual(C.check_lock(make_lock(tag="inferred", level=0, test=None), self.root), [])
        self.assertEqual(C.check_lock(make_lock(tag="inferred"), self.root), [])
        self.assertEqual(C.check_lock(make_lock(level=1, test=None), self.root), [])
        fixture = os.path.join(HERE, "fixtures", "lock", "invalid", "inferred-at-level-1.json")
        self.assertTrue(has(errors(C._fixture_issues("lock", fixture)), "inferred"))

    def test_semantics(self):
        self.assertTrue(has(errors(C.check_lock(make_lock(feature="F-ISS-02"), self.root)), "not under feature"))
        self.assertTrue(has(errors(C.check_lock(make_lock(test=None), self.root)), "level 2 needs a test"))

    def test_text_change_drops_level(self):
        issues = C.check_lock(make_lock(text_sha256=sha("old text")), self.root)
        self.assertEqual(errors(issues), [])
        self.assertTrue(has(warnings(issues), "level drops to 0"))

    def test_hash_not_checked_without_root(self):
        self.assertTrue(has(errors(C.check_lock(make_lock(), None)), "not run"))
        self.assertTrue(has(errors(C.check_lock(make_lock(file="features/gone.md"), self.root)), "not found"))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


SEED = """steps:
  - request: {method: POST, path: /seed, json: {team: ENG, issues: 11}}
    expect: {status: 200}
"""


def make_bundle(root, http_text=HTTP_EXAMPLE, **over):
    write(os.path.join(root, "http", "F-ISS-01.AC2.yaml"), http_text)
    write(os.path.join(root, "seed", "team-eng-11-issues.yaml"), SEED)
    entry = {"criterion": "F-ISS-01.AC2", "runner": "http", "path": "http/F-ISS-01.AC2.yaml",
             "sha256": sha(http_text), "level": "integration", "visibility": "open",
             "recorded_against": {"kind": "oss", "version_or_commit": "v2.7.4", "base_url_env": "ACCEPT_BASE_URL"},
             "last_green": {"timestamp": "2026-11-08T10:00:00Z", "target": "reference"}, "normalize": []}
    entry.update(over)
    write(os.path.join(root, "manifest.json"), json.dumps({"contracts": "1.0.0", "tests": [entry]}, indent=2))


class TestC4Bundle(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def check(self, http_text=HTTP_EXAMPLE, **over):
        make_bundle(self.root, http_text, **over)
        return C.check_bundle(self.root)

    def test_valid_bundle(self):
        self.assertEqual(self.check(), [])

    def test_manifest_fields(self):
        self.assertTrue(has(errors(self.check(sha256="0" * 64)), "sha256 does not match"))
        self.assertTrue(has(errors(self.check(path="e2e/F-ISS-01.AC2.yaml")), "runner http"))
        self.assertTrue(has(errors(self.check(visibility="secret")), "visibility"))
        self.assertTrue(has(warnings(self.check(level="unit")), "integration or e2e"))

    def test_no_url_or_secret(self):
        url = HTTP_EXAMPLE.replace("path: /api/teams/ENG/issues", "path: /api/x?next=https://ref.example/a")
        self.assertTrue(has(errors(self.check(url)), "URL"))
        secret = HTTP_EXAMPLE.replace('json: {title: "Fix login"}',
                                      'json: {title: "Fix login"}, headers: {Authorization: "Bearer abcdef123456"}')
        self.assertTrue(has(errors(self.check(secret)), "secret"))

    def test_http_file_validated(self):
        self.assertTrue(has(errors(self.check("criterion: F-ISS-01.AC2\n")), "steps"))
        self.assertTrue(has(errors(self.check(HTTP_EXAMPLE.replace("criterion: F-ISS-01.AC2", "criterion: F-ISS-01.AC3"))),
                            "does not match its file name"))
        self.assertTrue(has(errors(self.check(HTTP_EXAMPLE.replace("capture: issue_id", "capture: other"))),
                            "{issue_id}"))
        same = HTTP_EXAMPLE.replace('equals: "Fix login"', "rule: same-as:nope")
        self.assertTrue(has(errors(self.check(same)), "same-as:nope"))
        self.assertTrue(has(errors(self.check(HTTP_EXAMPLE.replace("rule: uuid", "rule: guid"))), "unknown rule"))

    def test_paths_stay_inside_the_bundle(self):
        make_bundle(self.root)
        write(os.path.join(self.root, "..", "elsewhere", "F-ISS-01.AC2.yaml"), HTTP_EXAMPLE)
        issues = C.check_bundle(self.root) + self.check(path="http/../../elsewhere/F-ISS-01.AC2.yaml")
        self.assertTrue(has(errors(issues), "outside the bundle"))
        for seed in ("../x.yaml", "C:x.yaml", "/x.yaml"):
            out = HTTP_EXAMPLE.replace("seed: [seed/team-eng-11-issues.yaml]", "seed: [%s]" % seed)
            self.assertTrue(has(errors(self.check(out)), "outside the bundle"), seed)

    def test_non_utf8_file_is_still_scanned(self):
        make_bundle(self.root)
        with open(os.path.join(self.root, "seed", "notes.bin"), "wb") as f:
            f.write(b"\xff\nawait page.goto('https://prod.example.com')\n")
        self.assertTrue(has(errors(C.check_bundle(self.root)), "URL"))

    def test_json_checks_must_be_a_list(self):
        self.assertTrue(has(errors(self.check(HTTP_EXAMPLE.replace(
            'expect: {status: 200, json: [{pointer: /title, equals: "Fix login"}]}', "expect: {status: 200, json: 5}"))),
            "json must be a list"))

    def test_seed_must_exist(self):
        make_bundle(self.root)
        os.remove(os.path.join(self.root, "seed", "team-eng-11-issues.yaml"))
        self.assertTrue(has(errors(C.check_bundle(self.root)), "seed/team-eng-11-issues.yaml not found"))


UUID = "3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b"


class _Ref(http.server.BaseHTTPRequestHandler):
    seeded = []

    def log_message(self, *a):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"null")
        if self.path == "/seed":
            _Ref.seeded.append(body)
            return self._send(200, {})
        if self.headers.get("Authorization") != "Bearer t1":
            return self._send(401, {"error": "auth"})
        self._send(201, {"key": "ENG-12", "id": UUID, "n": 12, "created": "2026-11-08T10:00:00Z"})

    def do_GET(self):
        if self.path == "/api/issues/" + UUID:
            return self._send(200, {"title": "Fix login"})
        if self.path == "/text":
            self.send_response(200)
            self.send_header("Content-Length", "5")
            self.end_headers()
            return self.wfile.write(b"hello")
        self._send(404, {})


class _Junk(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(65536)
        self.request.sendall(b"not http at all\r\n\r\n")


class TestC4RunHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Ref)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.root = tempfile.mkdtemp()
        _Ref.seeded = []

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_it(self, text=HTTP_EXAMPLE, env=None):
        make_bundle(self.root, text)
        if env is None:
            env = {"ACCEPT_BASE_URL": self.base, "ACCEPT_ACCOUNT_MEMBER": "Authorization: Bearer t1"}
        return C.run_http([os.path.join(self.root, "http", "F-ISS-01.AC2.yaml")], env)

    def test_spec_example_passes_against_reference(self):
        xml, failed = self.run_it()
        self.assertEqual(failed, 0, xml)
        self.assertIn('tests="1"', xml)
        self.assertIn('failures="0"', xml)
        self.assertEqual(_Ref.seeded, [{"team": "ENG", "issues": 11}])

    def test_mismatch_fails_with_pointer(self):
        xml, failed = self.run_it(HTTP_EXAMPLE.replace('equals: "ENG-12"', 'equals: "ENG-13"'))
        self.assertEqual(failed, 1)
        self.assertIn("/key", xml)
        self.assertIn("<failure", xml)

    def test_rules(self):
        extra = HTTP_EXAMPLE.replace(
            "        - {pointer: /id, rule: uuid, capture: issue_id}\n",
            "        - {pointer: /id, rule: uuid, capture: issue_id}\n"
            "        - {pointer: /n, rule: int}\n"
            "        - {pointer: /created, rule: iso8601}\n"
            "        - {pointer: /key, rule: \"regex:^[A-Z]{2,4}-\\\\d+$\"}\n")
        xml, failed = self.run_it(extra)
        self.assertEqual(failed, 0, xml)
        xml, failed = self.run_it(HTTP_EXAMPLE.replace("rule: uuid", "rule: int"))
        self.assertEqual(failed, 1, xml)

    def test_missing_target_is_not_run(self):
        xml, failed = self.run_it(env={"ACCEPT_ACCOUNT_MEMBER": "Authorization: Bearer t1"})
        self.assertEqual(failed, 1)
        self.assertIn("not run: ACCEPT_BASE_URL is not set", xml)
        xml, failed = self.run_it(env={"ACCEPT_BASE_URL": self.base})
        self.assertIn("not run: ACCEPT_ACCOUNT_MEMBER is not set", xml)

    def test_bad_target_is_a_failed_case_not_a_crash(self):
        acct = {"ACCEPT_ACCOUNT_MEMBER": "Authorization: Bearer t1"}
        xml, failed = self.run_it(env=dict(acct, ACCEPT_BASE_URL="127.0.0.1:9"))
        self.assertEqual(failed, 1)
        self.assertIn("<failure", xml)
        junk = socketserver.TCPServer(("127.0.0.1", 0), _Junk)
        threading.Thread(target=junk.serve_forever, daemon=True).start()
        try:
            xml, failed = self.run_it(env=dict(acct, ACCEPT_BASE_URL="http://127.0.0.1:%d" % junk.server_address[1]))
        finally:
            junk.shutdown()
            junk.server_close()
        self.assertEqual(failed, 1)
        self.assertIn("<failure", xml)

    def test_unreachable_target_fails(self):
        xml, failed = self.run_it(env={"ACCEPT_BASE_URL": "http://127.0.0.1:9",
                                       "ACCEPT_ACCOUNT_MEMBER": "Authorization: Bearer t1"})
        self.assertEqual(failed, 1)
        self.assertIn("<failure", xml)


class TestC5Departures(unittest.TestCase):
    def check(self, text):
        return C.check_departures(C.parse_yaml(text))

    def test_spec_example(self):
        self.assertEqual(self.check(DEPARTURES_EXAMPLE), [])

    def test_decided_by_required(self):
        bad = DEPARTURES_EXAMPLE.replace('  decided_by: "Tam Mai, features approval 2026-11-08"\n', "")
        self.assertTrue(has(errors(self.check(bad)), "decided_by"))

    def test_proposed_blocks(self):
        prop = DEPARTURES_EXAMPLE.replace('  decided_by: "Tam Mai, features approval 2026-11-08"\n',
                                          "  status: proposed\n")
        issues = self.check(prop)
        self.assertTrue(any(sev == "blocked" and "D-004" in m for sev, m in issues), issues)
        both = DEPARTURES_EXAMPLE + "  status: proposed\n"
        self.assertTrue(has(errors(self.check(both)), "proposed departure has no decided_by"))

    def test_fields(self):
        self.assertTrue(has(errors(self.check(DEPARTURES_EXAMPLE.replace("kind: simplification", "kind: whim"))), "kind"))
        self.assertTrue(has(errors(self.check(DEPARTURES_EXAMPLE.replace("id: D-004", "id: D4"))), "id"))
        self.assertTrue(has(errors(self.check(DEPARTURES_EXAMPLE + DEPARTURES_EXAMPLE)), "duplicate id D-004"))
        self.assertTrue(has(errors(self.check(DEPARTURES_EXAMPLE.replace("runner: http", "runner: curl"))), "runner"))


def make_finding(**over):
    f = {"id": "BH-0007", "source": "bug-hunter", "class": "build-defect", "severity": "high",
         "criterion": "F-ISS-01.AC2", "rule": None,
         "repro": {"runner": "http", "steps": [{"request": {"method": "GET", "path": "/api/issues/x"},
                                                 "expect": {"status": 200}}]},
         "observed": {"rebuild": "404", "reference": "200"}, "route": "sdlc",
         "verified_by": {"agent": "repro-verifier", "result": "reproduced"}}
    f.update(over)
    return f


def make_question(**over):
    f = {"id": "SQ-0001", "source": "sdlc-question", "class": "spec-gap", "severity": "medium",
         "criterion": "F-ISS-01.AC2", "rule": None, "repro": None, "observed": None, "route": "rspec",
         "question": "Does the key counter skip numbers of deleted issues?",
         "verified_by": {"agent": None, "result": "not run: spec question"}}
    f.update(over)
    return f


class TestC6Finding(unittest.TestCase):
    def test_valid_and_routed(self):
        self.assertEqual(C.check_finding(make_finding()), [])
        self.assertEqual(C.finding_route(make_finding()), "sdlc")

    def test_route_derived_from_class(self):
        self.assertTrue(has(errors(C.check_finding(make_finding(route="rspec"))), "route must be sdlc"))
        self.assertEqual(C.check_finding(make_finding(**{"class": "spec-gap", "route": "rspec"})), [])

    def test_fields(self):
        self.assertTrue(has(errors(C.check_finding(make_finding(**{"class": "nit"}))), "class"))
        f = make_finding()
        del f["verified_by"]
        self.assertTrue(has(errors(C.check_finding(f)), "verified_by"))
        bad = make_finding(repro={"runner": "http", "steps": []})
        self.assertTrue(has(errors(C.check_finding(bad)), "steps"))
        ok = make_finding(observed={"rebuild": "404", "reference": "not run: reference down"})
        self.assertEqual(C.check_finding(ok), [])

    def test_unverified_is_never_routed(self):
        f = make_finding(verified_by={"agent": "repro-verifier", "result": "not-reproduced"})
        self.assertEqual(C.check_finding(f), [])
        self.assertIsNone(C.finding_route(f))

    def test_spec_question_routed_without_verifier(self):
        q = make_question()
        self.assertEqual(C.check_finding(q), [])
        self.assertEqual(C.finding_route(q), "rspec")

    def test_non_question_without_reproduced_not_routed(self):
        # The C6 exception belongs to the exact spec-question shape; borrowing any part of it fails.
        borrowed = make_question(source="bug-hunter")
        self.assertTrue(has(errors(C.check_finding(borrowed)), "repro"))
        self.assertTrue(has(errors(C.check_finding(borrowed)), "verified_by.agent"))
        self.assertIsNone(C.finding_route(borrowed))
        no_text = make_question()
        del no_text["question"]
        self.assertTrue(has(errors(C.check_finding(no_text)), "question"))
        wrong_class = make_question(**{"class": "build-defect", "route": "sdlc"})
        self.assertTrue(has(errors(C.check_finding(wrong_class)), "spec-gap"))
        self.assertIsNone(C.finding_route(wrong_class))
        verified = make_question(verified_by={"agent": "repro-verifier", "result": "not-reproduced"})
        self.assertTrue(has(errors(C.check_finding(verified)), "not run: spec question"))
        self.assertIsNone(C.finding_route(verified))
        self.assertIsNone(C.finding_route(make_finding(verified_by={"agent": None,
                                                                    "result": "not run: spec question"})))
        self.assertTrue(has(errors(C.check_finding(make_finding(source="Bug Hunter"))), "source"))

    def test_version_is_1_3_0(self):
        self.assertEqual(C.VERSION, "1.3.0")
        for name in sorted(os.listdir(HERE)):
            path = os.path.join(HERE, name)
            if os.path.isfile(path) and name != "MANIFEST" and C.header_for(name):
                with open(path, encoding="utf-8") as f:
                    self.assertIn("contracts-version: 1.3.0", f.read(300), name)


COST = "\n".join([
    json.dumps({"ts": "2026-11-08T10:00:00Z", "plugin": "rspec", "stage": "verify", "agent": "recorder",
                "tier": "sonnet", "wall_s": 30, "turns": 4, "tokens_in": 1000, "tokens_out": 200, "result": "ok"}),
    json.dumps({"ts": "2026-11-08T10:01:00Z", "plugin": "rspec", "stage": "verify", "agent": "verify-judge",
                "tier": "opus", "wall_s": 12.5, "turns": 2, "tokens_in": None, "tokens_out": None, "result": "ok"}),
    json.dumps({"ts": "2026-11-08T10:02:00Z", "plugin": "sdlc", "stage": "build", "agent": "session",
                "tier": "session", "wall_s": 100, "turns": 10, "tokens_in": 5, "tokens_out": 6, "result": "ok"}),
]) + "\n"


class TestCli(unittest.TestCase):
    def test_cli_survives_cp1252_console(self):
        # A Windows console in cp1252 crashed on "routed: X → rspec".
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        fixture = os.path.join(HERE, "fixtures", "finding", "valid", "SQ-0001-spec-question.json")
        r = subprocess.run([sys.executable, os.path.join(HERE, "contracts.py"), "finding", fixture],
                           capture_output=True, env=env)
        self.assertNotIn(b"Traceback", r.stderr)
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"routed: SQ-0001 ? rspec", r.stdout)


class TestC7Cost(unittest.TestCase):
    def test_sums_by_stage(self):
        self.assertEqual(C.check_cost(COST), [])
        s = C.sum_cost(COST)
        self.assertEqual(s["verify"], {"runs": 2, "wall_s": 42.5, "turns": 6, "tokens_in": 1000,
                                       "tokens_out": 200, "tokens_unreported": 1})
        self.assertEqual(s["build"]["runs"], 1)

    def test_bad_line_named(self):
        bad = COST.replace('"wall_s": 12.5', '"wall_s": -1')
        self.assertTrue(has(errors(C.check_cost(bad)), "line 2"))
        self.assertTrue(has(errors(C.check_cost(COST + "not json\n")), "line 4"))


class TestYamlSubset(unittest.TestCase):
    def test_spec_http_example(self):
        d = C.parse_yaml(HTTP_EXAMPLE)
        self.assertEqual(d["seed"], ["seed/team-eng-11-issues.yaml"])
        self.assertEqual(d["steps"][0]["request"], {"method": "POST", "path": "/api/teams/ENG/issues",
                                                    "account": "MEMBER", "json": {"title": "Fix login"}})
        self.assertEqual(d["steps"][0]["expect"]["json"][1], {"pointer": "/id", "rule": "uuid", "capture": "issue_id"})
        self.assertEqual(d["steps"][1]["expect"], {"status": 200, "json": [{"pointer": "/title", "equals": "Fix login"}]})

    def test_spec_departures_example(self):
        d = C.parse_yaml(DEPARTURES_EXAMPLE)[0]
        self.assertEqual(d["kind"], "simplification")
        self.assertEqual(d["summary"], "Issue keys use 2–4 letters; the reference allows 1–5.")
        self.assertEqual(d["match"], [{"runner": "http", "pointer": "/key", "rule": "regex:^[A-Z]{2,4}-\\d+$"}])

    def test_scalars(self):
        d = C.parse_yaml("a: 12\nb: true\nc: ~\nd: 2026-11-08\ne: 'it''s'\nf: \"\\u00e9\\n\"\ng: 1.5\nh: no\n"
                         "list:\n- x\n- y\n")
        self.assertEqual(d, {"a": 12, "b": True, "c": None, "d": "2026-11-08", "e": "it's", "f": "é\n",
                             "g": 1.5, "h": "no", "list": ["x", "y"]})

    def test_outside_the_subset_names_the_line(self):
        cases = {
            "a: 1\nb: &x 2\n": "line 2: anchors",
            "a: 1\nb: *x\n": "line 2: aliases",
            "a: !!str 1\n": "line 1: tags",
            "a: |\n  text\n": "line 1: block scalars",
            "a: 1\n---\nb: 2\n": "line 2: multiple documents",
            "a: 1\na: 2\n": "line 2: duplicate key 'a'",
            "a:\n  b: 1\n   c: 2\n": "line 3: bad indentation",
            "a:\n\tb: 1\n": "line 2: tab",
            'a: "open\n': "line 1: unterminated",
            "a: {b: 1\n": "line 1: flow collection",
            ": x\n": "line 1: empty key",
            "x: {a:\n": "line 1: flow collection",
        }
        for text, msg in cases.items():
            with self.assertRaises(C.YamlError, msg=text) as ctx:
                C.parse_yaml(text)
            self.assertIn(msg, str(ctx.exception), text)


class TestRemainingMessages(unittest.TestCase):
    """The error messages the classes above do not reach: one input each, so every message has a test."""

    def test_yaml_messages(self):
        cases = {
            'a: "\\q"\n': "unknown escape \\q",
            "a: {b c}\n": "expected ':' after flow key",
            'a: ["x" y]\n': "expected ',' or ']'",
            "a: [1] x\n": "unexpected text after the value",
            "a: b: c\n": "a plain value cannot contain ': '",
            "a: 1\njust text\n": "expected 'key: value'",
            '"a" b: 1\n': "unexpected text after quoted key",
            "%YAML 1.2\na: 1\n": "directives are outside the subset",
            "a: %x\n": "'%' is reserved",
            "a: @x\n": "'@' is reserved",
            "a: `x`\n": "'`' is reserved",
            "? a\n": "complex keys are outside the subset",
        }
        for text, msg in cases.items():
            with self.assertRaises(C.YamlError, msg=text) as ctx:
                C.parse_yaml(text)
            self.assertIn(msg, str(ctx.exception), text)

    def test_criteria_and_story_messages(self):
        self.assertTrue(has(errors(criteria(["- [ ] ~~**F-ISS-01.AC7** text"])), "removed criterion must read"))
        story = STORY.replace("As a member, I create an issue so the team sees it.\n", "")
        self.assertTrue(has(errors(C.check_story(story)), "section Story is empty"))
        story = STORY.replace("- **MNB-1** Two issues", "- Two issues").replace("→ MNB-1", "→ F-ISS-01.AC2")
        self.assertTrue(has(errors(C.check_story(story)), "needs an MNB-<n> ID"))

    def test_lock_criterion_missing_from_file(self):
        root = tempfile.mkdtemp()
        try:
            write(os.path.join(root, "docs", "specs", "trackr", "features", "F-ISS-01-create-issue.md"), "# empty\n")
            self.assertTrue(has(errors(C.check_lock(make_lock(), root)), "not found in features/"))
        finally:
            shutil.rmtree(root)

    def test_schema_messages(self):
        found = errors(C.check_lock({"contracts": "x", "spec": "", "generated": "today", "criteria": "no"}, None))
        for text in ("must match", "must not be empty", "ISO 8601 date-time", "must be array"):
            self.assertTrue(has(found, text), (text, found))
        self.assertTrue(has(errors(C.check_cost(COST.replace('"turns": 4', '"turns": -4'))), "must be >= 0"))
        with self.assertRaises(C.SchemaUnsupported):
            C._validate({"exclusiveMinimum": 1}, 1, "", {}, [])

    def test_http_step_messages(self):
        steps = [
            ({"request": "x"}, "needs request and expect mappings"),
            ({"request": {"method": "FETCH", "path": "/a"}, "expect": {"status": 200}}, "method must be one of"),
            ({"request": {"method": "GET", "path": "a"}, "expect": {"status": 200}}, "path must start with /"),
            ({"request": {"method": "GET", "path": "/a", "account": "member"}, "expect": {"status": 200}},
             "account must be an upper-case name"),
            ({"request": {"method": "GET", "path": "/a"}, "expect": {"status": "200"}}, "expect.status must be an integer"),
            ({"request": {"method": "GET", "path": "/a"}, "expect": {"status": 200, "json": [{"pointer": "key"}]}},
             "needs a JSON pointer"),
            ({"request": {"method": "GET", "path": "/a"}, "expect": {"status": 200, "json": [{"pointer": "/k"}]}},
             "needs equals, rule or capture"),
            ({"request": {"method": "GET", "path": "/a"}, "expect": {"status": 200,
                                                                    "json": [{"pointer": "/k", "capture": "1x"}]}},
             "capture must be a name"),
            ({"request": {"method": "GET", "path": "/a"}, "expect": {"status": 200,
                                                                    "json": [{"pointer": "/k", "rule": "regex:("}]}},
             "is not a valid regex"),
        ]
        for step, msg in steps:
            found = errors(C.check_http_test({"criterion": "F-ISS-01.AC2", "steps": [step]}, "t.yaml"))
            self.assertTrue(has(found, msg), (msg, found))
        self.assertTrue(has(errors(C.check_http_test({"criterion": "X", "steps": []}, "t.yaml")),
                            "criterion must be a criterion ID"))
        self.assertTrue(has(errors(C.check_http_test({"criterion": "F-ISS-01.AC2", "seed": "s.yaml", "steps": []},
                                                     "t.yaml", None, ".")), "seed must be a list of paths"))

    def test_vendor_check_messages(self):
        tmp = tempfile.mkdtemp()
        try:
            copy = os.path.join(tmp, "v1")
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            manifest = os.path.join(copy, "MANIFEST")
            with open(manifest, encoding="utf-8") as f:
                lines = f.read().split("\n")
            with open(manifest, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(["contracts-version: 0.9.0", "garbage"] + lines[1:]))
            found = errors(C.vendor_check(copy))
            self.assertTrue(has(found, "MANIFEST line 1 is 'contracts-version: 0.9.0'"), found)
            self.assertTrue(has(found, "MANIFEST line 2 is not"), found)
            write(os.path.join(copy, "notes.txt"), "x")
            write(os.path.join(copy, "fixtures", "cost", "valid", "bad.jsonl"), "not json\n")
            write(os.path.join(copy, "fixtures", "cost", "invalid", "good.jsonl"), COST)
            C.seal(copy)
            found = errors(C.vendor_check(copy))
            self.assertTrue(has(found, "no header rule for notes.txt"), found)
            self.assertTrue(has(found, "fixture cost/valid/bad.jsonl should pass: line 1: not JSON"), found)
            self.assertTrue(has(found, "fixture cost/invalid/good.jsonl should fail but passed"), found)
            schema = os.path.join(copy, "cost-line.schema.json")
            with open(schema, encoding="utf-8") as f:
                data = json.load(f)
            del data["$comment"]
            write(schema, json.dumps(data))
            write(os.path.join(copy, "fixtures", "nonsense", "valid", "x.txt"), "x")
            C.seal(copy)
            found = errors(C.vendor_check(copy))
            self.assertTrue(has(found, 'cost-line.schema.json must have "$comment"'), found)
            self.assertTrue(has(found, "not run: fixtures"), found)
        finally:
            shutil.rmtree(tmp)


class TestRunHttpMessages(TestC4RunHttp):
    def test_failure_messages(self):
        acct = {"ACCEPT_BASE_URL": self.base, "ACCEPT_ACCOUNT_MEMBER": "Authorization: Bearer t1"}
        cases = [
            (HTTP_EXAMPLE, dict(acct, ACCEPT_ACCOUNT_MEMBER="Bearer t1"), "must be a header line 'Name: value'"),
            (HTTP_EXAMPLE, dict(acct, ACCEPT_ACCOUNT_MEMBER="Authorization: Bearer no"), "status 401, expected 201"),
            (HTTP_EXAMPLE.replace("pointer: /key, equals", "pointer: /nope, equals"), acct,
             "/nope: not present in the response"),
            (HTTP_EXAMPLE.replace("rule: uuid", "rule: int"), acct, "does not satisfy rule int"),
            (HTTP_EXAMPLE.replace("steps:", "stepz:"), acct, "invalid test"),
            (HTTP_EXAMPLE, dict(acct, ACCEPT_BASE_URL="http://127.0.0.1:9"), "request failed"),
        ]
        for text, env, msg in cases:
            xml, failed = self.run_it(text, env)
            self.assertEqual(failed, 1, msg)
            self.assertIn(escape_xml(msg), xml)

    def test_non_json_response(self):
        text = HTTP_EXAMPLE.replace('path: "/api/issues/{issue_id}"', "path: /text")
        xml, failed = self.run_it(text)
        self.assertIn("response is not JSON", xml)


def escape_xml(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    unittest.main()
