"""
Mission file (.moos) parser.

Reads global key=value pairs and ProcessConfig blocks.
"""

import os


class MissionReader:
    """Reads a .moos mission file for global params and ProcessConfig blocks."""

    def __init__(self, filepath="", app_name=""):
        self._globals = {}
        self._configs = {}
        self._app_name = app_name
        if filepath and os.path.isfile(filepath):
            self._parse(filepath)

    def _parse(self, filepath):
        """Parse the .moos file."""
        with open(filepath, "r") as f:
            lines = f.readlines()

        current_block = None
        current_block_name = None
        brace_depth = 0

        for raw_line in lines:
            line = raw_line.split("//")[0].strip()
            if not line:
                continue

            if line.upper().startswith("PROCESSCONFIG"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    name = parts[1].strip().rstrip("{").strip()
                    current_block_name = name
                    current_block = {}
                    self._configs[name] = current_block
                    if "{" in line:
                        brace_depth = 1
                    continue

            if current_block_name is not None:
                if "{" in line and brace_depth == 0:
                    brace_depth = 1
                    continue
                if brace_depth > 0:
                    if "}" in line:
                        brace_depth -= 1
                        if brace_depth == 0:
                            current_block = None
                            current_block_name = None
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        current_block[k.strip().lower()] = v.strip()
                continue

            if "=" in line:
                k, v = line.split("=", 1)
                self._globals[k.strip()] = v.strip()

    def get_value(self, key, default=None, type=str):
        """Get a global (top-level) parameter (case-insensitive)."""
        raw = self._globals.get(key)
        if raw is None:
            key_lower = key.lower()
            for k, v in self._globals.items():
                if k.lower() == key_lower:
                    raw = v
                    break
        if raw is None:
            return default
        try:
            return type(raw)
        except (ValueError, TypeError):
            return default

    def get_config(self, key, default=None, type=str):
        """Get a parameter from this app's ProcessConfig block."""
        block = self._configs.get(self._app_name, {})
        raw = block.get(key.lower())
        if raw is None:
            return default
        try:
            if type is bool:
                return raw.lower() in ("true", "1", "yes")
            return type(raw)
        except (ValueError, TypeError):
            return default

    def get_config_list(self):
        """Return all key=value pairs from this app's ProcessConfig block."""
        return dict(self._configs.get(self._app_name, {}))

    def get_all_globals(self):
        """Return all global key=value pairs."""
        return dict(self._globals)
