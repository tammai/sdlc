# sdlc plugin repo

Knowledge map: `knowledge/index.md` — read it before working in an area you haven't touched this session, then open only the docs relevant to the task.

- Tests: run the suite once, on Python 3.10 only: `py -3.10 -m unittest discover -s tests -t tests` (macOS/Linux: `python3.10 -m unittest discover -s tests -t tests`). It is the oldest Python here, so it catches syntax newer than the 3.9 floor and, below 3.15, the cp1252 crashes 3.15's UTF-8 default hides; a second run on a newer Python adds nothing.
- After adding or changing a plugin feature, run the stale-docs audit in `CONTRIBUTING.md` (Making changes → Stale-docs audit) before reporting it done.
