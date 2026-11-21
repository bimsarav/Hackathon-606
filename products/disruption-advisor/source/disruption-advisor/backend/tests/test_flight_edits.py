"""Evaluator edits of existing flights: saved edits change what the analysis sees, reset restores the real flight."""

from pathlib import Path

from fastapi.testclient import TestClient

from app import flight_edits
from app.engine.store import OpsStore
from tests.ops_fixture import F1, X1, write_ops


def _edit_body(store: OpsStore, flight_id: str) -> dict:
    f = store.query("SELECT std, sta, tail, capacity, booked_seats FROM flights WHERE flight_id = ?", [flight_id])[0]
    pax = store.query(
        """SELECT p.customer_key, p.pnr, p.pax_type, p.fare_family_synthetic AS fare_family, p.fare, p.ssr_code AS ssr,
                  coalesce(c.loyalty_tier_synthetic, 'none') AS loyalty_tier,
                  coalesce(c.travel_frequency_band, 'unknown') AS frequency
           FROM pax_segments p LEFT JOIN customers c USING (customer_key) WHERE p.flight_id = ? ORDER BY p.pnr""",
        [flight_id],
    )
    return {
        "flight": {
            "std": f["std"].strftime("%H:%M"),
            "sta": f["sta"].strftime("%H:%M"),
            "tail": f["tail"],
            "capacity": f["capacity"],
            "booked_seats": f["booked_seats"],
        },
        "passengers": [
            {
                **p,
                "fare_family": p["fare_family"] or "Basic",
                "fare": float(p["fare"] or 0),
                "ssr": p["ssr"] or None,
                "remove": False,
            }
            for p in pax
        ],
    }


def test_saved_edits_are_applied_on_top_of_the_real_data(tmp_path: Path) -> None:
    ops = write_ops(tmp_path)
    folder = tmp_path / "testdata"
    store = OpsStore(ops, folder)
    body = _edit_body(store, X1)
    real_count = len(body["passengers"])
    assert real_count >= 2
    first = body["passengers"][0]
    first.update(loyalty_tier="Platinum", frequency="frequent", ssr="WCHR", fare=999.0)
    body["passengers"][1]["remove"] = True
    body["passengers"].append(
        {
            "customer_key": None,
            "pnr": "EVAL01",
            "pax_type": "AD",
            "fare_family": "Value",
            "fare": 400.0,
            "loyalty_tier": "Gold",
            "frequency": "regular",
            "ssr": None,
            "remove": False,
        }
    )
    body["flight"].update(capacity=200, booked_seats=200, tail="A6-EVL")
    flight_edits.write(folder, {X1: {**body, "saved_by": "t", "saved_at": "now"}})

    edited = OpsStore(ops, folder)
    assert edited.flights_edited == 1
    f = edited.query("SELECT tail, capacity, booked_seats, capacity_source FROM flights WHERE flight_id = ?", [X1])[0]
    assert f == {
        "tail": "A6-EVL",
        "capacity": 200,
        "booked_seats": 200,
        "capacity_source": "evaluator-edit",
    }
    pax = {p["customer_key"]: p for p in edited.passengers_on([X1])}
    assert len(pax) == real_count  # one removed, one added
    assert pax[first["customer_key"]]["loyalty_tier_synthetic"] == "Platinum"
    assert pax[first["customer_key"]]["ssr_code"] == "WCHR"
    assert body["passengers"][1]["customer_key"] not in pax
    assert any(p["pnr"] == "EVAL01" for p in pax.values())

    flight_edits.write(folder, {})  # reset everything: the real flight is back
    back = OpsStore(ops, folder)
    assert back.flights_edited == 0
    assert back.query("SELECT tail FROM flights WHERE flight_id = ?", [X1])[0]["tail"] != "A6-EVL"


