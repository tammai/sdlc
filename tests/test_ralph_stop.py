"""hooks/stop-hook.sh: the ralph-loop Stop hook."""
import json
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["bash", os.path.join(HOOKS, "stop-hook.sh")]
STATE = ".claude/ralph-loop.local.md"


class RalphStopTest(ProjectTestCase):
    def start_loop(self, iteration=1, max_iterations=0, promise="DONE", session="s1", prompt="Fix the auth bug"):
        promise_yaml = f'"{promise}"' if promise else "null"
        self.write(STATE, f"""---
active: true
iteration: {iteration}
session_id: {session}
max_iterations: {max_iterations}
completion_promise: {promise_yaml}
started_at: "2026-10-22T00:00:00Z"
---

{prompt}
""")

    def transcript(self, *texts):
        # Compact separators: real transcripts have no spaces, and the hook greps for '"role":"assistant"'
        lines = [json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                              "content": [{"type": "text", "text": t}]}},
                            separators=(",", ":"))
                 for t in texts]
        return self.write("transcript.jsonl", "\n".join(lines) + "\n")

    def stop(self, session="s1", transcript=None):
        payload = {"hook_event_name": "Stop", "session_id": session,
                   "transcript_path": transcript or self.transcript("working on it")}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return out, raw

    def iteration(self):
        with open(self.path(STATE)) as f:
            return next(int(l.split(":")[1]) for l in f if l.startswith("iteration:"))

    def test_no_loop_is_noop(self):
        out, raw = self.stop()
        self.assertEqual(raw, "")

    def test_active_loop_blocks_and_feeds_prompt_back(self):
        self.start_loop()
        out, _ = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"].strip(), "Fix the auth bug")
        self.assertIn("iteration 2", out["systemMessage"])
        self.assertEqual(self.iteration(), 2)

    def test_other_session_is_not_blocked(self):
        self.start_loop(session="s1")
        out, raw = self.stop(session="s2")
        self.assertEqual(raw, "")
        self.assertEqual(self.iteration(), 1)

    def test_completion_promise_ends_loop(self):
        self.start_loop()
        out, raw = self.stop(transcript=self.transcript("all green <promise>DONE</promise>"))
        self.assertNotIn('"decision"', raw)
        self.assertFalse(os.path.exists(self.path(STATE)))

    def test_wrong_promise_continues(self):
        self.start_loop()
        out, _ = self.stop(transcript=self.transcript("<promise>NOT YET</promise>"))
        self.assertEqual(out["decision"], "block")

    def test_max_iterations_ends_loop(self):
        self.start_loop(iteration=5, max_iterations=5)
        out, raw = self.stop()
        self.assertNotIn('"decision"', raw)
        self.assertFalse(os.path.exists(self.path(STATE)))

    def test_corrupt_state_stops_loop(self):
        self.write(STATE, "---\niteration: abc\nmax_iterations: 3\n---\nprompt\n")
        out, raw = self.stop()
        self.assertNotIn('"decision"', raw)
        self.assertFalse(os.path.exists(self.path(STATE)))


if __name__ == "__main__":
    unittest.main()
