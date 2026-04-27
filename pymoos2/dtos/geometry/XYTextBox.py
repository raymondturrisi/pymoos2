"""
XYTextBox — VIEW_TEXTBOX geometry DTO.

Spec format: x=<val>,y=<val>,msg="<text>"[,msg="<text>"]*,fsize=<val>
             [,mcolor=<color>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYTextBox(XYObject):
    def __init__(self, x=0.0, y=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.messages = []
        self.fsize = 12
        self.mcolor = ""

    def add_msg(self, text):
        self.messages.append(text)

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}"]
        for m in self.messages:
            parts.append(f'msg="{m}"')
        parts.append(f"fsize={self.fsize}")
        if self.mcolor:
            parts.append(f"mcolor={self.mcolor}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "fsize" in params: obj.fsize = int(params.pop("fsize"))
        if "mcolor" in params: obj.mcolor = params.pop("mcolor")
        import re
        for match in re.finditer(r'msg="([^"]*)"', spec):
            obj.messages.append(match.group(1))
        cls._parse_common(obj, params)
        return obj
