"""Load the 18 monthly booking CSVs (nested zips, Latin-1) into DuckDB table `bookings`.
Each physical line is one record; lines with the wrong field count or an unterminated quote are rejected
and written to rejects_<month>.txt (Oct 2025 has 2 such lines). Usage: python load_bookings.py <zip> <out.duckdb>
"""
import csv, io, os, sys, zipfile
import duckdb

def main(zpath: str, db: str) -> None:
    con = duckdb.connect(db); outer = zipfile.ZipFile(zpath); first = True
    for n in sorted(x for x in outer.namelist() if x.endswith(".csv.zip") and not x.startswith("__MACOSX")):
        inner = zipfile.ZipFile(io.BytesIO(outer.read(n))); cn = inner.namelist()[0]; tag = cn[13:30]
        ok = bad = 0
        with inner.open(cn) as fi, open("u.csv", "w", encoding="utf-8", newline="") as fo, open(f"rejects_{tag}.txt", "w", encoding="utf-8") as rj:
            w = csv.writer(fo); hdr = None
            for raw in io.TextIOWrapper(fi, encoding="latin-1", newline=""):
                line = raw.rstrip("\r\n")
                if not line: continue
                try: rec = next(csv.reader([line]))
                except Exception: rec = []
                if hdr is None: hdr = rec; w.writerow(hdr + ["SRC_FILE"]); continue
                if len(rec) == len(hdr) and line.count('"') % 2 == 0: w.writerow(rec + [tag]); ok += 1
                else: bad += 1; rj.write(line[:300] + "\n")
        con.execute(("CREATE TABLE bookings AS " if first else "INSERT INTO bookings ") + "SELECT * FROM read_csv('u.csv', all_varchar=true, header=true)")
        first = False; os.remove("u.csv"); print(tag, "loaded", ok, "rejected", bad, flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
