"""
Column-aligned ASCII tables for AppCast reports.
"""


class ACTable:
    """Build formatted column-aligned tables for buildReport()."""

    def __init__(self, columns, pad=2):
        """
        columns: list of column header strings, e.g. ["Variable", "Value"]
        pad:     spaces between columns
        """
        self.headers = list(columns)
        self.ncols = len(columns)
        self.pad = pad
        self.rows = []
        self.widths = [len(h) for h in self.headers]

    def add(self, *values):
        """Add a row of values. Number of values should match number of columns."""
        row = [str(v) for v in values]
        while len(row) < self.ncols:
            row.append("")
        row = row[:self.ncols]
        self.rows.append(row)
        for i, v in enumerate(row):
            if len(v) > self.widths[i]:
                self.widths[i] = len(v)

    def _fmt_row(self, values):
        parts = []
        for i, v in enumerate(values):
            parts.append(v.ljust(self.widths[i]))
        sep = " " * self.pad
        return sep.join(parts)

    def __str__(self):
        lines = []
        lines.append(self._fmt_row(self.headers))
        lines.append(self._fmt_row(["-" * self.widths[i] for i in range(self.ncols)]))
        for row in self.rows:
            lines.append(self._fmt_row(row))
        return "\n".join(lines)
