"""Publish docs/wiki/ to the GitHub wiki, or check its links.

  python3 .github/scripts/wiki_sync.py check
  python3 .github/scripts/wiki_sync.py build <wiki clone> [--repo owner/name] [--ref main]

docs/wiki/ is the source; the wiki is a copy. Pages link to each other as `Page.md#anchor` and to the repo by
relative path, so they also read correctly on github.com. `build` rewrites those for the wiki (`Page#anchor`, and
repo files to blob/raw URLs) and replaces every page in the clone, so a page deleted here goes from the wiki too.
`check` reports a link to a missing page, file or heading; `build` refuses while there is one.
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "docs/wiki"
NOT_PUBLISHED = {"README.md"}  # explains the folder to someone browsing the repo
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")


def masked(line):
    """The line with inline code blanked out, same length, so a link inside code isn't seen as one."""
    return CODE_SPAN.sub(lambda m: m.group(1) + "\0" * len(m.group(2)) + m.group(1), line)


def prose_lines(text):
    """(index, line) for each line outside fenced code blocks."""
    fence = None
    for i, line in enumerate(text.split("\n")):
        s = line.lstrip()
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        if s.startswith("```") or s.startswith("~~~"):
            fence = s[:3]
            continue
        yield i, line


def slug(heading):
    """GitHub's anchor for a heading's text."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path):
    found, seen = set(), {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for _, line in prose_lines(text):
        m = re.match(r"#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            s = slug(m.group(1))
            n = seen.get(s, 0)
            seen[s] = n + 1
            found.add(s if n == 0 else "%s-%d" % (s, n))
    return found


def links(text):
    """(line index, start, end, is_image, target) of each link target outside code."""
    for i, line in prose_lines(text):
        for m in LINK.finditer(masked(line)):
            yield i, m.start(3), m.end(3), bool(m.group(1)), line[m.start(3):m.end(3)]


def resolve(target, src_dir):
    """('page', name, anchor) | ('repo', path, anchor) | ('self', None, anchor) | ('url', None, None)."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
        return "url", None, None
    path, _, anchor = target.partition("#")
    if not path:
        return "self", None, anchor
    if "/" not in path and path.endswith(".md") and path not in NOT_PUBLISHED and os.path.isfile(os.path.join(src_dir, path)):
        return "page", path[:-3], anchor
    rel = os.path.normpath(os.path.join(SRC_REL, path)).replace(os.sep, "/")
    return "repo", rel, anchor


def pages(src_dir):
    return sorted(f for f in os.listdir(src_dir) if f.endswith(".md"))


def problems(root):
    src_dir = os.path.join(root, SRC_REL)
    out, cache = [], {}

    def has_anchor(path, anchor):
        if path not in cache:
            cache[path] = anchors(path)
        return anchor in cache[path]

    for page in pages(src_dir):
        page_path = os.path.join(src_dir, page)
        with open(page_path, encoding="utf-8") as f:
            text = f.read()
        for i, _, _, _, target in links(text):
            kind, ref, anchor = resolve(target, src_dir)
            where = "%s/%s:%d: %s" % (SRC_REL, page, i + 1, target)
            if kind == "url":
                continue
            if kind == "repo":
                full = os.path.join(root, ref)
                if ref.startswith("../") or not os.path.exists(full):
                    out.append(where + " (no such file)")
                    continue
                if anchor and full.endswith(".md") and not has_anchor(full, anchor):
                    out.append(where + " (no such heading)")
                continue
            target_path = page_path if kind == "self" else os.path.join(src_dir, ref + ".md")
            if anchor and not has_anchor(target_path, anchor):
                out.append(where + " (no such heading)")
    return out


def rewrite(text, src_dir, repo, ref):
    lines = text.split("\n")
    edits = {}
    for i, start, end, image, target in links(text):
        kind, path, anchor = resolve(target, src_dir)
        suffix = "#" + anchor if anchor else ""
        if kind == "page":
            new = path + suffix
        elif kind == "repo":
            how = "raw" if image else ("tree" if os.path.isdir(os.path.join(REPO_ROOT, path)) else "blob")
            new = "https://github.com/%s/%s/%s/%s%s" % (repo, how, ref, path, suffix)
        else:
            continue
        edits.setdefault(i, []).append((start, end, new))
    for i, spans in edits.items():
        line = lines[i]
        for start, end, new in sorted(spans, reverse=True):
            line = line[:start] + new + line[end:]
        lines[i] = line
    return "\n".join(lines)


def build(out_dir, repo, ref):
    src_dir = os.path.join(REPO_ROOT, SRC_REL)
    for name in os.listdir(out_dir):
        if name.endswith(".md"):
            os.remove(os.path.join(out_dir, name))
    written = []
    for page in pages(src_dir):
        if page in NOT_PUBLISHED:
            continue
        with open(os.path.join(src_dir, page), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(out_dir, page), "w", encoding="utf-8", newline="\n") as f:
            f.write(rewrite(text, src_dir, repo, ref))
        written.append(page)
    return written


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    b = sub.add_parser("build")
    b.add_argument("out_dir")
    b.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "tammai/sdlc"))
    b.add_argument("--ref", default="main")
    a = p.parse_args(argv)
    bad = problems(REPO_ROOT)
    for line in bad:
        print(line)
    if bad:
        print("%d broken link(s) in %s" % (len(bad), SRC_REL), file=sys.stderr)
        return 1
    if a.cmd == "build":
        written = build(a.out_dir, a.repo, a.ref)
        print("wrote %d page(s) to %s" % (len(written), a.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