def test_edit_api_changes_the_scenario_and_reset_restores_it(
    client: TestClient, auth: dict[str, str], evaluator_auth: dict[str, str]
) -> None:
    url = f"/api/v1/test-data/flights/{F1}"
    assert client.get(url, headers=auth).status_code == 403  # evaluator only
    view = client.get(url, headers=evaluator_auth).json()
    assert view["edited"] is False
    assert view["flight"]["std_hhmm"]

    def misses() -> int:
        made = client.post(
            "/api/v1/scenarios", headers=evaluator_auth, json={"kind": "DELAY", "flight_id": F1, "delay_minutes": 150}
        ).json()
        return len(made["result"]["misconnections"])

    before = misses()
    assert before > 0
    body = {
        "flight": {
            "std": view["flight"]["std_hhmm"],
            "sta": view["flight"]["sta_hhmm"],
            "tail": view["flight"]["tail"],
            "capacity": view["flight"]["capacity"],
            "booked_seats": view["flight"]["booked_seats"],
        },
        "passengers": [
            {
                "customer_key": p["customer_key"],
                "pnr": p["pnr"],
                "pax_type": p["pax_type"],
                "fare_family": p["fare_family"] or "Basic",
                "fare": float(p["fare"] or 0),
                "loyalty_tier": p["loyalty_tier"],
                "frequency": p["frequency"],
                "ssr": p["ssr"] or None,
                "remove": True,
            }
            for p in view["passengers"]
        ],  # everyone off the flight
    }
    bad = {**body, "flight": {**body["flight"], "booked_seats": body["flight"]["capacity"] + 1}}
    assert client.put(url, json=bad, headers=evaluator_auth).status_code == 422
    assert client.put(url, json=body, headers=evaluator_auth).json() == {"saved": True, "flight_id": F1}
    assert client.get(url, headers=evaluator_auth).json()["edited"] is True
    assert client.get("/api/v1/test-data/edits", headers=evaluator_auth).json()[0]["flight_id"] == F1
    assert misses() == 0  # nobody left to miss a connection

    assert client.delete(url, headers=evaluator_auth).json()["reset"] is True
    assert misses() == before
    assert client.get("/api/v1/test-data/flights/G9999_202611210000", headers=evaluator_auth).status_code == 404


def test_a_second_save_keeps_earlier_removals_and_added_passengers(
    client: TestClient, evaluator_auth: dict[str, str]
) -> None:
    url = f"/api/v1/test-data/flights/{F1}"

    def body(view: dict, remove: set[str], add: bool = False) -> dict:
        pax = [
            {
                "customer_key": p["customer_key"],
                "pnr": p["pnr"],
                "pax_type": p["pax_type"],
                "fare_family": p["fare_family"] or "Basic",
                "fare": float(p["fare"] or 0),
                "loyalty_tier": p["loyalty_tier"],
                "frequency": p["frequency"],
                "ssr": p["ssr"] or None,
                "remove": p["customer_key"] in remove,
            }
            for p in view["passengers"]
        ]
        if add:
            pax.append(
                {
                    "customer_key": None,
                    "pnr": "EVAL01",
                    "pax_type": "AD",
                    "fare_family": "Value",
                    "fare": 1.0,
                    "loyalty_tier": "none",
                    "frequency": "regular",
                    "ssr": None,
                    "remove": False,
                }
            )
        f = view["flight"]
        return {
            "flight": {
                "std": f["std_hhmm"],
                "sta": f["sta_hhmm"],
                "tail": f["tail"],
                "capacity": f["capacity"],
                "booked_seats": f["booked_seats"],
            },
            "passengers": pax,
        }

    real = client.get(url, headers=evaluator_auth).json()
    keys = [p["customer_key"] for p in real["passengers"]]
    assert len(keys) >= 2
    client.put(url, json=body(real, {keys[0]}, add=True), headers=evaluator_auth)
    first = client.get(url, headers=evaluator_auth).json()
    assert keys[0] not in {p["customer_key"] for p in first["passengers"]}
    assert any(p["pnr"] == "EVAL01" for p in first["passengers"])

    client.put(url, json=body(first, {keys[1]}), headers=evaluator_auth)  # the second save lists only what it sees
    second = {p["customer_key"]: p for p in client.get(url, headers=evaluator_auth).json()["passengers"]}
    assert keys[0] not in second
    assert keys[1] not in second
    assert sum(p["pnr"] == "EVAL01" for p in second.values()) == 1  # the added passenger is still there, once
    assert len(second) == len(keys) - 1
    client.delete(url, headers=evaluator_auth)
