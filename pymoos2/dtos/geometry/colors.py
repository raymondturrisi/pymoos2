"""MOOS color strings: named colors ("dark_blue", "DarkBlue"), decimal
triples ("0.5,0.5,0.5"), "hex:ff,80,00", and invisible, empty or off.

CSS "#rrggbb" is not a MOOS color; css_to_moos() converts it.
"""

from pymoos2.dtos.geometry._color_table import NAMED_COLORS

INVISIBLE = "invisible"
_INVISIBLE_WORDS = ("invisible", "empty", "off")
_SEPARATORS = ",:%$#"


def _normalize_name(s):
    return s.strip().lower().replace("_", "")


def parse_color(text):
    """(r, g, b) floats, 'invisible', or None."""
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None
    low = s.lower()
    if low in _INVISIBLE_WORDS:
        return INVISIBLE
    if low.startswith("hex:"):
        parts = low[4:].split(",")
        if len(parts) != 3:
            return None
        try:
            return tuple(int(p, 16) / 255.0 for p in parts)
        except ValueError:
            return None
    if any(c in s for c in _SEPARATORS):
        for sep in _SEPARATORS:
            if sep in s:
                parts = s.split(sep)
                break
        if len(parts) != 3:
            return None
        try:
            vals = [min(1.0, max(0.0, float(p))) for p in parts]
        except ValueError:
            return None
        return tuple(vals)
    rgb = NAMED_COLORS.get(_normalize_name(s))
    return rgb


def is_color(text):
    """True for anything parse_color understands (including invisibility words)."""
    return parse_color(text) is not None


def to_css(color, alpha=None):
    """CSS color for a parsed or MOOS color; 'transparent' for invisible,
    None when the input is not a color.
    """
    rgb = parse_color(color) if isinstance(color, str) else color
    if rgb is None:
        return None
    if rgb == INVISIBLE:
        return "transparent"
    r, g, b = (int(round(c * 255)) for c in rgb)
    if alpha is None:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{max(0.0, min(1.0, alpha)):.3f})"


def css_to_moos(css_hex):
    """'#rrggbb' -> 'hex:rr,gg,bb' (the hex form MOOS-IvP accepts)."""
    s = css_hex.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"not a css hex color: {css_hex}")
    return f"hex:{s[0:2]},{s[2:4]},{s[4:6]}"


def color_names():
    return sorted(NAMED_COLORS)
