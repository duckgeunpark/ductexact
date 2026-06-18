"""Pattern 치수표 -> CSV / 텍스트."""
from __future__ import annotations

import csv

from ..core.pattern import Pattern


def table_rows(pattern: Pattern) -> list[dict]:
    return pattern.table


def export_csv(pattern: Pattern, path: str) -> str:
    rows = pattern.table
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def as_text(pattern: Pattern) -> str:
    lines = [f"[{pattern.shape_name}]"]
    for r in pattern.table:
        lines.append("  " + " | ".join(f"{k}: {v}" for k, v in r.items()))
    if pattern.notes:
        lines.append("-- 비고 --")
        lines.extend("  " + n for n in pattern.notes)
    return "\n".join(lines)
