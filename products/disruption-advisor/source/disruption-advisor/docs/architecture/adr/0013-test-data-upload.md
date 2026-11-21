# ADR 0013: Test data upload for evaluators

Status: accepted (21 Nov 2026), user request. Not yet deployed.

## Context
Evaluators will bring one or two flights of their own and want to search them and see the disruption details. The
ingest takes full extracts (hundreds of thousands of rows, minutes to run, models retrained); it is the wrong tool
for two flights. The API mounts the operating data read-only, and runs two worker processes.

## Decision
- A **Test data** tab: it lists the two CSV sheets (flights, passengers) with every column, an example and a
  downloadable template. The evaluator picks both files, presses **Check files** (nothing is stored), then
  **Add to system**. **Remove test data** deletes them again.
- Our own simple template, not the full extract layouts. Everything the sheets lack is filled with labelled
  placeholders (synthetic passport and national id, fare by fare family, `capacity_source = judge-test-data`).
  A passenger on two flights has two rows: the second flight is the onward flight, so connections work.
- **Add on top, never replace.** The checked rows are written as three small Parquet files in their own folder
  (`TEST_DATA_DIR`, Docker volume `test-data`, writable by the API). `OpsStore` appends them to its in-memory tables
  at load time. The real Parquet, the trained models and the ingest are untouched. Uploading again replaces the
  earlier test data; flights that clash with a real flight (same number and departure) are rejected.
- **Score only.** The delay and reward models are not retrained. The saved delay model (ADR 0008) scores the new flights at
  upload time with the live history behind their features, and the result (`flight_risk`, `connection_risk`) is stored next to the
  test data and appended to the store's risk tables, so they appear in the 7-day watchlist and the flight risk page. If no saved model
  exists (ingest not run since this release) or it does not match the code, the flights are added without risk figures and the page says so.
  The reward model is already saved and loaded; it needs no change. The page and the check warn when a route has no history.
- **Multi-worker safe.** The manifest file's modification time is the version. Every `get_store()` call compares it with
  the version the worker loaded and reloads on a change, so no restart and no cross-process message are needed.
- **Atomic.** Tables are written first, the manifest last; a bad upload is rejected before anything is written.
- **Roles:** a third demo role, `EVALUATOR`, sees every view. `OCC` and `PCU` do not see the **Model** and **Test data** tabs, and the
  server refuses them (403) on `/api/v1/test-data*` and `/api/v1/risk/model`; every other endpoint is open to all three roles.
  Accounts come from `DEMO_USERS` (`user:password:ROLE`, comma separated). Limits: 50 flights, 3,000 passenger rows,
  1 MB per sheet (JSON body, no multipart dependency).

## Consequences
- No ingest run, no retraining, a few seconds from upload to searchable.
- Test flights show in search, the scenario, rebooking, care and reward views, and (when scored) in the 7-day watchlist.
- Scenarios saved for test flights stay in Postgres after the test data is removed; reopening them still works from
  the stored result.
- Needs the `test-data` volume and `TEST_DATA_DIR` (default `/testdata`). Not copied to the `extracts` schema.
