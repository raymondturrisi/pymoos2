"""String helpers for mission files and VIEW_* specs."""

import re

_NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def strip_comment(line):
    """Remove a trailing // comment, except inside double quotes or a URL scheme."""
    in_quote = False
    i = 0
    n = len(line)
    while i < n - 1:
        c = line[i]
        if c == '"':
            in_quote = not in_quote
        elif c == "/" and line[i + 1] == "/" and not in_quote:
            if i > 0 and line[i - 1] == ":":
                i += 2
                continue
            return line[:i]
        i += 1
    return line


def parse_string(s, sep=","):
    """Split on sep, keeping empty fields."""
    if s == "":
        return []
    return s.split(sep)


def parse_string_q(s, sep=","):
    """Split on sep outside double quotes and (nested) braces."""
    out = []
    buf = []
    depth = 0
    in_quote = False
    for c in s:
        if c == '"':
            in_quote = not in_quote
            buf.append(c)
        elif in_quote:
            buf.append(c)
        elif c == "{":
            depth += 1
            buf.append(c)
        elif c == "}":
            depth = max(0, depth - 1)
            buf.append(c)
        elif c == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    out.append("".join(buf))
    return out


def parse_string_z(s, sep=",", protect_open="{"):
    """Split on sep outside the given braces."""
    close = {"{": "}", "(": ")", "[": "]", "<": ">"}.get(protect_open, "}")
    out = []
    buf = []
    depth = 0
    for c in s:
        if c == protect_open:
            depth += 1
        elif c == close:
            depth = max(0, depth - 1)
        if c == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    out.append("".join(buf))
    return out


def bite(s, sep):
    """Return (front, rest) split at the first sep; rest is '' if sep absent."""
    idx = s.find(sep)
    if idx < 0:
        return s, ""
    return s[:idx], s[idx + len(sep):]


def parse_kv(s, sep=",", lower_keys=True, quoted=True):
    """Parse 'k=v,k=v' into [(key, value)]; a token without '=' has value None."""
    tokens = parse_string_q(s, sep) if quoted else parse_string(s, sep)
    pairs = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            k = k.strip()
            if lower_keys:
                k = k.lower()
            pairs.append((k, v.strip()))
        else:
            pairs.append((tok.lower() if lower_keys else tok, None))
    return pairs


def strip_quotes(s):
    """Remove one pair of surrounding double quotes."""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def strip_braces(s):
    """Remove one pair of surrounding braces."""
    if len(s) >= 2 and s[0] == "{" and s[-1] == "}":
        return s[1:-1]
    return s


def is_number(s):
    """True if s parses as a plain decimal number."""
    return bool(_NUMBER_RE.match(s.strip())) if isinstance(s, str) else False


def is_boolean(s):
    return s.strip().lower() in ("true", "false")


def to_bool(s, default=False):
    v = s.strip().lower() if isinstance(s, str) else s
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    return default


def double_to_string(v, digits=2):
    """Fixed-decimal formatting."""
    return f"{float(v):.{digits}f}"


def double_to_string_x(v, digits=2):
    """Fixed decimals without trailing zeros or a trailing '.'; '-0' becomes '0'."""
    s = f"{float(v):.{digits}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


def macro_expand(s, key, value):
    """Replace every $(KEY) and $[KEY] in s with value."""
    value = str(value)
    return s.replace(f"$({key})", value).replace(f"$[{key}]", value)


def macro_expand_all(s, mapping):
    """Apply macro_expand for every key in mapping (longest keys first)."""
    for key in sorted(mapping, key=len, reverse=True):
        s = macro_expand(s, key, mapping[key])
    return s


def has_macro(s, key):
    return f"$({key})" in s or f"$[{key}]" in s
