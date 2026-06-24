"""Stream wrapper that timestamps raw print() output for log correlation.

Third-party libraries (yfinance, curl_cffi) print warnings/errors directly to
stdout/stderr, bypassing loguru and uvicorn's own timestamped formatters. In
the combined gateway.log this raw output has no timestamp, making it
impossible to tell when a burst of "possibly delisted" spam happened relative
to other timestamped log lines (e.g. a crash a few lines later).
"""

import re
import time
from typing import TextIO

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")


class TimestampedStream:
    """Wraps a text stream, prefixing each line with a timestamp unless it
    already starts with one (loguru/uvicorn lines are left untouched)."""

    def __init__(self, stream: TextIO):
        self._stream = stream
        self._at_line_start = True

    def write(self, data: str) -> int:
        if not data:
            return 0
        out = []
        for chunk in data.splitlines(keepends=True):
            if self._at_line_start and chunk.strip() and not _TIMESTAMP_RE.match(chunk):
                out.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {chunk}")
            else:
                out.append(chunk)
            self._at_line_start = chunk.endswith("\n")
        return self._stream.write("".join(out))

    def flush(self) -> None:
        self._stream.flush()

    def isatty(self) -> bool:
        return self._stream.isatty()

    def __getattr__(self, name):
        return getattr(self._stream, name)


def install() -> None:
    """Wrap sys.stdout/sys.stderr in-place with TimestampedStream."""
    import sys
    if not isinstance(sys.stdout, TimestampedStream):
        sys.stdout = TimestampedStream(sys.stdout)
    if not isinstance(sys.stderr, TimestampedStream):
        sys.stderr = TimestampedStream(sys.stderr)
