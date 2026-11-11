# contracts-version: 1.3.0
"""contracts.py — validators for the shared contracts v1 (C1–C7 in CONTRACTS.md), stdlib only.

  python3 contracts.py id F-ISS-01.AC2 [--profile rspec|sdlc-s|sdlc-m|sdlc-l]
  python3 contracts.py criteria <story-or-change.md> [--profile …] [--domain domain.md]
  python3 contracts.py story <story.md>
  python3 contracts.py lock <criteria.lock.json> [--root <repo>]
  python3 contracts.py bundle <acceptance-dir>
  python3 contracts.py run-http <test.yaml>...          # target from ACCEPT_BASE_URL, prints JUnit XML
  python3 contracts.py departures <departures.yaml>
  python3 contracts.py finding <finding.json>...
  python3 contracts.py cost <cost.jsonl>
  python3 contracts.py vendor-check <contracts/v1>      # every consumer's drift test
  python3 contracts.py seal <contracts/v1>              # canonical repo only: rewrite MANIFEST

WHY ONE STDLIB FILE. rspec, sdlc, bug-hunter and product-rebuild exchange specs, tests and findings
in these formats, and none may depend on another at runtime (decision D1). So this folder is copied
byte-identical into each of them, and a single file with no imports outside the standard library is
the only thing that copies cleanly into four plugins with four install stories. That is also why it
carries its own YAML subset parser and its own JSON Schema subset: PyYAML and jsonschema would each
be a dependency to vendor four times.

Exit codes: 0 no errors (warnings allowed) · 1 errors, blocked or failed tests · 2 usage.
Every issue is printed as `error: …`, `warning: …` or `blocked: …`.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape, quoteattr

# Must equal the version in MANIFEST and in every header; vendor-check compares them.
VERSION = "1.3.0"
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- YAML subset

class YamlError(ValueError):
    def __init__(self, line, message):
        super().__init__("line %d: %s" % (line, message))
        self.line = line


_INDICATORS = {
    "&": "anchors are outside the subset",
    "*": "aliases are outside the subset",
    "!": "tags are outside the subset",
    "|": "block scalars are outside the subset; use a quoted string with \\n",
    ">": "block scalars are outside the subset; use a quoted string with \\n",
    "%": "'%' is reserved; quote the value",
    "@": "'@' is reserved; quote the value",
    "`": "'`' is reserved; quote the value",
    "?": "complex keys are outside the subset",
}
_ESCAPES = {"\\": "\\", '"': '"', "/": "/", "n": "\n", "t": "\t", "r": "\r", "0": "\0", "b": "\b",
            "f": "\f", " ": " ", "e": "\x1b"}
_INT = re.compile(r"[-+]?[0-9]+")
_FLOAT = re.compile(r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?")


def _resolve(s):
    """YAML 1.2 core schema: `no`, `on` and dates stay strings, unlike YAML 1.1."""
    if s in ("null", "Null", "NULL", "~"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _INT.fullmatch(s):
        return int(s)
    if re.fullmatch(r"0o[0-7]+", s):
        return int(s[2:], 8)
    if re.fullmatch(r"0x[0-9a-fA-F]+", s):
        return int(s[2:], 16)
    if _FLOAT.fullmatch(s):
        return float(s)
    if s in (".inf", ".Inf", ".INF", "+.inf", "+.Inf", "+.INF"):
        return float("inf")
    if s in ("-.inf", "-.Inf", "-.INF"):
        return float("-inf")
    if s in (".nan", ".NaN", ".NAN"):
        return float("nan")
    return s


def _strip_comment(line):
    quote = None
    i = 0
    while i < len(line):
        c = line[i]
        if quote == '"':
            if c == "\\":
                i += 1
            elif c == '"':
                quote = None
        elif quote == "'":
            if c == "'":
                quote = None
        elif c in "\"'":
            prev = line[:i].rstrip()
            # A quote only opens a quoted scalar where a scalar can start; `don't` is plain text.
            if not prev or prev[-1] in ":-[{,":
                quote = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _quoted(text, pos, ln):
    q = text[pos]
    out = []
    i = pos + 1
    while i < len(text):
        c = text[i]
        if q == "'":
            if c == "'":
                if text[i + 1:i + 2] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), i + 1
            out.append(c)
        else:
            if c == '"':
                return "".join(out), i + 1
            if c == "\\":
                e = text[i + 1:i + 2]
                if e in _ESCAPES:
                    out.append(_ESCAPES[e])
                    i += 2
                    continue
                width = {"x": 2, "u": 4, "U": 8}.get(e)
                digits = text[i + 2:i + 2 + width] if width else ""
                if not width or not re.fullmatch(r"[0-9a-fA-F]{%d}" % width, digits):
                    raise YamlError(ln, "unknown escape \\%s" % e)
                out.append(chr(int(digits, 16)))
                i += 2 + width
                continue
            out.append(c)
        i += 1
    raise YamlError(ln, "unterminated quoted scalar")


def _check_indicator(text, ln):
    if text[:1] in _INDICATORS:
        raise YamlError(ln, _INDICATORS[text[0]])


def _flow(text, pos, ln):
    """A flow collection, which must close on its own line (multi-line flow is outside the subset)."""
    closing = "]" if text[pos] == "[" else "}"
    out = [] if closing == "]" else {}
    i = pos + 1
    while True:
        while i < len(text) and text[i] == " ":
            i += 1
        if i >= len(text):
            raise YamlError(ln, "flow collection is not closed on this line")
        if text[i] == closing:
            return out, i + 1
        if closing == "}":
            if text[i] in "\"'":
                key, i = _quoted(text, i, ln)
            else:
                _check_indicator(text[i:], ln)
                m = re.compile(r"[^,:{}\[\]]*").match(text, i)
                key, i = m.group(0).strip(), m.end()
            while i < len(text) and text[i] == " ":
                i += 1
            if text[i:i + 1] != ":":
                raise YamlError(ln, "expected ':' after flow key %r" % key)
            i += 1
            while i < len(text) and text[i] == " ":
                i += 1
            if i >= len(text):
                raise YamlError(ln, "flow collection is not closed on this line")
            if text[i] in ",}":
                value = None
            else:
                value, i = _flow_item(text, i, ln)
            if key in out:
                raise YamlError(ln, "duplicate key %r" % key)
            out[key] = value
        else:
            value, i = _flow_item(text, i, ln)
            out.append(value)
        while i < len(text) and text[i] == " ":
            i += 1
        if i >= len(text):
            raise YamlError(ln, "flow collection is not closed on this line")
        if text[i] == ",":
            i += 1
        elif text[i] != closing:
            raise YamlError(ln, "expected ',' or '%s' in flow collection" % closing)


def _flow_item(text, i, ln):
    c = text[i]
    if c in "[{":
        return _flow(text, i, ln)
    if c in "\"'":
        return _quoted(text, i, ln)
    _check_indicator(text[i:], ln)
    m = re.compile(r"[^,\]}]*").match(text, i)
    return _resolve(m.group(0).strip()), m.end()


def _inline(text, ln):
    c = text[0]
    if c in "[{\"'":
        value, end = (_flow if c in "[{" else _quoted)(text, 0, ln)
        if text[end:].strip():
            raise YamlError(ln, "unexpected text after the value: %r" % text[end:].strip())
        return value
    _check_indicator(text, ln)
    if ": " in text:
        raise YamlError(ln, "a plain value cannot contain ': '; quote it")
    return _resolve(text)


def _mapping_sep(text):
    """Index of the ':' that separates key and value, or None. Quoted keys may contain ':'."""
    i = 0
    if text[:1] in "\"'":
        q = text[0]
        i = 1
        while i < len(text):
            if q == '"' and text[i] == "\\":
                i += 2
                continue
            if text[i] == q:
                if q == "'" and text[i + 1:i + 2] == "'":
                    i += 2
                    continue
                break
            i += 1
        i += 1
    elif text[:1] in "[{":
        return None
    while i < len(text):
        if text[i] == ":" and (i + 1 == len(text) or text[i + 1] == " "):
            return i
        i += 1
    return None


def _is_item(body):
    return body == "-" or body.startswith("- ")


class _Block:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    def at(self, indent):
        return self.i < len(self.lines) and self.lines[self.i][1] == indent

    def deeper(self, indent):
        return self.i < len(self.lines) and self.lines[self.i][1] > indent

    def block(self, indent):
        if _is_item(self.lines[self.i][2]):
            return self.seq(indent)
        return self.mapping(indent)

    def seq(self, indent):
        out = []
        while self.at(indent) and _is_item(self.lines[self.i][2]):
            ln, _, body = self.lines[self.i]
            rest = body[1:].lstrip(" ")
            col = indent + len(body) - len(rest)
            if not rest:
                self.i += 1
                out.append(self.block(self.lines[self.i][1]) if self.deeper(indent) else None)
            elif _is_item(rest) or (rest[0] not in "[{" and _mapping_sep(rest) is not None):
                self.lines[self.i] = (ln, col, rest)
                out.append(self.block(col))
            else:
                out.append(_inline(rest, ln))
                self.i += 1
        if self.deeper(indent):
            raise YamlError(self.lines[self.i][0], "bad indentation")
        return out

    def mapping(self, indent):
        out = {}
        while self.at(indent) and not _is_item(self.lines[self.i][2]):
            ln, _, body = self.lines[self.i]
            if body == "?" or body.startswith("? "):
                raise YamlError(ln, _INDICATORS["?"])
            sep = _mapping_sep(body)
            if sep is None:
                raise YamlError(ln, "expected 'key: value'")
            raw = body[:sep].strip()
            if not raw:
                raise YamlError(ln, "empty key")
            if raw[0] in "\"'":
                key, end = _quoted(raw, 0, ln)
                if raw[end:].strip():
                    raise YamlError(ln, "unexpected text after quoted key")
            else:
                _check_indicator(raw, ln)
                key = raw
            if key in out:
                raise YamlError(ln, "duplicate key %r" % key)
            rest = body[sep + 1:].strip()
            self.i += 1
            if rest:
                out[key] = _inline(rest, ln)
            elif self.deeper(indent):
                out[key] = self.block(self.lines[self.i][1])
            elif self.at(indent) and _is_item(self.lines[self.i][2]):
                out[key] = self.seq(indent)
            else:
                out[key] = None
        if self.deeper(indent):
            raise YamlError(self.lines[self.i][0], "bad indentation")
        return out


def parse_yaml(text):
    """Parse the YAML subset in CONTRACTS.md; anything outside it raises YamlError naming the line."""
    lines = []
    started = False
    for ln, raw in enumerate(text.split("\n"), 1):
        raw = raw.rstrip("\r")
        if not raw.strip():
            continue
        lead = raw[:len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in lead:
            raise YamlError(ln, "tab in indentation")
        line = _strip_comment(raw)
        body = line.strip()
        if not body:
            continue
        if body in ("---", "..."):
            if lines or started or body == "...":
                raise YamlError(ln, "multiple documents are outside the subset")
            started = True
            continue
        if body.startswith("%"):
            raise YamlError(ln, "directives are outside the subset")
        lines.append((ln, len(line) - len(line.lstrip(" ")), body))
    if not lines:
        return None
    p = _Block(lines)
    value = p.block(lines[0][1])
    if p.i < len(lines):
        raise YamlError(lines[p.i][0], "bad indentation")
    return value

# ---------------------------------------------------------------- JSON Schema subset

class SchemaUnsupported(Exception):
    pass


_ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "definitions", "examples"}
_KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "minItems", "enum",
             "pattern", "minimum", "minLength", "format", "$ref"}
_DATE_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})")


def _is_type(value, t):
    # bool is a subclass of int in Python, so `true` would otherwise pass as an integer.
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "null":
        return value is None
    return isinstance(value, {"string": str, "boolean": bool, "object": dict, "array": list}[t])


def _same(a, b):
    return type(a) is type(b) and a == b or (a is None and b is None)


def _validate(schema, value, path, root, out):
    unknown = set(schema) - _KEYWORDS - _ANNOTATIONS
    if unknown:
        raise SchemaUnsupported("schema keyword(s) not implemented: %s" % ", ".join(sorted(unknown)))
    where = path or "(root)"
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return _validate(root["definitions"][name], value, path, root, out)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, t) for t in types):
            out.append("%s: must be %s" % (where, " or ".join(types)))
            return
    if "enum" in schema and not any(_same(value, e) for e in schema["enum"]):
        out.append("%s: must be one of %s" % (where, ", ".join(json.dumps(e) for e in schema["enum"])))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append("%s: must not be empty" % where)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append("%s: must match %s" % (where, schema["pattern"]))
        if schema.get("format") == "date-time" and not _DATE_TIME.fullmatch(value):
            out.append("%s: must be an ISO 8601 date-time" % where)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append("%s: must be >= %s" % (where, schema["minimum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append("%s: must have required property '%s'" % (where, key))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                _validate(sub, value[key], "%s/%s" % (path, key) if path else key, root, out)
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    out.append("%s: unknown property '%s'" % (where, key))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append("%s: must have at least %d item(s)" % (where, schema["minItems"]))
        if "items" in schema:
            for n, item in enumerate(value):
                _validate(schema["items"], item, "%s/%d" % (path, n) if path else str(n), root, out)


def schema_errors(name, value):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        schema = json.load(f)
    out = []
    _validate(schema, value, "", schema, out)
    return [("error", m) for m in out]

# ---------------------------------------------------------------- C1 criteria

PROFILES = ("rspec", "sdlc-s", "sdlc-m", "sdlc-l")
REVERSE_TAGS = ("docs", "api", "observed", "code", "3p", "inferred")
FORWARD_TAGS = ("request", "decision", "inferred")
SPEC_ID = re.compile(r"(F-[A-Z][A-Z0-9]*-[0-9]+)\.AC([0-9]+)")
STANDALONE_ID = re.compile(r"AC-([0-9]{3,})")
CRIT_LINE = re.compile(r"^\s*[-*] (?:\[[ xX]\] )?(?P<body>(?:~~)?\*\*.*)$")
ACTIVE = re.compile(r"\*\*(?P<id>[^*]+)\*\*\s*(?P<rest>.*)$")
REMOVED = re.compile(r"~~\*\*(?P<id>[^*]+)\*\*.*?~~\s*(?P<reason>.*)$")
TAG = re.compile(r"`\[([^\]`]*)\]`")
GRAMMAR = re.compile(r"Given .+?, when .+?, then (?P<then>.+)\.")


def check_id(cid, profile="rspec"):
    """C1 ID rule: `<FEATURE-ID>.AC<n>` (spec-backed) or `AC-<nnn>` (standalone sdlc), n from 1."""
    m = SPEC_ID.fullmatch(cid)
    if m:
        return [] if int(m.group(2)) else [("error", "%s: ACs are numbered from 1" % cid)]
    m = STANDALONE_ID.fullmatch(cid)
    if m:
        if profile == "rspec":
            return [("error", "%s: rspec needs spec-backed IDs (<FEATURE-ID>.AC<n>)" % cid)]
        return [] if int(m.group(1)) else [("error", "%s: ACs are numbered from 1" % cid)]
    return [("error", "%s: not a criterion ID (<FEATURE-ID>.AC<n>, or AC-<nnn> standalone)" % cid)]


def _section(text, title, level=None):
    """(line number, line) pairs under the heading `title`; the whole file when there is no such heading."""
    lines = text.split("\n")
    for n, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m and m.group(2).lower() == title.lower() and (level is None or len(m.group(1)) == level):
            out = []
            for k in range(n + 1, len(lines)):
                h = re.match(r"^(#{1,6})\s", lines[k])
                if h and len(h.group(1)) <= len(m.group(1)):
                    break
                out.append((k + 1, lines[k].rstrip("\r")))
            return out
    return None if level else [(n + 1, l.rstrip("\r")) for n, l in enumerate(lines)]


def criterion_text_sha256(line):
    """C3 `text_sha256`: SHA-256 of the line after `**ID**`, stripped; the checkbox state is not part of it."""
    m = CRIT_LINE.match(line)
    a = ACTIVE.match(m.group("body")) if m else None
    if not a:
        raise ValueError("not a criterion line: %r" % line)
    return hashlib.sha256(a.group("rest").strip().encode("utf-8")).hexdigest()


def _domain_states(domain):
    return set(re.findall(r"`([^`\[\]]+)`", domain or ""))


def check_criteria(text, profile="rspec", domain=None):
    """C1 for every criterion line under `Acceptance criteria` (or the whole file without that heading)."""
    if profile not in PROFILES:
        raise ValueError("profile must be one of %s" % ", ".join(PROFILES))
    strict = "error" if profile in ("rspec", "sdlc-l") else "warning"
    issues, seen = [], set()
    lines = [(ln, line) for ln, line in _section(text, "Acceptance criteria") if CRIT_LINE.match(line)]
    if not lines:
        return [("error", "no criterion line found (- [ ] **<ID>** Given …); nothing was checked")]
    for ln, line in lines:
        m = CRIT_LINE.match(line)
        body = m.group("body")
        at = "line %d: " % ln
        if body.startswith("~~"):
            r = REMOVED.match(body)
            if not r:
                issues.append(("error", at + "removed criterion must read ~~**ID** text~~ <reason>"))
                continue
            cid = r.group("id")
            if not r.group("reason").strip():
                issues.append(("error", at + "%s: removed criterion needs a reason after the strikethrough" % cid))
        else:
            a = ACTIVE.match(body)
            if not a:
                issues.append(("error", at + "criterion ID must be **bold**: - [ ] **<ID>** Given …"))
                continue
            cid = a.group("id")
        issues += [(s, at + msg) for s, msg in check_id(cid, profile)]
        if cid in seen:
            issues.append(("error", at + "%s: duplicate ID" % cid))
        seen.add(cid)
        if body.startswith("~~"):
            continue
        at += cid + ": "
        rest = a.group("rest")
        tags = TAG.findall(rest)
        sentence = TAG.sub("", rest).strip()
        g = GRAMMAR.fullmatch(sentence)
        if not g:
            issues.append(("error", at + "grammar: must read Given …, when …, then …. (keywords in English)"))
        elif ", then " in g.group("then"):
            issues.append(("error", at + "one observable behaviour per criterion: more than one then clause"))
        allowed = REVERSE_TAGS if SPEC_ID.fullmatch(cid) else FORWARD_TAGS
        sources, manual = [], None
        for t in tags:
            if t == "manual" or t.startswith("manual:"):
                manual = t[len("manual:"):].strip() if ":" in t else ""
            elif t in REVERSE_TAGS or t in FORWARD_TAGS:
                if t in allowed:
                    sources.append(t)
                else:
                    issues.append(("error", at + "tag [%s] is not allowed here (allowed: %s)" % (t, ", ".join(allowed))))
            else:
                issues.append(("error", at + "unknown tag [%s]" % t))
        if not sources:
            issues.append(("error", at + "no source tag (one of %s)" % ", ".join(allowed)))
        elif len(sources) > 1:
            issues.append(("error", at + "exactly one source tag, found %d" % len(sources)))
        if manual == "":
            issues.append(("error", at + "[manual] needs a reason: `[manual: <reason>]`"))
        if g and manual is None:
            then = g.group("then")
            spans = re.findall(r"`([^`\[\]]+)`", then)
            if domain is not None:
                states = _domain_states(domain)
                for s in spans:
                    if s not in states:
                        issues.append((strict, at + "example data: `%s` is not a state in domain.md" % s))
                spans = [s for s in spans if s in states]
            if not (re.search(r'"[^"]+"', then) or re.search(r"[0-9]", then) or spans):
                issues.append((strict, at + "example data: the then clause has no literal a test can assert "
                                            "(quoted string, number, identifier, or a `state` from domain.md)"))
    return issues

# ---------------------------------------------------------------- C2 story

STORY_SECTIONS = ("Story", "Acceptance criteria", "Failure modes", "Must never break",
                  "Differences from the original", "Sources")


def _items(lines):
    return [(ln, m.group(1).strip()) for ln, l in lines for m in [re.match(r"^\s*[-*] (.*)$", l)] if m]


def check_story(text):
    """C2: the six sections, no Edge cases, and the arrows that tie failure modes and differences to IDs."""
    issues = []
    sections = {}
    for title in STORY_SECTIONS + ("Edge cases",):
        sections[title] = _section(text, title, level=2)
    if sections["Edge cases"] is not None:
        issues.append(("error", "Edge cases section is removed in v1: make each edge case a criterion or a failure mode"))
    for title in STORY_SECTIONS:
        if sections[title] is None:
            issues.append(("error", "missing section: %s" % title))
        elif title in ("Story", "Sources") and not any(l.strip() for _, l in sections[title]):
            issues.append(("error", "section %s is empty" % title))
    if sections["Acceptance criteria"] is not None:
        crit = "\n".join(l for _, l in sections["Acceptance criteria"])
        found = check_criteria("## Acceptance criteria\n" + crit, "rspec")
        issues +=[(s, "Acceptance criteria: " + m) for s, m in found]
    ids = {m.group("id") for _, l in sections["Acceptance criteria"] or []
           for c in [CRIT_LINE.match(l)] if c
           for m in [ACTIVE.match(c.group("body")) or REMOVED.match(c.group("body"))] if m}
    mnb = set()
    for ln, item in _items(sections["Must never break"] or []):
        if item.lower() == "none":
            continue
        m = re.search(r"\bMNB-[0-9]+\b", item)
        if not m:
            issues.append(("error", "line %d: Must never break line needs an MNB-<n> ID" % ln))
            continue
        mnb.add(m.group(0))
        if not re.search(r"(?i)\b(test|check):", item):
            issues.append(("error", "line %d: %s names no test or check (test: … or check: …)" % (ln, m.group(0))))
    for ln, item in _items(sections["Failure modes"] or []):
        if item.lower() == "none":
            continue
        m = re.search(r"→\s*(\S+)\s*$", item)
        if not m or not (SPEC_ID.fullmatch(m.group(1)) or re.fullmatch(r"MNB-[0-9]+", m.group(1))):
            issues.append(("error", "line %d: failure mode must end with → <criterion ID> or → MNB-<n>" % ln))
        elif m.group(1) not in ids | mnb:
            issues.append(("error", "line %d: failure mode points to unknown ID %s" % (ln, m.group(1))))
    for ln, item in _items(sections["Differences from the original"] or []):
        if item.lower() != "none" and not re.search(r"→\s*D-[0-9]{3,}\s*$", item):
            issues.append(("error", "line %d: difference must end with → D-<nnn>" % ln))
    return issues

# ---------------------------------------------------------------- C3 lock

def check_lock(lock, root=None):
    """C3 schema and rules; with `root` (the repo), each text_sha256 is compared with the spec's text."""
    issues = schema_errors("criteria-lock.schema.json", lock)
    if issues:
        return issues
    seen = set()
    for c in lock["criteria"]:
        cid = c["id"]
        issues += check_id(cid, "sdlc-l")
        if cid in seen:
            issues.append(("error", "%s: duplicate ID" % cid))
        seen.add(cid)
        if SPEC_ID.fullmatch(cid) and not cid.startswith(c["feature"] + ".AC"):
            issues.append(("error", "%s: id is not under feature %s" % (cid, c["feature"])))
        if c["level"] == 2 and not c["test"]:
            issues.append(("error", "%s: level 2 needs a test (a recorded test passed against the reference)" % cid))
        if c["level"] == 1 and c["tag"] == "inferred":
            issues.append(("error", "%s: an [inferred] criterion never reaches level 1 by audit; it needs a source "
                                    "tag first (C3)" % cid))
    if root is None:
        issues.append(("error", "not run: text_sha256 check (pass --root <repo>)"))
        return issues
    for c in lock["criteria"]:
        path = os.path.join(root, lock["spec"], c["file"])
        if not os.path.isfile(path):
            issues.append(("error", "%s: %s not found under %s" % (c["id"], c["file"], lock["spec"])))
            continue
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        hit = [l for l in lines for m in [CRIT_LINE.match(l)] if m
               for a in [ACTIVE.match(m.group("body"))] if a and a.group("id") == c["id"]]
        if not hit:
            issues.append(("error", "%s: not found in %s" % (c["id"], c["file"])))
        elif criterion_text_sha256(hit[0].rstrip("\r")) != c["text_sha256"]:
            issues.append(("warning", "%s: text changed since the lock (text_sha256 mismatch); "
                                      "level drops to 0 until re-verified" % c["id"]))
    return issues

