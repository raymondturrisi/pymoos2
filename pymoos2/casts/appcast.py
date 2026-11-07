"""APPCAST wire format.

  proc=P!@#iter=N!@#node=V!@#iter=N!@#messages=l1!@l2!@!@#config_warnings=a!@b!@#
  events_total=K!@#events=e1!@e2!@#run_warning_total=M!@#run_warnings=2:w1!@1:w2

Outer separator !@#, inner separator !@.
"""

from pymoos2.core.strutil import to_int

OSEP = "!@#"
ISEP = "!@"


class AppCast:
    def __init__(self, proc="", node="", iteration=0):
        self.proc = proc
        self.node = node
        self.iteration = iteration
        self.messages = ""
        self.config_warnings = []
        self.events = []
        self.run_warning_total = 0
        self.run_warnings = {}
        self.received_time = None

    @property
    def config_warning_count(self):
        return len(self.config_warnings)

    @property
    def run_warning_count(self):
        return self.run_warning_total

    def get_formatted_string(self, with_header=True):
        """The appcast as text, laid out as uMAC shows it."""
        out = []
        if with_header:
            iter_str = f"({self.iteration})"
            warn_str = f"{len(self.config_warnings)}/{self.run_warning_total}"
            title = f"{self.proc} {self.node}"
            max_len = 62
            now_len = len(warn_str) + len(title) + len(iter_str)
            pad = " " * (max_len - now_len) if now_len < max_len else ""
            out.append("=" * 62)
            out.append(f"{title}{pad}{warn_str}{iter_str}")
            out.append("=" * 62)
        if self.config_warnings:
            n = len(self.config_warnings)
            out.append(f"Configuration Warnings: {n}")
            for i, w in enumerate(self.config_warnings, 1):
                out.append(f" [{i} of {n}]: {w}")
            out.append("")
        if self.run_warning_total > 0:
            out.append(f"Runtime Warnings: {self.run_warning_total}")
            for text, count in self.run_warnings.items():
                out.append(f" [{count}]: {text}")
            out.append("")
        out.append(self.messages)
        if self.events:
            out.append("=" * 67)
            out.append(f"Most Recent Events ({len(self.events)}):")
            out.append("=" * 67)
            out.extend(reversed(self.events))
        return "\n".join(out) + "\n"

    def to_dict(self):
        return {
            "proc": self.proc,
            "node": self.node,
            "iter": self.iteration,
            "messages": self.messages,
            "config_warnings": list(self.config_warnings),
            "events": list(self.events),
            "run_warning_total": self.run_warning_total,
            "run_warnings": [{"count": c, "text": t} for t, c in self.run_warnings.items()],
            "received_time": self.received_time,
        }

    def __repr__(self):
        return f"AppCast({self.proc}@{self.node} iter={self.iteration} cw={len(self.config_warnings)} rw={self.run_warning_total})"


def parse_appcast(text):
    """Parse an APPCAST value. Unknown fields are ignored; never raises."""
    ac = AppCast()
    for pair in text.split(OSEP):
        if "=" not in pair:
            continue
        param, value = pair.split("=", 1)
        param = param.strip()
        if param == "proc":
            ac.proc = value.strip()
        elif param == "iter":
            n = to_int(value)
            if n is not None:
                ac.iteration = n
        elif param == "node":
            ac.node = value.strip()
        elif param == "messages":
            lines = value.split(ISEP)
            if lines and lines[-1] == "":
                lines = lines[:-1]
            ac.messages = "\n".join(lines) + ("\n" if lines else "")
        elif param == "config_warnings":
            ac.config_warnings = [w.strip() for w in value.split(ISEP) if w.strip()]
        elif param == "events":
            ac.events = [e.strip() for e in value.split(ISEP) if e.strip()]
        elif param == "run_warning_total":
            n = to_int(value)
            if n is not None:
                ac.run_warning_total = max(0, n)
        elif param == "run_warnings":
            for item in value.split(ISEP):
                item = item.strip()
                if not item:
                    continue
                count, _, warning = item.partition(":")
                n = to_int(count)
                if n is None:
                    n, warning = 0, item
                n = max(0, n)
                ac.run_warnings[warning.strip()] = n
    return ac
