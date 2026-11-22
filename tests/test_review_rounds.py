"""hooks/review_rounds.py: when the check of a review's fixes still fails, only the user's reply lets work go on."""
import json
import os
import subprocess
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "review_rounds.py")]
ASKED = ["python3", os.path.join(HOOKS, "user_answer.py")]
STATE = "# login\nStatus: active\nProcess: 3\nTrack: M\nRisk: low\nCurrent: Stage 3 – Review\n"


class ReviewRoundsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/state/login.md", STATE)
        self.write(".sdlc/config.json", '{"commands": {"test": "npm test"}}')

    def report(self, n, verdict):
        self.write(f".sdlc/.work/findings/login/code-reviewer-r{n}.md", f"# r{n}\n\nVERDICT: {verdict}\n")

    def edit(self, path="src/login.ts"):
        _, out, _, err = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Edit",
                                         "tool_input": {"file_path": self.path(path)}}, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def bash(self, command):
        _, out, _, _ = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Bash",
                                       "tool_input": {"command": command}}, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_a_failing_check_of_the_fixes_stops_until_the_user_answers(self):
        self.report(1, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # round 1's bugs are fixed without asking
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.assertIsNone(self.bash("npm test"))  # the project's tests change no code
        self.assertEqual(self.bash("npm test && git commit -am x"), "deny")
        self.assertIsNone(self.edit(".sdlc/.work/findings/login/security-r2.md"))  # a reviewer finishing its report
        os.remove(self.path(".sdlc/.work/findings/login/code-reviewer-r2.md"))  # deleting the report doesn't reset it
        self.assertEqual(self.edit(), "deny")
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "one more round"}, self.root)
        self.assertIsNone(self.edit())
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # the granted round failed too: ask again

    def test_a_monitor_command_is_held_at_the_cap_like_bash(self):
        # .sdlc/2026-11-22-s-monitor-other-hooks AC-001: Monitor runs a shell command too
        self.report(2, "FAIL — 1 high: H1")
        _, out, _, _ = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Monitor",
                                       "tool_input": {"command": "npm test && git commit -am x", "description": "d"}},
                                self.root)
        self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        with open(os.path.join(os.path.dirname(HOOK[-1]), "hooks.json"), encoding="utf-8") as f:
            pre = json.load(f)["hooks"]["PreToolUse"]
        [matcher] = [e["matcher"] for e in pre if any("review_rounds.py" in h["command"] for h in e["hooks"])]
        self.assertIn("Monitor", matcher.split("|"))

    def answer(self, header="Review cap", forged=False, use_id="toolu_1"):
        q = {"question": "One more round?", "header": header, "options": [{"label": "One more round"}, {"label": "Stop"}]}
        given = {q["question"]: "One more round"}
        _, out, _, _ = run_hook(ASKED, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "AskUserQuestion",
                                        "tool_use_id": use_id,
                                        "tool_input": dict({"questions": [q]}, **({"answers": given} if forged else {}))},
                                self.root)
        if forged:
            return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")
        run_hook(HOOK, {"hook_event_name": "PostToolUse", "cwd": self.root, "tool_name": "AskUserQuestion",
                        "tool_use_id": use_id, "tool_input": {"questions": [q], "answers": given},
                        "tool_response": {"questions": [q], "answers": given}}, self.root)

    def test_the_users_answer_to_the_review_cap_question_grants_one_round(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.answer(header="Color")  # an answer to another question grants nothing
        self.assertEqual(self.answer(forged=True, use_id="toolu_forged"), "deny")  # an answer the agent filled in
        self.assertEqual(self.edit(), "deny")
        self.answer()
        self.assertIsNone(self.edit())
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")

    def config(self, rounds):
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}, "review_rounds": rounds}))

    def prompt(self, text="go on"):
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": text}, self.root)

    def reason(self):
        _, out, _, _ = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Edit",
                                       "tool_input": {"file_path": self.path("src/login.ts")}}, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecisionReason") or ""

    def test_a_configured_cap_moves_the_stop(self):
        self.prompt("/sdlc:setup review-rounds 3")  # the number is read from the user's prompt
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # round 3 runs without asking
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.assertIn("login (round 3): the last review round allowed", self.reason())

    def test_a_raise_waits_for_the_users_prompt_a_lower_cap_applies_at_once(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.config(4)  # written by the agent: no command from the user
        self.assertEqual(self.edit(), "deny")  # still capped at 2
        self.prompt("/sdlc:setup review-rounds")  # no number: shows the value, blesses nothing
        self.assertIsNone(self.edit())  # it was a plain reply: one grant
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # 2 + 1: the agent's 4 never counted
        self.prompt("/sdlc:setup review-rounds 5")  # while held: no config write needed, so no deadlock
        self.report(4, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # cap 5; grants alone (2 + 2) would stop here
        self.report(5, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # the grant never stacks on the new cap
        self.prompt("/sdlc:setup review-rounds 2")  # lowered, at once
        self.assertEqual(self.edit(), "deny")

    def test_a_typed_cap_is_written_to_config_and_a_later_lower_value_still_lowers_it(self):
        self.prompt("/sdlc:setup review-rounds 5")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual((cfg["review_rounds"], cfg["commands"]), (5, {"test": "npm test"}))  # the rest kept
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())
        self.config(2)  # lowered later, by hand or by the agent
        self.assertEqual(self.edit(), "deny")

    def test_grants_survive_a_cap_that_goes_down_and_back_up(self):
        self.commit_config(4)
        for n in (1, 2, 3, 4):
            self.report(n, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.prompt()  # round 5 allowed
        self.config(2)
        self.assertIsNone(self.edit())  # a grant is the user's: config doesn't take it back
        self.config(4)
        self.assertIsNone(self.edit())
        self.prompt("/sdlc:setup review-rounds " + "1" * 5000)  # not a cap: a plain reply, never a crash
        with open(self.path(".sdlc/.work/review-rounds.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["login"]["ceiling"], 2)

    def test_the_agent_cant_climb_back_above_a_lower_value(self):
        self.commit_config(4)
        self.prompt("/sdlc:setup review-rounds 2")  # the user's 2 under the team's 4
        self.config(4)  # the agent puts 4 back
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.prompt("/sdlc:setup review-rounds 5")
        self.assertIsNone(self.edit())
        self.config(3)  # lowered by hand
        self.assertIsNone(self.edit())  # the next call sees it: the ceiling is 3, round 2 under it
        self.config(5)  # and the agent raises it again
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # the ceiling went down to 3 and stays

    def test_a_lower_value_before_round_2_still_counts(self):
        self.commit_config(4)
        self.report(1, "FAIL — 1 high: H1")
        self.config(2)  # lowered in round 1
        self.assertIsNone(self.edit())  # nothing holds in round 1, but the ceiling sees the 2
        self.config(4)  # the agent puts 4 back
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")

    def test_a_typed_cap_equal_to_a_float_in_config_is_written(self):
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}, "review_rounds": 3.0}))
        self.prompt("/sdlc:setup review-rounds 3")
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertIs(type(json.load(f)["review_rounds"]), int)

    def test_a_config_read_mid_edit_holds_one_call_not_for_good(self):
        self.commit_config(4)
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())
        self.write(".sdlc/config.json", '{"review_rounds": 4,')  # a save half done
        self.assertEqual(self.edit(), "deny")  # 2 while it can't be read
        self.config(4)
        self.assertIsNone(self.edit())  # the committed 4 is back

    def said(self, text):
        _, out, _, _ = run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": text}, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext") or ""

    def test_a_config_unreadable_on_the_first_call_doesnt_fix_the_ceiling(self):
        self.commit_config(4)
        self.write(".sdlc/config.json", '{"review_rounds": 4,')  # the first call meets a save half done
        self.assertIsNone(self.edit())
        self.config(4)
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # Base's 4 was still read

    def test_a_typed_cap_reaches_a_paused_feature(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # ceiling 2 stored
        self.write(".sdlc/state/login.md", STATE.replace("Status: active", "Status: paused"))
        self.prompt("/sdlc:setup review-rounds 4")
        self.write(".sdlc/state/login.md", STATE)  # resumed
        self.assertIsNone(self.edit())

    def test_an_out_of_range_typed_cap_is_named_not_granted(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIn("2 to 5", self.said("/sdlc:setup review-rounds 9"))
        self.assertEqual(self.edit(), "deny")  # not a grant either

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root writes through read-only modes")
    def test_a_typed_cap_that_cant_be_saved_says_so(self):
        os.chmod(self.path(".sdlc/config.json"), 0o444)
        try:
            self.assertIn("couldn't write", self.said("/sdlc:setup review-rounds 4"))
        finally:
            os.chmod(self.path(".sdlc/config.json"), 0o644)

    def test_every_typed_form_sets_the_cap(self):
        for typed in ("/setup review-rounds 3", "$sdlc-setup review-rounds 3", "/SDLC:SETUP Review-Rounds 3"):
            self.write(".sdlc/.work/review-rounds.json", "{}")
            self.prompt(typed)
            with open(self.path(".sdlc/.work/review-rounds.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["login"]["ceiling"], 3, typed)

    def test_a_typed_cap_with_no_feature_writes_only_config(self):
        os.remove(self.path(".sdlc/state/login.md"))
        self.prompt("/sdlc:setup review-rounds 3")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["review_rounds"], 3)
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/review-rounds.json")))

    def test_a_base_git_cant_read_gives_the_stricter_cap(self):
        self.config(4)
        self.write(".sdlc/state/login.md", STATE + "Base: deadbee\n")  # no such commit (no repo at all)
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root writes through read-only modes")
    def test_a_config_it_cant_write_keeps_the_cap_and_still_answers(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        os.chmod(self.path(".sdlc/config.json"), 0o444)
        os.chmod(self.path(".sdlc"), 0o555)  # no temp file either
        try:
            self.prompt("/sdlc:setup review-rounds 4")
        finally:
            os.chmod(self.path(".sdlc"), 0o755)
            os.chmod(self.path(".sdlc/config.json"), 0o644)
        self.assertEqual(self.edit(), "deny")  # config still says 2: no raise, and the hook didn't crash
        self.assertIn("sets the cap instead", self.reason())

    def test_a_raise_keeps_the_rounds_already_granted(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.prompt()
        self.report(3, "FAIL — 1 high: H1")
        self.prompt()  # granted twice: round 4 allowed
        self.prompt("/sdlc:setup review-rounds 3")
        self.assertIsNone(self.edit())  # a "raise" to 3 doesn't take round 4 back

    def commit_config(self, rounds, top=None):
        top = top or self.root
        git = lambda *a: subprocess.run(["git", "-C", top, *a], capture_output=True, encoding="utf-8",
                                        errors="replace", check=True).stdout.strip()
        self.config(rounds)
        git("init", "-q")
        git("add", os.path.relpath(self.path(".sdlc/config.json"), top))
        git("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "config")
        self.write(".sdlc/state/login.md", STATE + f"Base: {git('rev-parse', '--short', 'HEAD')}\n")

    def test_an_agent_lowered_config_applies_at_once(self):
        self.commit_config(4)
        for n in (1, 2, 3):
            self.report(n, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # the committed 4
        self.config(3)  # lowered mid-feature, no prompt
        self.assertEqual(self.edit(), "deny")

    def test_a_value_committed_before_the_feature_applies_without_a_prompt(self):
        self.commit_config(3)
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # the team's committed 3
        self.config(5)  # raised after Base, by the agent
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # still 3

    def test_a_committed_value_applies_below_the_git_top_level(self):
        top = self.root
        self.root = os.path.join(top, "apps", "web")
        try:
            self.commit_config(3, top=top)
            self.report(1, "FAIL — 1 high: H1")
            self.report(2, "FAIL — 1 high: H1")
            self.assertIsNone(self.edit())  # 3 from apps/web/.sdlc/config.json at Base
        finally:
            self.root = top

    def test_a_bad_value_keeps_the_cap_at_two(self):
        self.commit_config(4)
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # the committed 4 holds: a bad value below must be what lowers it
        for bad in (None, "4", True, 3.5, 1, 6, "not an object"):
            if bad == "not an object":
                self.write(".sdlc/config.json", "[5]")
            else:
                self.config(bad)
            self.assertEqual(self.edit(), "deny", bad)
        self.config(2)
        self.assertEqual(self.edit(), "deny")  # the ceiling follows a readable 2
        for bad in ("1", "6", "x", "\u0663"):  # typed values out of range, or not ASCII digits, set nothing
            self.prompt(f"/sdlc:setup review-rounds {bad}")
            with open(self.path(".sdlc/.work/review-rounds.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["login"]["ceiling"], 2, bad)
        self.prompt("/sdlc:setup review-rounds 3")
        with open(self.path(".sdlc/.work/review-rounds.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["login"]["ceiling"], 3)  # a valid one does

    def test_with_no_active_feature_it_writes_nothing(self):
        # Setup commits as it goes, before its .gitignore step: a store written here would land in those commits
        os.remove(self.path(".sdlc/state/login.md"))
        self.assertIsNone(self.edit())
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "go on"}, self.root)
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/review-rounds.json")))


if __name__ == "__main__":
    unittest.main()
