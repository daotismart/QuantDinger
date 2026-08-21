#!/usr/bin/env python3
"""Fix missing commas between consecutive JSON-like string entries in locale JS files."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def fix_text(text: str) -> str:
    # Insert comma when a "key": "value" line is followed by another "key"
    # without a comma. Handles simple string values (no raw newlines).
    pattern = re.compile(
        r'(":\s*"(?:\\.|[^"\\])*")\s*\n(\s*")',
        re.MULTILINE,
    )
    fixed = pattern.sub(r"\1,\n\2", text)
    fixed = re.sub(r",,+", ",", fixed)
    return fixed


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: fix_locale_commas.py <file>...", file=sys.stderr)
        return 2
    for raw in argv[1:]:
        path = Path(raw)
        original = path.read_text(encoding="utf-8")
        fixed = fix_text(original)
        path.write_text(fixed, encoding="utf-8")
        print(f"fixed {path} changed={original != fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
