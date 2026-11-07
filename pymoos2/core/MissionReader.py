"""Reader for .moos mission files."""

from pymoos2.core.strutil import strip_comment, to_bool


class MissionReader:
    def __init__(self, filepath, app_name=""):
        """Raises OSError when filepath cannot be read."""
        self.filepath = filepath
        self._app_name = app_name
        self._global_lines = []
        self._block_lines = {}
        self._block_order = []
        self.warnings = []
        self._parse(filepath)

    def _parse(self, filepath):
        with open(filepath, "r", errors="replace") as f:
            raw_lines = f.readlines()

        block = None
        pending = None

        for lineno, raw in enumerate(raw_lines, 1):
            line = strip_comment(raw.rstrip("\n")).strip()
            if not line:
                continue

            if pending is not None:
                if line.startswith("{"):
                    block = pending
                    pending = None
                    rest = line[1:].strip()
                    if rest:
                        self._add_block_line(block, rest, lineno)
                else:
                    self.warnings.append(
                        f"line {lineno}: expected '{{' after ProcessConfig = {pending}")
                    pending = None
                    block = None
                continue

            if block is None:
                if line.lower().startswith("processconfig"):
                    _, _, name = line.partition("=")
                    name = name.strip()
                    opened = False
                    if name.endswith("{"):
                        name = name[:-1].strip()
                        opened = True
                    if not name:
                        self.warnings.append(f"line {lineno}: ProcessConfig without a name")
                        continue
                    self._block_lines.setdefault(name, [])
                    if name not in self._block_order:
                        self._block_order.append(name)
                    if opened:
                        block = name
                    else:
                        pending = name
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    self._global_lines.append((k.strip(), v.strip()))
                continue

            if line.startswith("}"):
                block = None
                continue
            if line.startswith("{"):
                continue
            self._add_block_line(block, line, lineno)

    def _add_block_line(self, block, line, lineno):
        if "=" not in line:
            self.warnings.append(f"line {lineno}: ignored '{line}' in ProcessConfig = {block}")
            return
        k, v = line.split("=", 1)
        self._block_lines[block].append((k.strip(), v.strip()))

    def _block_name(self, app_name=None):
        name = app_name if app_name is not None else self._app_name
        if name in self._block_lines:
            return name
        lname = name.lower()
        for b in self._block_order:
            if b.lower() == lname:
                return b
        return None

    @staticmethod
    def _convert(raw, default, type):
        if raw is None:
            return default
        if type is bool:
            return to_bool(raw, default)
        try:
            return type(raw)
        except (ValueError, TypeError):
            return default

    def get_value(self, key, default=None, type=str):
        """A global parameter, case-insensitive; the first line wins."""
        lkey = key.lower()
        for k, v in self._global_lines:
            if k.lower() == lkey:
                return self._convert(v, default, type)
        return default

    def get_config(self, key, default=None, type=str, first=False):
        """A parameter from an app's ProcessConfig block, case-insensitive; the
        last line wins unless first=True.
        """
        block = self._block_name()
        if block is None:
            return default
        lkey = key.lower()
        found = None
        for k, v in self._block_lines[block]:
            if k.lower() == lkey:
                found = v
                if first:
                    break
        return self._convert(found, default, type)

    def get_config_lines(self, app_name=None):
        """Every (key, value) line of a ProcessConfig block, in file order."""
        block = self._block_name(app_name)
        if block is None:
            return []
        return list(self._block_lines[block])

    def get_config_values(self, key, app_name=None):
        """All values for a repeated key, in file order."""
        lkey = key.lower()
        return [v for k, v in self.get_config_lines(app_name) if k.lower() == lkey]

    def has_block(self, app_name=None):
        return self._block_name(app_name) is not None

    def block_names(self):
        return list(self._block_order)

    def get_all_globals(self):
        """Dict of global key=value pairs (first value wins)."""
        out = {}
        for k, v in self._global_lines:
            out.setdefault(k, v)
        return out

    def get_global_lines(self):
        return list(self._global_lines)
