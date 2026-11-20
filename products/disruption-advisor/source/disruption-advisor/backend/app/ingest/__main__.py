"""Ingest command:  python -m app.ingest [--force] [--skip-bookings]

Reads the airline extracts from INPUT_DIR (read-only) and writes Parquet to DATA_DIR/raw and DATA_DIR/ops.
Stage 1 (extracts -> raw Parquet, minutes) runs only when the inputs changed since the last successful run
(fingerprint of names, sizes and modification times). Stage 2 (raw -> ops, seconds) runs when the inputs or the
options changed. DEMO_SCENARIO=true appends the labelled synthetic demo scenario (app/ingest/demo.py).
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from app.ingest import build, convert, demo

log = logging.getLogger("ingest")


def fingerprint(input_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in input_dir.iterdir() if p.is_file()):
        st = f.stat()
        h.update(f"{f.name}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild everything even if nothing changed")
    parser.add_argument("--skip-bookings", action="store_true", help="reuse the existing bookings Parquet")
    args = parser.parse_args()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    input_dir = Path(os.environ.get("INPUT_DIR", "/input"))
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    with_demo = os.environ.get("DEMO_SCENARIO", "false").strip().lower() in {"1", "true", "yes"}
    raw_marker, ops_marker = data_dir / "ingest_fingerprint.txt", data_dir / "ops_fingerprint.txt"
    inputs = fingerprint(input_dir)
    ops_key = f"{inputs}|demo={with_demo}"

    raw_current = raw_marker.exists() and raw_marker.read_text() == inputs and (data_dir / "raw" / "bookings").exists()
    if args.force or not raw_current:
        log.info("stage 1: converting extracts to Parquet")
        raw = convert.run(input_dir, data_dir, skip_bookings=args.skip_bookings)
        log.info("stage 1 done: %s", json.dumps(raw))
        raw_marker.write_text(inputs)
    else:
        log.info("stage 1 skipped: extracts unchanged")

    if not args.force and raw_current and ops_marker.exists() and ops_marker.read_text() == ops_key:
        log.info("stage 2 skipped: operating picture is current")
        return 0
    log.info("stage 2: building the operating picture")
    report = build.build(data_dir)
    log.info("stage 2 done: %s", json.dumps(report["counts"]))
    if with_demo:
        log.info("demo scenario added: %s", json.dumps(demo.add_demo_scenario(data_dir / "ops")))
    ops_marker.write_text(ops_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
