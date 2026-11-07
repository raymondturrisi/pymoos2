"""
XYTextBox — VIEW_TEXTBOX geometry DTO.

Spec: x=<v>,y=<v>,msg="<line>"[,msg="<line>"]*[,fsize=<pt>][,mcolor=<color>][,<common fields>]
A bare number token sets fsize and a bare color name sets mcolor.
"""

from pymoos2.core.strutil import double_to_string_x, is_number, strip_quotes
from pymoos2.dtos.geometry.XYObject import XYObject, tokenize_spec
from pymoos2.dtos.geometry.colors import is_color


class XYTextBox(XYObject):
    KIND = "textbox"

    def __init__(self, x=None, y=None, **kwargs):
        super().__init__(**kwargs)
        if x is not None and y is not None:
            self.x, self.y = float(x), float(y)
            self._set.update(("x", "y"))

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.messages = []
        self.fsize = 10
        self.mcolor = ""
        self._set = set()

    def add_msg(self, text):
        self.messages.append(text)

    def valid(self):
        return {"x", "y"} <= self._set

    def _set_own_param(self, key, value):
        if value is None:
            if is_number(key):
                self.fsize = int(float(key))
                return True
            if is_color(key):
                self.mcolor = key
                return True
            return False
        if key in ("x", "y") and is_number(value):
            setattr(self, key, float(value))
            self._set.add(key)
        elif key == "msg":
            self.messages.append(strip_quotes(value))
        elif key == "fsize" and is_number(value):
            self.fsize = int(float(value))
        elif key == "mcolor" and is_color(value):
            self.mcolor = value
        else:
            return False
        return True

    @classmethod
    def from_spec(cls, spec):
        obj = cls()
        obj._apply_tokens(tokenize_spec(spec))
        if not obj.messages and obj.duration is None:
            obj.duration = 1.0
        return obj

    def get_spec(self, *, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}"]
        parts += [f'msg="{m}"' for m in self.messages]
        parts.append(f"fsize={self.fsize}")
        if self.mcolor:
            parts.append(f"mcolor={self.mcolor}")
        common = [p for p in self._common_spec(active) if not p.startswith("msg=")]
        return ",".join(parts + common)

    def _inactive_parts(self):
        return ["x=0", "y=0", "msg=null"]

    def _fields_dict(self):
        d = {"x": self.x, "y": self.y, "messages": list(self.messages), "fsize": self.fsize}
        if self.mcolor:
            d["mcolor"] = self.mcolor
        return d
