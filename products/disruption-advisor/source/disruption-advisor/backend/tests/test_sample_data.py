"""Test data upload: validation messages, storage next to the real data, and a scenario on an uploaded flight."""

from pathlib import Path

from fastapi.testclient import TestClient

from app import sample_data
from app.config import Settings
from app.engine import priority
from app.engine.explain import Explainer
from app.engine.scenarios import Context, analyse_delay
from app.engine.store import OpsStore
from app.ml import delay_risk
from tests.ops_fixture import t, write_ops

FLIGHTS = (
    "flight_number,date,origin,destination,std,sta,aircraft_registration,seat_capacity,booked_seats\n"
    "G9801,2026-11-22,KHI,SHJ,05:00,07:30,A6-TST,174,160\n"
    "G9851,2026-11-22,SHJ,HBE,09:00,13:30,A6-TSU,174,174\n"
    "G9853,2026-11-23,SHJ,HBE,03:00,07:30,A6-TSV,174,166\n"
)
PEOPLE = [  # (pnr, first, last, type, ssr, tier)
    ("PN0001", "Ahmed", "Raza", "AD", "WCHR", ""),
    ("PN0002", "Omar", "Siddiqui", "AD", "", "Platinum"),
    ("PN0003", "Sara", "Malik", "AD", "", "Gold"),
]


def passengers(*, onward: bool = True) -> str:
    rows = [
        "pnr,first_name,last_name,pax_type,flight_number,date,fare_family,fare_aed,loyalty_tier,travel_frequency,special_service"
    ]
    for pnr, first, last, ptype, ssr, tier in PEOPLE:
        rows.append(f"{pnr},{first},{last},{ptype},G9801,2026-11-22,Value,,{tier},regular,{ssr}")
        if onward:
            rows.append(f"{pnr},{first},{last},{ptype},G9851,2026-11-22,Value,,{tier},regular,{ssr}")
    return "\n".join(rows) + "\n"


def test_template_matches_the_spec_and_is_valid() -> None:
    spec = sample_data.spec()
    flights, people = (f["template"] for f in spec["files"])
    result = sample_data.check(flights, people, set(), set())
    assert result.ok, [i.message for i in result.issues]
    assert len(result.flights) == 2
    assert len(result.customers) == 2
    assert flights.splitlines()[0].split(",") == [f["name"] for f in spec["files"][0]["fields"]]


def test_errors_name_the_file_row_and_column() -> None:
    bad_flights = FLIGHTS.replace("KHI,SHJ,05:00", "KHIX,SHJ,5pm").replace("A6-TSU,174,174", "A6-TSU,0,0")
    result = sample_data.check(bad_flights, passengers(), set(), set())
    found = {(i.file, i.row, i.column) for i in result.issues}
    assert ("flights.csv", 2, "origin") in found
    assert ("flights.csv", 2, "std") in found
    assert ("flights.csv", 3, "seat_capacity") in found
    result = sample_data.check(
        FLIGHTS, passengers().replace("Value", "Gold", 1).replace(",AD,", ",XX,", 1), set(), set()
    )
    assert {(i.row, i.column) for i in result.issues} == {(2, "fare_family"), (2, "pax_type")}
    missing = sample_data.check("flight_number,date\nG9801,2026-11-22\n", passengers(), set(), set())
    assert "Missing column(s)" in missing.issues[0].message
    unknown = sample_data.check(FLIGHTS, passengers().replace("G9851", "G9999", 1), set(), set())
    assert "No flight G9999" in unknown.issues[0].message


def test_clashes_and_overbooking_are_rejected() -> None:
    existing = sample_data.check(FLIGHTS, passengers(), {"G9801_202611220500"}, set())
    assert "already exists" in existing.issues[0].message
    over = sample_data.check(FLIGHTS.replace("A6-TST,174,160", "A6-TST,174,2"), passengers(), set(), set())
    assert "below the 3 passenger rows" in over.issues[0].message
    twice = sample_data.check(FLIGHTS, passengers() + passengers().split("\n", 1)[1], set(), set())
    assert "already on G9801" in twice.issues[0].message


