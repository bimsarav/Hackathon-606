#!/usr/bin/env python3
"""Repairs the three syntax defects of the supplied ESMP dump (docs/data/data-quality-report.md §1).

  python3 tools/seed/repair_dump.py tools/seed/legacy/esmp_sample_dump.sql > repaired.sql

L1 unquoted priority names (P1..P4), L2 unquoted status names, L3 Python `None` instead of NULL.
The original file is never modified.
"""
import re
import sys


def repair(sql: str) -> str:
    sql = re.sub(r"^\((\d+),(P\d),", r"(\1,'\2',", sql, flags=re.M)
    sql = re.sub(r"^\((\d+),([A-Z_]+),(True|False)\)", r"(\1,'\2',\3)", sql, flags=re.M)
    prev = None
    while prev != sql:
        prev = sql
        sql = re.sub(r"([,(])None([,)])", r"\1NULL\2", sql)
    return sql


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(repair(f.read()))
