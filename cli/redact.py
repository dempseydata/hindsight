"""Secret redaction for the backstop's blobs (risk 1 in docs/architecture.md).

The backstop snapshots operator config — settings.json, settings.local.json,
mcp.json and every committed .claude/* file — and settings and MCP config
commonly carry API keys. Nothing renders a blob; they exist so a change can be
detected and diffed. Redacting before storage keeps that, minus the secrets.

JSON is walked: a value is replaced when its key names a secret, when it sits
under a `headers` object, or when it follows a secret-named CLI flag in a
list; every remaining string still gets the text pass. Anything else gets the
text pass alone: known key shapes, secret-named assignments, URL credentials,
private-key blocks. Redaction is idempotent, so a redacted blob's hash is
stable from run to run and change detection holds.
"""
import json
import re

MARK = "<redacted>"

# A key, env var or flag whose name says it holds a secret: it must END in the
# secret word, so input_tokens, token_budget and secretName pass untouched.
_SUFFIX = r"(?:api[_-]?key|access[_-]?key|private[_-]?key|secret|token|passw(?:or)?d|credentials?)"
SECRET_NAME = re.compile(rf"^[\w.-]*{_SUFFIX}$|^(?:auth|authorization|cookie|bearer)$", re.I)

_TEXT = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), MARK),
    (re.compile(r"\bsk-ant-[\w-]{8,}"), MARK),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), MARK),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[\w]{20,})"), MARK),
    (re.compile(r"\bxox[abprs]-[\w-]{10,}"), MARK),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), MARK),
    (re.compile(r"\bAIza[\w-]{35}"), MARK),
    (re.compile(r"\b(Bearer|Basic)\s+(?=[\w.~+/=-]*\d)[\w.~+/=-]{16,}"), r"\1 " + MARK),
    (re.compile(r"(://)[^/\s:@]+:[^/\s@]+@"), r"\1" + MARK + "@"),
    # NAME=value / NAME: value / --name=value where the name ends in a secret
    # word and the value is a literal: 12+ chars with a digit, not $(...) or <...>
    (re.compile(rf"(?i)\b((?:--?)?[\w-]*{_SUFFIX}[\"']?\s*[=:]\s*[\"']?)"
                r"(?![$<])(?=[^\s\"',}]*\d)[^\s\"',}]{12,}"), r"\1" + MARK),
]


def redact_text(text):
    for pattern, repl in _TEXT:
        text = pattern.sub(repl, text)
    return text


def _walk(node, under_headers=False):
    if isinstance(node, dict):
        return {k: (MARK if (under_headers or SECRET_NAME.search(k)) and isinstance(v, str)
                    else _walk(v, under_headers=k.lower() == "headers"))
                for k, v in node.items()}
    if isinstance(node, list):
        out, hide_next = [], False
        for item in node:
            if hide_next and isinstance(item, str) and not item.startswith("-"):
                out.append(MARK)
            else:
                out.append(_walk(item))
            hide_next = isinstance(item, str) and item.startswith("-") \
                and "=" not in item and bool(SECRET_NAME.search(item))
        return out
    if isinstance(node, str):
        return redact_text(node)
    return node


def redact(content):
    """The blob form of a config file: secrets replaced by MARK."""
    try:
        data = json.loads(content)
    except ValueError:
        return redact_text(content)
    if not isinstance(data, (dict, list)):
        return redact_text(content)
    walked = _walk(data)
    # Unchanged JSON keeps its exact text, so most blobs keep their hash.
    return content if walked == data else json.dumps(walked, indent=2, ensure_ascii=False) + "\n"
