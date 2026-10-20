#!/usr/bin/env python3
"""engine-skip-report — make container-engine skips visible, and fail an empty pass.

WHY THIS EXISTS. This package's live integration tests use a real Docker or Podman engine (and,
for some, a reachable registry). Those tests skip with the engine's own error when no engine is
available — which is the honest behaviour, and must stay that way. The risk is the other
direction: a suite that reports "green" because everything skipped. This script reads a pytest
log, prints every skip with its reason, and exits 1 when nothing actually passed.

It never changes the tests and never turns a skip into a pass. CI runs it on the log produced by
`make test`; a developer can run it on any saved pytest output.

Usage:
    python3 scripts/engine-skip-report.py <pytest-log>
    make test > pytest.log 2>&1; python3 scripts/engine-skip-report.py pytest.log

Exit 0 = at least one test passed (skips, if any, are reported).
Exit 1 = no test passed, the log is unreadable, or the run recorded failures/errors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_COUNT = re.compile(r"(\d+) (passed|skipped|failed|error|errors|xfailed|xpassed)")
_SKIP_LINE = re.compile(r"^SKIPPED\b")

# Failures/errors are already fatal in the pytest exit code, but the log is the
# only input here, so re-check them rather than trusting the caller.
_FATAL = ("failed", "error", "errors")


def _counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in _COUNT.finditer(text):
        value = int(match.group(1))
        key = match.group(2)
        # Keep the largest occurrence: the summary line is the last match, but
        # progress lines can mention the same token earlier.
        counts[key] = max(counts.get(key, 0), value)
    return counts


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 1
    log_path = Path(argv[1])
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"engine-skip-report: cannot read {log_path}: {exc}", file=sys.stderr)
        return 1

    counts = _counts(text)
    passed = counts.get("passed", 0)
    skipped = counts.get("skipped", 0)

    for line in text.splitlines():
        if _SKIP_LINE.match(line):
            print(f"engine-skip-report: {line}")

    fatal = {key: counts[key] for key in _FATAL if counts.get(key)}
    if fatal:
        print(f"engine-skip-report: FAIL run recorded {fatal}", file=sys.stderr)
        return 1
    if passed == 0:
        print(
            "engine-skip-report: FAIL no test passed — the suite cannot be green by skipping "
            f"everything (skipped={skipped})",
            file=sys.stderr,
        )
        return 1

    if skipped:
        print(
            f"engine-skip-report: {passed} passed, {skipped} skipped — "
            "reasons above; container-engine tests skipped honestly, not removed"
        )
    else:
        print(f"engine-skip-report: {passed} passed, 0 skipped — every test ran")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
