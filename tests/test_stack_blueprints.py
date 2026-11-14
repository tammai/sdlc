"""Stack blueprints folded into setup: how a stack is chosen, the sections, conventions and platforms."""
import os
import unittest

from helpers import PLUGIN_ROOT

REFS = ("skills", "setting-up-projects", "references")


def read_doc(*parts):
    with open(os.path.join(PLUGIN_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    """The text under `heading` up to the next heading of the same or a higher level."""
    level = heading.split(" ", 1)[0]
    start = text.index(heading + "\n")
    rest = text[start + len(heading) + 1:]
    ends = [i for i in (rest.find("\n" + "#" * n + " ") for n in range(1, len(level) + 1)) if i >= 0]
    return rest[:min(ends)] if ends else rest


class Selection(unittest.TestCase):
    def test_choosing_a_stack_table(self):
        stacks = read_doc(*REFS, "stacks.md")
        self.assertLess(stacks.index("\n## Choosing a stack\n"), stacks.index("\n## Nuxt"))
        choosing = section(stacks, "## Choosing a stack").lower()
        for term in ("one deployable", "standalone api", "one web client", "no mobile app", "internal", "small",
                     "crud", "cpu-heavy", "realtime", "high load", "go", "typescript", "python", "nuxt",
                     "next.js", "flutter", "the user names"):
            self.assertIn(term, choosing, term)
        self.assertIn("|", choosing)  # a table, not prose

    def test_warnings(self):
        warnings = section(read_doc(*REFS, "stacks.md"), "### Warnings").lower()
        for term in ("typescript", "python", "small crud", "no web or mobile", "two native", "macos",
                     "cloudflare workers", "background", "vercel", "commercial", "vps", "backups"):
            self.assertIn(term, warnings, term)

    def test_stack_interview_applies_the_table(self):
        step = section(read_doc(*REFS, "greenfield.md"), "## `stack` – interview, then propose (hard stop)")
        low = step.lower()
        for term in ("outside", "heaviest", "workload", "scale", "choosing a stack", "reason", "warning",
                     "approves"):
            self.assertIn(term, low, term)
        for ref in ("monorepo.md", "workbench.md"):
            stack_step = section(read_doc(*REFS, ref), "## `stack` – interview, then propose (hard stop)")
            self.assertIn("Choosing a stack", stack_step, ref)


if __name__ == "__main__":
    unittest.main()