def test_stored_flights_work_in_a_delay_scenario(tmp_path: Path) -> None:
    ops = write_ops(tmp_path)
    store = OpsStore(ops)
    before = store.query("SELECT count(*) AS n FROM flights")[0]["n"]
    checked = sample_data.check(FLIGHTS, passengers(), set(), set())
    assert checked.ok
    assert any("no flights on this route" in w for w in checked.warnings)  # KHI-SHJ is not in the fixture network
    folder = tmp_path / "testdata"
    sample_data.save(folder, checked, "occ (OCC)")

    store = OpsStore(ops, folder)
    assert store.query("SELECT count(*) AS n FROM flights")[0]["n"] == before + 3
    settings = Settings(database_url="postgresql+psycopg://unused", now_utc=t(0))
    ctx = Context(store, settings, Explainer("", settings.ai_model, "low", 1))
    result = analyse_delay(ctx, "G9801_202611220500", 150, priority.DEFAULT_WEIGHTS)
    assert len(result["misconnections"]) == 3  # the three connecting passengers miss G9851 (150 min late)
    rows = {r["name"]: r for r in result["passengers"]}
    assert len(rows) >= 3
    full = {a["flight_number"]: a for a in result["rebooking"]["alternatives"]}
    assert full["G9853"]["available_seats"] == 8  # next-day flight with 8 free seats; G9851 is full

    sample_data.clear(folder)
    assert sample_data.version(folder) is None
    assert OpsStore(ops, folder).query("SELECT count(*) AS n FROM flights")[0]["n"] == before


def test_saved_model_scores_uploaded_flights_into_the_risk_tables(tmp_path: Path) -> None:
    ops = write_ops(tmp_path)
    assert delay_risk.load_models(ops) is None  # nothing trained yet
    delay_risk.run(ops, default_mct=50)
    saved = delay_risk.load_models(ops)
    assert saved is not None
    assert set(saved[0].boosters) == set(delay_risk.THRESHOLDS)
    assert saved[2]["features"] == list(delay_risk.FEATURES)

    checked = sample_data.check(FLIGHTS, passengers(), set(), set())
    folder = tmp_path / "testdata"
    manifest = sample_data.save(folder, checked, "judge (EVALUATOR)", ops)
    assert manifest["risk"] == {"scored": 3, "connections": 3, "reason": None}

    store = OpsStore(ops, folder)
    risk = {r["flight_id"]: r for r in store.query("SELECT * FROM flight_risk WHERE flight_id LIKE 'G98%'")}
    assert set(risk) == {"G9801_202611220500", "G9851_202611220900", "G9853_202611230300"}
    first = risk["G9801_202611220500"]
    curve = [first[f"p_{t}"] for t in delay_risk.THRESHOLDS]
    assert curve == sorted(curve, reverse=True)  # monotone delay curve from the saved boosters
    assert first["connecting_pax"] == 3
    assert first["risk_band"] in {"low", "medium", "high"}
    links = store.query("SELECT * FROM connection_risk WHERE inbound_flight_id = 'G9801_202611220500'")
    assert len(links) == 3
    assert {row["outbound_flight_number"] for row in links} == {"G9851"}
    sample_data.clear(folder)
    assert not (folder / "flight_risk.parquet").exists()


def test_a_model_built_for_other_features_is_not_used(tmp_path: Path) -> None:
    ops = write_ops(tmp_path)
    delay_risk.run(ops, default_mct=50)
    meta = ops / delay_risk.MODEL_DIR / "meta.json"
    meta.write_text(meta.read_text().replace('"hour_local"', '"hour_other"'))
    assert delay_risk.load_models(ops) is None
    checked = sample_data.check(FLIGHTS, passengers(), set(), set())
    folder = tmp_path / "testdata"
    manifest = sample_data.save(folder, checked, "judge (EVALUATOR)", ops)
    assert manifest["risk"]["scored"] == 0
    assert manifest["risk"]["reason"] == "no saved model: run the ingest once"
    assert OpsStore(ops, folder).query("SELECT count(*) AS n FROM flights WHERE flight_id LIKE 'G98%'")[0]["n"] == 3