# ---------------------------------------------------------------- C4 acceptance bundle

RUNNER_DIRS = {"http": ("http/", ".yaml"), "playwright": ("e2e/", ".spec.ts"), "maestro": ("mobile/", ".yaml"),
               "cli": ("cli/", ".yaml")}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
URL = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://")
SECRET = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{6,}|"
                    r"\b(authorization|cookie|password|passwd|api[_-]?key|secret)\b[\"']?\s*[:=]")


def _rule_problem(rule, captures):
    if rule in ("uuid", "int", "iso8601"):
        return None
    if rule.startswith("same-as:"):
        return None if rule[8:] in captures else "rule %s refers to no earlier capture" % rule
    if rule.startswith("regex:"):
        try:
            re.compile(rule[6:])
            return None
        except re.error as e:
            return "rule %s is not a valid regex (%s)" % (rule, e)
    return "unknown rule %s (uuid, int, iso8601, same-as:<capture>, regex:<pattern>)" % rule


def _check_steps(steps, where):
    if not isinstance(steps, list) or not steps:
        return [("error", "%s: steps must be a non-empty list" % where)]
    issues, captures = [], set()
    for n, step in enumerate(steps, 1):
        at = "%s step %d" % (where, n)
        if not isinstance(step, dict) or not isinstance(step.get("request"), dict) or not isinstance(step.get("expect"), dict):
            issues.append(("error", "%s: needs request and expect mappings" % at))
            continue
        req, exp = step["request"], step["expect"]
        if req.get("method") not in METHODS:
            issues.append(("error", "%s: method must be one of %s" % (at, ", ".join(METHODS))))
        path = req.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(("error", "%s: path must start with / (the host comes from ACCEPT_BASE_URL)" % at))
        else:
            for name in re.findall(r"\{([^}]*)\}", path):
                if name not in captures:
                    issues.append(("error", "%s: path uses {%s} before it is captured" % (at, name)))
        if "account" in req and not (isinstance(req["account"], str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", req["account"])):
            issues.append(("error", "%s: account must be an upper-case name (ACCEPT_ACCOUNT_<NAME>)" % at))
        if not (isinstance(exp.get("status"), int) and not isinstance(exp.get("status"), bool)):
            issues.append(("error", "%s: expect.status must be an integer" % at))
        if not isinstance(exp.get("json", []), list):
            issues.append(("error", "%s: expect.json must be a list of checks" % at))
            continue
        for k, chk in enumerate(exp.get("json") or [], 1):
            cat = "%s check %d" % (at, k)
            if not isinstance(chk, dict) or not isinstance(chk.get("pointer"), str) or \
                    not (chk["pointer"] == "" or chk["pointer"].startswith("/")):
                issues.append(("error", "%s: needs a JSON pointer (/…)" % cat))
                continue
            if not any(k2 in chk for k2 in ("equals", "rule", "capture")):
                issues.append(("error", "%s: needs equals, rule or capture" % cat))
            if "rule" in chk:
                problem = _rule_problem(str(chk["rule"]), captures)
                if problem:
                    issues.append(("error", "%s: %s" % (cat, problem)))
            if "capture" in chk:
                if not (isinstance(chk["capture"], str) and NAME.fullmatch(chk["capture"])):
                    issues.append(("error", "%s: capture must be a name" % cat))
                else:
                    captures.add(chk["capture"])
    return issues


def check_http_test(data, where, criterion=None, root=None):
    """C4 HTTP replay format. `criterion`: the ID its file name says; `root`: the bundle, to find seeds."""
    if not isinstance(data, dict):
        return [("error", "%s: must be a mapping" % where)]
    issues = []
    cid = data.get("criterion")
    if not isinstance(cid, str) or (not SPEC_ID.fullmatch(cid) and not STANDALONE_ID.fullmatch(cid)):
        issues.append(("error", "%s: criterion must be a criterion ID" % where))
    elif criterion and cid != criterion:
        issues.append(("error", "%s: criterion %s does not match its file name %s" % (where, cid, criterion)))
    seeds = data.get("seed", [])
    if not isinstance(seeds, list) or not all(isinstance(s, str) for s in seeds):
        issues.append(("error", "%s: seed must be a list of paths" % where))
    elif root is not None:
        for s in seeds:
            if not _inside(s):
                issues.append(("error", "%s: seed %s is outside the bundle" % (where, s)))
                continue
            path = os.path.join(root, s)
            if not os.path.isfile(path):
                issues.append(("error", "%s: seed %s not found" % (where, s)))
                continue
            try:
                seed = parse_yaml(_read(path))
            except YamlError as e:
                issues.append(("error", "%s: %s" % (s, e)))
                continue
            issues += _check_steps(seed.get("steps") if isinstance(seed, dict) else None, s)
    issues += _check_steps(data.get("steps"), where)
    return issues


def _read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def _inside(rel):
    """A bundle path may not climb out of the bundle: what it names would escape the URL and secret scan."""
    # `C:x.yaml` is drive-relative on Windows and escapes the bundle; rejected on every OS so verdicts match.
    norm = os.path.normpath(rel).replace(os.sep, "/")
    return not (os.path.isabs(rel) or rel.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", rel)
                or norm == ".." or norm.startswith("../"))


def _sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_bundle(root):
    """C4: manifest entries, file hashes, runner folders, HTTP replay files, and no URL or secret anywhere."""
    mpath = os.path.join(root, "manifest.json")
    if not os.path.isfile(mpath):
        return [("error", "manifest.json not found in %s" % root)]
    try:
        manifest = json.loads(_read(mpath))
    except ValueError as e:
        return [("error", "manifest.json: not JSON (%s)" % e)]
    issues = schema_errors("acceptance-manifest.schema.json", manifest)
    if issues:
        return issues
    for t in manifest["tests"]:
        cid, rel = t["criterion"], t["path"]
        folder, ext = RUNNER_DIRS[t["runner"]]
        if not _inside(rel):
            issues.append(("error", "%s: path %s is outside the bundle" % (cid, rel)))
            continue
        if not rel.startswith(folder) or not rel.endswith(ext):
            issues.append(("error", "%s: path %s is not %s*%s (runner %s)" % (cid, rel, folder, ext, t["runner"])))
            continue
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            issues.append(("error", "%s: %s not found" % (cid, rel)))
            continue
        if _sha_file(path) != t["sha256"]:
            issues.append(("error", "%s: sha256 does not match %s" % (cid, rel)))
        if t["level"] == "unit":
            issues.append(("warning", "%s: a then clause seen by a user or API client needs integration or e2e, "
                                      "not unit (runner %s)" % (cid, t["runner"])))
        if t["runner"] == "http":
            try:
                data = parse_yaml(_read(path))
            except YamlError as e:
                issues.append(("error", "%s: %s" % (rel, e)))
                continue
            issues += check_http_test(data, rel, os.path.basename(rel)[:-len(ext)], root)
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            # Not UTF-8 is still scanned: skipping it would let a URL through unchecked.
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", errors="replace")
            for ln, line in enumerate(text.split("\n"), 1):
                if URL.search(line):
                    issues.append(("error", "URL in %s line %d: targets come only from ACCEPT_BASE_URL" % (rel, ln)))
                if SECRET.search(line):
                    issues.append(("error", "secret in %s line %d: accounts come only from ACCEPT_ACCOUNT_<NAME>"
                                   % (rel, ln)))
    return issues

# ---------------------------------------------------------------- C4 run-http

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?")


class _Fail(Exception):
    pass


def _pointer(doc, pointer):
    cur = doc
    if pointer == "":
        return cur
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise KeyError(pointer)
    return cur


def _rule_ok(rule, value, captures):
    if rule == "uuid":
        return isinstance(value, str) and bool(UUID_RE.fullmatch(value))
    if rule == "int":
        return (isinstance(value, int) and not isinstance(value, bool)) or \
            (isinstance(value, str) and value.isdigit())
    if rule == "iso8601":
        return isinstance(value, str) and bool(ISO_RE.fullmatch(value))
    if rule.startswith("same-as:"):
        return _same(value, captures.get(rule[8:]))
    if rule.startswith("regex:"):
        return isinstance(value, (str, int)) and not isinstance(value, bool) and bool(re.search(rule[6:], str(value)))
    return False


def _run_steps(steps, label, base, env):
    captures = {}
    for n, step in enumerate(steps, 1):
        at = "%s step %d" % (label, n)
        req, exp = step["request"], step["expect"]
        path = re.sub(r"\{([^}]*)\}", lambda m: urllib.parse.quote(str(captures[m.group(1)]), safe=""), req["path"])
        headers = {"Accept": "application/json"}
        if "account" in req:
            var = "ACCEPT_ACCOUNT_" + req["account"]
            if var not in env:
                raise _Fail("not run: %s is not set" % var)
            name, sep, value = env[var].partition(":")
            if not sep or not name.strip():
                raise _Fail("%s must be a header line 'Name: value'" % var)
            headers[name.strip()] = value.strip()
        data = None
        if "json" in req:
            data = json.dumps(req["json"]).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            request = urllib.request.Request(base.rstrip("/") + path, data=data, headers=headers,
                                             method=req["method"])
            with urllib.request.urlopen(request, timeout=30) as resp:
                status, body = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
        # ValueError: a base URL with no scheme; HTTPException: a listener that does not speak HTTP.
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
            raise _Fail("%s: request failed: %s" % (at, e))
        if status != exp["status"]:
            raise _Fail("%s: status %d, expected %d" % (at, status, exp["status"]))
        checks = exp.get("json") or []
        if not checks:
            continue
        try:
            doc = json.loads(body.decode("utf-8"))
        except ValueError:
            raise _Fail("%s: response is not JSON" % at)
        for chk in checks:
            ptr = chk["pointer"]
            try:
                value = _pointer(doc, ptr)
            except KeyError:
                raise _Fail("%s %s: not present in the response" % (at, ptr))
            if "equals" in chk and not _same(value, chk["equals"]):
                raise _Fail("%s %s: got %s, expected %s" % (at, ptr, json.dumps(value), json.dumps(chk["equals"])))
            if "rule" in chk and not _rule_ok(str(chk["rule"]), value, captures):
                raise _Fail("%s %s: %s does not satisfy rule %s" % (at, ptr, json.dumps(value), chk["rule"]))
            if "capture" in chk:
                captures[chk["capture"]] = value


def run_http(paths, env=None):
    """Run HTTP replay tests against ACCEPT_BASE_URL. Returns (JUnit XML, number failed)."""
    env = os.environ if env is None else env
    cases = []
    for path in paths:
        name = os.path.basename(path)[:-5] if path.endswith(".yaml") else os.path.basename(path)
        root = os.path.dirname(os.path.dirname(os.path.abspath(path)))
        failure, data = None, None
        try:
            data = parse_yaml(_read(path))
            problems = [m for s, m in check_http_test(data, os.path.basename(path), None, root) if s == "error"]
            if problems:
                raise _Fail("invalid test: " + "; ".join(problems))
            base = env.get("ACCEPT_BASE_URL")
            if not base:
                raise _Fail("not run: ACCEPT_BASE_URL is not set")
            for s in data.get("seed", []):
                _run_steps(parse_yaml(_read(os.path.join(root, s)))["steps"], "seed " + s, base, env)
            _run_steps(data["steps"], name, base, env)
        except (_Fail, YamlError, OSError) as e:
            failure = str(e)
        cases.append((data.get("criterion", name) if isinstance(data, dict) else name, failure))
    failed = sum(1 for _, f in cases if f)
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<testsuite name="contracts.run-http" tests="%d" failures="%d">' % (len(cases), failed)]
    for name, failure in cases:
        if failure:
            out.append('  <testcase classname="http" name=%s><failure message=%s>%s</failure></testcase>'
                       % (quoteattr(name), quoteattr(failure), escape(failure)))
        else:
            out.append('  <testcase classname="http" name=%s/>' % quoteattr(name))
    out.append("</testsuite>")
    return "\n".join(out) + "\n", failed

# ---------------------------------------------------------------- C5 departures

def check_departures(data):
    """C5: fields, unique IDs, decided_by required; a `status: proposed` entry blocks the gate that reads it."""
    issues = schema_errors("departures.schema.json", data)
    if issues:
        return issues
    seen = set()
    for d in data:
        did = d["id"]
        if did in seen:
            issues.append(("error", "duplicate id %s" % did))
        seen.add(did)
        for cid in d.get("criteria", []):
            issues += [(s, "%s: %s" % (did, m)) for s, m in check_id(cid, "rspec")]
        for k, m in enumerate(d.get("match") or [], 1):
            problem = _rule_problem(m["rule"], set())
            if problem:
                issues.append(("error", "%s match %d: %s" % (did, k, problem)))
        if d.get("status") == "proposed":
            if d.get("decided_by"):
                issues.append(("error", "%s: a proposed departure has no decided_by; drop one of them" % did))
            else:
                issues.append(("blocked", "%s is proposed: it blocks the gate that reads it until a human decides "
                                          "it (decided_by)" % did))
        elif not d.get("decided_by"):
            issues.append(("error", "%s: decided_by is required (a departure nobody decided is invalid)" % did))
    return issues

# ---------------------------------------------------------------- C6 findings

ROUTES = {"build-defect": "sdlc", "test-defect": "sdlc", "spec-gap": "rspec", "reference-defect": "human",
          "accepted-departure": "drop", "flaky": "orchestrator", "environment": "orchestrator"}


# A spec question (sdlc S10) reports an ambiguity, not a behaviour: nothing to re-run, so C6 lets exactly this
# shape through without a verifier. Every other finding still needs `reproduced`.
QUESTION_SOURCE = "sdlc-question"
QUESTION_VERIFIED_BY = {"agent": None, "result": "not run: spec question"}


def _is_spec_question(f):
    return (f.get("source") == QUESTION_SOURCE and f.get("class") == "spec-gap" and f.get("question")
            and f.get("verified_by") == QUESTION_VERIFIED_BY)


def check_finding(f):
    """C6: fields, `route` derived from `class`, and the spec-question exception."""
    issues = schema_errors("finding.schema.json", f)
    if issues:
        return issues
    fid = f["id"]
    if f["criterion"] is not None:
        issues += [(s, "%s: %s" % (fid, m)) for s, m in check_id(f["criterion"], "sdlc-m")]
    want = ROUTES[f["class"]]
    if f["route"] != want:
        issues.append(("error", "%s: route must be %s for class %s (got %s)" % (fid, want, f["class"], f["route"])))
    if f["source"] == QUESTION_SOURCE:
        if f["class"] != "spec-gap":
            issues.append(("error", "%s: a %s finding must be class spec-gap" % (fid, QUESTION_SOURCE)))
        if not f.get("question"):
            issues.append(("error", "%s: a %s finding needs question" % (fid, QUESTION_SOURCE)))
        if f["verified_by"] != QUESTION_VERIFIED_BY:
            issues.append(("error", '%s: a %s finding has verified_by {agent: null, result: "not run: spec question"}'
                           % (fid, QUESTION_SOURCE)))
    else:
        for key in ("repro", "observed"):
            if f[key] is None:
                issues.append(("error", "%s: %s is required (only a spec question may leave it null)" % (fid, key)))
        if f["verified_by"]["agent"] is None:
            issues.append(("error", "%s: verified_by.agent is required (only a spec question has none)" % fid))
    if f["repro"] is not None and f["repro"]["runner"] == "http":
        issues += _check_steps(f["repro"].get("steps"), "%s repro" % fid)
    return issues


def finding_route(f):
    """Where a valid finding goes, or None: only a reproduced finding, or a spec question, is routed."""
    if _is_spec_question(f):
        return ROUTES["spec-gap"]
    if f.get("verified_by", {}).get("result") != "reproduced" or not f["verified_by"].get("agent"):
        return None
    return ROUTES[f["class"]]

# ---------------------------------------------------------------- C7 cost

def _cost_lines(text):
    for ln, line in enumerate(text.split("\n"), 1):
        if line.strip():
            yield ln, line


def check_cost(text):
    issues = []
    for ln, line in _cost_lines(text):
        try:
            row = json.loads(line)
        except ValueError as e:
            issues.append(("error", "line %d: not JSON (%s)" % (ln, e)))
            continue
        issues += [(s, "line %d: %s" % (ln, m)) for s, m in schema_errors("cost-line.schema.json", row)]
    return issues


def sum_cost(text):
    """Totals per stage. Tokens a host did not report are not guessed: they are counted in tokens_unreported."""
    out = {}
    for _, line in _cost_lines(text):
        row = json.loads(line)
        s = out.setdefault(row["stage"], {"runs": 0, "wall_s": 0, "turns": 0, "tokens_in": 0, "tokens_out": 0,
                                          "tokens_unreported": 0})
        s["runs"] += 1
        s["wall_s"] += row["wall_s"]
        s["turns"] += row["turns"]
        if row["tokens_in"] is None or row["tokens_out"] is None:
            s["tokens_unreported"] += 1
        s["tokens_in"] += row["tokens_in"] or 0
        s["tokens_out"] += row["tokens_out"] or 0
    return out

# ---------------------------------------------------------------- distribution

def header_for(rel):
    """The contracts-version header a file must open with, None for fixtures. The one place the rule lives."""
    if rel.startswith("fixtures/"):
        return None
    if rel.endswith(".schema.json"):
        return ('"$comment"', "contracts-version: %s" % VERSION)
    if rel.endswith((".py", ".yaml", ".yml")):
        return "# contracts-version: %s" % VERSION
    if rel.endswith(".md"):
        return "<!-- contracts-version: %s -->" % VERSION
    return "unknown"


def _files(folder):
    out = []
    for dirpath, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in files:
            rel = os.path.relpath(os.path.join(dirpath, name), folder).replace(os.sep, "/")
            if rel != "MANIFEST" and not name.endswith(".pyc"):
                out.append(rel)
    return sorted(out)


def seal(folder):
    """Rewrite MANIFEST from the files on disk. Canonical repo only: a consumer never seals its copy."""
    lines = ["contracts-version: %s" % VERSION] + ["%s  %s" % (_sha_file(os.path.join(folder, r)), r)
                                                   for r in _files(folder)]
    with open(os.path.join(folder, "MANIFEST"), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))


def _header_issue(folder, rel):
    want = header_for(rel)
    if want is None:
        return None
    if want == "unknown":
        return "header: no header rule for %s" % rel
    data = _read(os.path.join(folder, rel))
    if isinstance(want, tuple):
        try:
            pairs = json.loads(data, object_pairs_hook=lambda p: p)
        except ValueError as e:
            return "header: %s is not JSON (%s)" % (rel, e)
        if not pairs or pairs[0] != ("$comment", want[1]):
            return 'header: %s must have "$comment": "%s" as its first key' % (rel, want[1])
        return None
    if data.split("\n", 1)[0].rstrip("\r") != want:
        return "header: %s must start with %s" % (rel, want)
    return None


def vendor_check(folder):
    """Drift check: MANIFEST hashes, the file list, every header, and every fixture's verdict."""
    mpath = os.path.join(folder, "MANIFEST")
    if not os.path.isfile(mpath):
        return [("error", "MANIFEST not found in %s" % folder)]
    lines = _read(mpath).split("\n")
    issues = []
    if lines[0] != "contracts-version: %s" % VERSION:
        issues.append(("error", "MANIFEST line 1 is %r; it must be 'contracts-version: %s' (the version of "
                                "contracts.py)" % (lines[0], VERSION)))
    listed = {}
    for n, line in enumerate(lines[1:], 2):
        if not line:
            continue
        m = re.fullmatch(r"([0-9a-f]{64})  (\S.*)", line)
        if not m:
            issues.append(("error", "MANIFEST line %d is not '<sha256>  <path>'" % n))
        else:
            listed[m.group(2)] = m.group(1)
    actual = _files(folder)
    for rel in sorted(set(listed) - set(actual)):
        issues.append(("error", "missing: %s (listed in MANIFEST)" % rel))
    for rel in actual:
        if rel not in listed:
            issues.append(("error", "not in MANIFEST: %s" % rel))
            continue
        if _sha_file(os.path.join(folder, rel)) != listed[rel]:
            issues.append(("error", "changed: %s (sha256 differs from MANIFEST)" % rel))
        problem = _header_issue(folder, rel)
        if problem:
            issues.append(("error", problem))
    try:
        for rel, valid, found in run_fixtures(os.path.join(folder, "fixtures")):
            bad = [m for s, m in found if s != "warning"]
            if valid and bad:
                issues.append(("error", "fixture %s should pass: %s" % (rel, bad[0])))
            elif not valid and not bad:
                issues.append(("error", "fixture %s should fail but passed" % rel))
    except (OSError, ValueError, KeyError, SchemaUnsupported) as e:
        issues.append(("error", "not run: fixtures (%s)" % e))
    return issues


def _fixture_issues(kind, path):
    name = os.path.basename(path)
    try:
        if kind == "criteria":
            profile = name.split("--")[0] if "--" in name else "rspec"
            return check_criteria(_read(path), profile)
        if kind == "story":
            return check_story(_read(path))
        if kind == "lock":
            if os.path.isdir(path):
                return check_lock(json.loads(_read(os.path.join(path, "criteria.lock.json"))), path)
            return check_lock(json.loads(_read(path)), None)
        if kind == "bundle":
            return check_bundle(path)
        if kind == "http":
            return check_http_test(parse_yaml(_read(path)), name)
        if kind == "departures":
            return check_departures(parse_yaml(_read(path)))
        if kind == "finding":
            return check_finding(json.loads(_read(path)))
        if kind == "cost":
            return check_cost(_read(path))
        if kind == "yaml":
            parse_yaml(_read(path))
            return []
    except (YamlError, ValueError) as e:
        return [("error", str(e))]
    raise ValueError("unknown fixture kind %s" % kind)


def run_fixtures(fixtures):
    """fixtures/<kind>/valid/* must have no error; fixtures/<kind>/invalid/* must have one."""
    out = []
    for kind in sorted(os.listdir(fixtures)):
        for verdict in ("valid", "invalid"):
            folder = os.path.join(fixtures, kind, verdict)
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                out.append(("%s/%s/%s" % (kind, verdict, name), verdict == "valid",
                            _fixture_issues(kind, os.path.join(folder, name))))
    return out

# ---------------------------------------------------------------- CLI

def _report(issues):
    for sev, msg in issues:
        print("%s: %s" % (sev, msg))
    return 1 if any(s != "warning" for s, _ in issues) else 0


def _console_safe():
    # A Windows console in cp1252 can't encode the →, … and — in our messages (or in a path or ID),
    # and print() raised UnicodeEncodeError, which main() then reported as an error with exit 1.
    # errors="replace" prints "?" instead; a UTF-8 console is
    # unaffected. A stream without reconfigure (StringIO, an embedding caller's) already takes any str.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def main(argv=None):
    _console_safe()
    ap = argparse.ArgumentParser(prog="contracts.py", description="Shared contracts v%s validators" % VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("id")
    p.add_argument("ids", nargs="+")
    p.add_argument("--profile", choices=PROFILES, default="rspec")
    p = sub.add_parser("criteria")
    p.add_argument("file")
    p.add_argument("--profile", choices=PROFILES, default="rspec")
    p.add_argument("--domain")
    sub.add_parser("story").add_argument("file")
    p = sub.add_parser("lock")
    p.add_argument("file")
    p.add_argument("--root", default=".", help="the repo the lock's spec path is relative to (default: cwd)")
    sub.add_parser("bundle").add_argument("dir")
    sub.add_parser("run-http").add_argument("files", nargs="+")
    sub.add_parser("departures").add_argument("file")
    sub.add_parser("finding").add_argument("files", nargs="+")
    sub.add_parser("cost").add_argument("file")
    sub.add_parser("vendor-check").add_argument("dir")
    sub.add_parser("seal").add_argument("dir")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "id":
            return _report([i for cid in a.ids for i in check_id(cid, a.profile)])
        if a.cmd == "criteria":
            return _report(check_criteria(_read(a.file), a.profile, _read(a.domain) if a.domain else None))
        if a.cmd == "story":
            return _report(check_story(_read(a.file)))
        if a.cmd == "lock":
            return _report(check_lock(json.loads(_read(a.file)), a.root))
        if a.cmd == "bundle":
            return _report(check_bundle(a.dir))
        if a.cmd == "run-http":
            xml, failed = run_http(a.files)
            sys.stdout.write(xml)
            return 1 if failed else 0
        if a.cmd == "departures":
            return _report(check_departures(parse_yaml(_read(a.file))))
        if a.cmd == "finding":
            code = 0
            for path in a.files:
                f = json.loads(_read(path))
                issues = check_finding(f)
                code |= _report([(s, "%s: %s" % (path, m)) for s, m in issues])
                if not issues or all(s == "warning" for s, _ in issues):
                    route = finding_route(f)
                    print("routed: %s → %s" % (f["id"], route) if route else
                          "not routed: %s (verified_by.result: %s)" % (f["id"], f["verified_by"]["result"]))
            return code
        if a.cmd == "cost":
            text = _read(a.file)
            issues = check_cost(text)
            if not issues:
                print(json.dumps(sum_cost(text), indent=2, sort_keys=True))
            return _report(issues)
        if a.cmd == "vendor-check":
            issues = vendor_check(a.dir)
            code = _report(issues)
            if not code:
                print("ok: %s matches MANIFEST (contracts %s)" % (a.dir, VERSION))
            return code
        if a.cmd == "seal":
            seal(a.dir)
            return 0
    except (OSError, YamlError, ValueError) as e:
        print("error: %s" % e)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
