"""Run the suite in parallel: one job per test class (big classes split), one process per core.

    py -3.10 tests/run_parallel.py            # all cores
    py -3.10 tests/run_parallel.py -j 4       # four workers
    py -3.10 tests/run_parallel.py test_ship  # only modules whose name contains "test_ship"

Same tests as `unittest discover -s tests -t tests` (load_tests filters included), stdlib only.
Each worker gets its own temp folder, plugin data folder and security state folder, so hooks
that keep state outside the test's project folder don't collide. HOME stays: git commits need
the machine's identity. Exit code 1 when any test fails or errors.
"""
import argparse
import os
import sys
import tempfile
import time
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed

TESTS = os.path.dirname(os.path.abspath(__file__))
CHUNK = 6  # tests per job; no class uses setUpClass, so a class can be split freely


def _ids(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _ids(t)
        else:
            yield t


def jobs(filter_text):
    """Group the discovered tests into jobs of at most CHUNK tests from one class."""
    suite = unittest.defaultTestLoader.discover(TESTS, top_level_dir=TESTS)
    by_class, broken = {}, []
    for t in _ids(suite):
        tid = t.id()
        if tid.startswith("unittest.loader."):  # a module that failed to import
            broken.append(t)
            continue
        if filter_text and filter_text not in tid.split(".")[0]:
            continue
        by_class.setdefault(tid.rsplit(".", 1)[0], []).append(tid)
    out = []
    for ids in by_class.values():
        out += [ids[i:i + CHUNK] for i in range(0, len(ids), CHUNK)]
    out.sort(key=len, reverse=True)
    return out, broken


def _init(base):
    """Give this worker private copies of every folder a hook may write outside the test's project."""
    me = tempfile.mkdtemp(prefix="w%d-" % os.getpid(), dir=base)
    tmp = os.path.join(me, "tmp")
    os.makedirs(tmp)
    for k in ("TMP", "TEMP", "TMPDIR"):
        os.environ[k] = tmp
    tempfile.tempdir = None  # re-read the variables above
    os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(me, "plugin-data")
    os.environ["SECURITY_WARNINGS_STATE_DIR"] = os.path.join(me, "security")
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)


class _Timed(unittest.TestResult):
    def startTest(self, test):
        self._t = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        self.durations.append((test.id(), time.perf_counter() - self._t))
        super().stopTest(test)


def run_job(ids):
    os.chdir(TESTS)
    suite = unittest.defaultTestLoader.loadTestsFromNames(ids)
    result = _Timed()
    result.durations = []
    suite.run(result)
    return {"run": result.testsRun, "skipped": len(result.skipped), "durations": result.durations,
            "failures": [(t.id(), tb) for t, tb in result.failures] +
                        [(t.id(), "unexpected success\n") for t in result.unexpectedSuccesses],
            "errors": [(t.id(), tb) for t, tb in result.errors]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("module", nargs="?", default="", help="run only modules whose name contains this")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--slowest", type=int, default=10, help="list this many slowest tests")
    a = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    sys.path.insert(0, TESTS)
    work, broken = jobs(a.module)
    start = time.perf_counter()
    total = {"run": 0, "skipped": 0, "durations": [], "failures": [], "errors": []}
    for t in broken:  # an import error: run it here so its traceback is reported
        r = unittest.TestResult()
        t.run(r)
        total["run"] += r.testsRun
        total["errors"] += [(x.id(), tb) for x, tb in r.errors]
    with tempfile.TemporaryDirectory(prefix="sdlc-par-") as base:
        with ProcessPoolExecutor(max_workers=a.jobs, initializer=_init, initargs=(base,)) as pool:
            for f in as_completed([pool.submit(run_job, ids) for ids in work]):
                r = f.result()
                for k in total:
                    total[k] += r[k]
                if r["failures"] or r["errors"]:
                    sys.stdout.write("F")
                else:
                    sys.stdout.write(".")
                sys.stdout.flush()
    took = time.perf_counter() - start
    print()
    for kind in ("failures", "errors"):
        for tid, tb in sorted(total[kind]):
            print("=" * 70 + "\n%s: %s\n" % (kind[:-1].upper(), tid) + "-" * 70 + "\n" + tb)
    if a.slowest:
        print("Slowest tests:")
        for tid, s in sorted(total["durations"], key=lambda x: -x[1])[:a.slowest]:
            print("  %6.2fs  %s" % (s, tid))
    bad = len(total["failures"]) + len(total["errors"])
    print("Ran %d tests in %.1fs with %d workers (%d skipped)  %s" % (
        total["run"], took, a.jobs, total["skipped"],
        "FAILED (failures=%d, errors=%d)" % (len(total["failures"]), len(total["errors"])) if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