def test_upload_api_checks_then_adds_then_removes(client: TestClient, evaluator_auth: dict[str, str]) -> None:
    body = {"flights_csv": FLIGHTS, "passengers_csv": passengers(), "commit": False}
    assert client.post("/api/v1/test-data", json=body).status_code == 401
    assert client.get("/api/v1/test-data/spec", headers=evaluator_auth).json()["files"][0]["key"] == "flights"
    assert client.get("/api/v1/test-data", headers=evaluator_auth).json() == {"loaded": False}

    checked = client.post("/api/v1/test-data", json=body, headers=evaluator_auth).json()
    assert checked["ok"]
    assert not checked["committed"]
    assert checked["summary"]["flights"] == 3
    assert client.get("/api/v1/test-data", headers=evaluator_auth).json() == {
        "loaded": False
    }  # check only: nothing stored

    bad = client.post(
        "/api/v1/test-data", json={**body, "commit": True, "flights_csv": "x,y\n1,2\n"}, headers=evaluator_auth
    ).json()
    assert not bad["ok"]
    assert not bad["committed"]
    assert bad["errors"][0]["file"] == "flights.csv"

    added = client.post("/api/v1/test-data", json={**body, "commit": True}, headers=evaluator_auth).json()
    assert added["committed"]
    assert added["status"]["risk"]["scored"] == 3  # scored with the saved model, so the flights are in the risk views
    detail = client.get("/api/v1/risk/flights/G9801_202611220500", headers=evaluator_auth)
    assert detail.status_code == 200
    assert detail.json()["flight"]["connecting_pax"] == 3
    assert added["status"]["counts"] == {"flights": 3, "passenger_segments": 6, "passengers": 3}
    found = client.get("/api/v1/flights", params={"q": "G9801"}, headers=evaluator_auth).json()
    assert [f["flight_id"] for f in found] == ["G9801_202611220500"]
    assert found[0]["capacity_source"] == "judge-test-data"
    made = client.post(
        "/api/v1/scenarios",
        json={"kind": "DELAY", "flight_id": "G9801_202611220500", "delay_minutes": 150},
        headers=evaluator_auth,
    )
    assert made.status_code == 201
    assert made.json()["result"]["type"] == "DELAY"
    rewards = client.post(
        f"/api/v1/scenarios/{made.json()['id']}/rewards", json={"budget_aed": 2000}, headers=evaluator_auth
    )
    assert rewards.status_code == 200

    again = client.post("/api/v1/test-data", json={**body, "commit": True}, headers=evaluator_auth).json()
    assert again["committed"]  # the earlier test data is replaced, not reported as a clash

    assert client.delete("/api/v1/test-data", headers=evaluator_auth).json() == {"loaded": False}
    assert client.get("/api/v1/flights", params={"q": "G9801"}, headers=evaluator_auth).json() == []


def test_only_the_evaluator_role_reaches_the_test_data_and_model_views(
    client: TestClient, auth: dict[str, str], evaluator_auth: dict[str, str]
) -> None:
    occ = client.post("/api/v1/auth/login", json={"username": "occ", "password": "occ-pass"}).json()["token"]
    for headers in (auth, {"Authorization": f"Bearer {occ}"}):  # PCU and OCC
        assert client.get("/api/v1/test-data", headers=headers).status_code == 403
        assert client.get("/api/v1/test-data/spec", headers=headers).status_code == 403
        body = {"flights_csv": FLIGHTS, "passengers_csv": passengers(), "commit": True}
        assert client.post("/api/v1/test-data", json=body, headers=headers).status_code == 403
        assert client.delete("/api/v1/test-data", headers=headers).status_code == 403
        assert client.get("/api/v1/risk/model", headers=headers).status_code == 403
        assert client.get("/api/v1/meta", headers=headers).status_code == 200  # everything else is open to them
        assert client.get("/api/v1/risk/watchlist", headers=headers).status_code == 200
    assert client.get("/api/v1/risk/model", headers=evaluator_auth).status_code == 200
    assert client.get("/api/v1/meta", headers=evaluator_auth).json()["user"]["role"] == "EVALUATOR"
