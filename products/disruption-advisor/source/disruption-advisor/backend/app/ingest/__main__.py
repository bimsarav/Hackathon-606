"""Ingest command:  python -m app.ingest [--force] [--skip-bookings]

Reads the airline extracts from INPUT_DIR (read-only) and writes Parquet to DATA_DIR/raw and DATA_DIR/ops.
Stage 1 (extracts -> raw Parquet, minutes) runs only when the inputs changed since the last successful run
(fingerprint of names, sizes and modification times) or the bookings are still in an older layout. Bookings
supplied as name-free Parquet (INPUT_DIR/parquet/raw/bookings) are used instead of converting the zip.
Stage 2 (raw -> ops, seconds) runs when the inputs, the
options or the build code changed.
OPERATING_CARRIERS (default G9) limits the picture to those carriers.
DEMO_SCENARIO=true appends the labelled synthetic demo scenario (app/ingest/demo.py).
Stage 3 (phase 2) trains the delay-risk model and scores the window (app/ml/delay_risk.py, ~30 s on the server).
Stage 4 (phase 5) trains the reward preference model on simulated redemption history (app/ml/reward_pref.py).
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from app.ingest import build, convert, demo
from app.ml import delay_risk, reward_pref

log = logging.getLogger("ingest")


def fingerprint(input_dir: Path) -> str:
    """Names, sizes and modification times of the extracts and of any supplied name-free bookings Parquet."""
    h = hashlib.sha256()
    supplied = convert.supplied_bookings(input_dir)
    files = [p for p in input_dir.iterdir() if p.is_file()] + (list(supplied.rglob("*.parquet")) if supplied else [])
    for f in sorted(files):
        st = f.stat()
        h.update(f"{f.relative_to(input_dir)}|{st.st_size}|{int(st.st_mtime)}".encode())
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
    carriers = (
        tuple(c.strip().upper() for c in os.environ.get("OPERATING_CARRIERS", "G9").split(",") if c.strip().isalnum())
        or build.DEFAULT_CARRIERS
    )
    raw_marker, ops_marker = data_dir / "ingest_fingerprint.txt", data_dir / "ops_fingerprint.txt"
    inputs = fingerprint(input_dir)
    # stage 2 also reruns when its code changes (build rules, synthetic data), so a deploy picks up new logic
    code = hashlib.sha256(
        b"".join(Path(m.__file__ or "").read_bytes() for m in (build, demo, delay_risk, reward_pref))
    ).hexdigest()[:16]
    ops_key = f"{inputs}|demo={with_demo}|carriers={','.join(carriers)}|code={code}"

    # bookings must be in the current layout: name-free, by departure month (an older dep_year layout is rebuilt)
    bookings_current = any((data_dir / "raw" / "bookings").glob("dep_month=*"))
    raw_current = raw_marker.exists() and raw_marker.read_text() == inputs and bookings_current
    if args.force or not raw_current:
        log.info("stage 1: converting extracts to Parquet")
        raw = convert.run(input_dir, data_dir, skip_bookings=args.skip_bookings)
        log.info("stage 1 done: %s", json.dumps(raw))
        raw_marker.write_text(inputs)
    else:
        log.info("stage 1 skipped: extracts unchanged")

    ops_present = (data_dir / "ops" / "flights.parquet").exists()
    if not args.force and raw_current and ops_present and ops_marker.exists() and ops_marker.read_text() == ops_key:
        log.info("stage 2 skipped: operating picture is current")
        return 0
    log.info("stage 2: building the operating picture")
    report = build.build(data_dir, carriers=carriers)
    log.info("stage 2 done: %s", json.dumps(report["counts"]))
    if with_demo:
        log.info("demo scenario added: %s", json.dumps(demo.add_demo_scenario(data_dir / "ops")))
    # stage 3 (phase 2): delay-risk model, trained and scored on the fresh operating picture
    if (data_dir / "ops" / "history_flights.parquet").exists():
        mct = delay_risk.default_mct_from_env(os.environ.get("DEFAULT_MCT_MINUTES"))
        log.info("stage 3 done: %s", json.dumps(delay_risk.run(data_dir / "ops", default_mct=mct)))
    else:
        log.warning("stage 3 skipped: no history_flights.parquet")
    # stage 4 (phase 5): reward preference model, trained on simulated redemption history (app/ml/reward_pref.py)
    log.info("stage 4 done: %s", json.dumps(reward_pref.run(data_dir / "ops")))
    ops_marker.write_text(ops_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
