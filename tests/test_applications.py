from datetime import date

from app.domain import Status, allowed_next, can_transition
from conftest import make_app


# ---- domain rules ---------------------------------------------------------

def test_transition_rules():
    assert can_transition(Status.WISHLIST, Status.APPLIED)
    assert not can_transition(Status.WISHLIST, Status.OFFER)
    assert not can_transition(Status.REJECTED, Status.APPLIED)
    assert allowed_next(Status.ACCEPTED) == []
    assert Status.OFFER in allowed_next(Status.INTERVIEW)


# ---- create / read --------------------------------------------------------

def test_create_and_get(client, auth):
    created = make_app(client, auth, company="  Acme  ", location="Remote", salary_min=100, salary_max=200)
    assert created["status"] == "wishlist" and created["company"] == "Acme"
    resp = client.get(f"/applications/{created['id']}", headers=auth)
    assert resp.status_code == 200 and resp.json()["location"] == "Remote"


def test_create_validation(client, auth):
    bad = [
        {"company": "", "role": "x"},
        {"company": "A", "role": "x", "salary_min": 200, "salary_max": 100},
        {"company": "A", "role": "x", "salary_min": -1},
        {"role": "x"},
    ]
    for body in bad:
        assert client.post("/applications", json=body, headers=auth).status_code == 422, body


# ---- list / filter / paginate --------------------------------------------

def test_list_filter_search_and_pagination(client, auth):
    for i in range(5):
        make_app(client, auth, company=f"Company{i}", role="Backend Engineer")
    target = make_app(client, auth, company="Globex", role="Data Analyst", notes="great 100% remote team")
    client.post(f"/applications/{target['id']}/status", json={"status": "applied"}, headers=auth)

    page = client.get("/applications?limit=4&offset=0", headers=auth).json()
    assert page["total"] == 6 and len(page["items"]) == 4
    rest = client.get("/applications?limit=4&offset=4", headers=auth).json()
    assert len(rest["items"]) == 2

    assert client.get("/applications?status=applied", headers=auth).json()["total"] == 1
    assert client.get("/applications?q=analyst", headers=auth).json()["total"] == 1
    assert client.get("/applications?q=100%25", headers=auth).json()["total"] == 1   # literal %
    assert client.get("/applications?q=%25", headers=auth).json()["total"] == 1      # not a wildcard
    assert client.get("/applications?limit=0", headers=auth).status_code == 422
    assert client.get("/applications?status=bogus", headers=auth).status_code == 422


# ---- ownership isolation --------------------------------------------------

def test_users_cannot_see_or_modify_each_others_data(client, auth, other_auth):
    mine = make_app(client, auth)
    url = f"/applications/{mine['id']}"
    assert client.get(url, headers=other_auth).status_code == 404
    assert client.patch(url, json={"company": "Hacked"}, headers=other_auth).status_code == 404
    assert client.post(f"{url}/status", json={"status": "applied"}, headers=other_auth).status_code == 404
    assert client.delete(url, headers=other_auth).status_code == 404
    assert client.get("/applications", headers=other_auth).json()["total"] == 0
    assert client.get(url, headers=auth).json()["company"] == "Acme"


# ---- update ---------------------------------------------------------------

def test_partial_update(client, auth):
    created = make_app(client, auth, location="NYC", salary_min=100, salary_max=200)
    url = f"/applications/{created['id']}"
    resp = client.patch(url, json={"role": "Senior Data Engineer"}, headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "Senior Data Engineer" and body["location"] == "NYC" and body["salary_max"] == 200
    assert client.patch(url, json={"location": None}, headers=auth).json()["location"] is None


def test_update_rejects_bad_values(client, auth):
    created = make_app(client, auth, salary_min=100, salary_max=200)
    url = f"/applications/{created['id']}"
    assert client.patch(url, json={"company": None}, headers=auth).status_code == 422
    assert client.patch(url, json={"salary_min": 500}, headers=auth).status_code == 422  # > stored max
    assert client.patch(url, json={"salary_max": 50}, headers=auth).status_code == 422   # < stored min


# ---- status workflow ------------------------------------------------------

def test_status_workflow_and_applied_date(client, auth):
    created = make_app(client, auth)
    url = f"/applications/{created['id']}/status"

    assert client.post(url, json={"status": "applied"}, headers=auth).json()["applied_on"] == date.today().isoformat()
    assert client.post(url, json={"status": "interview"}, headers=auth).json()["status"] == "interview"
    assert client.post(url, json={"status": "offer"}, headers=auth).status_code == 200
    final = client.post(url, json={"status": "accepted"}, headers=auth)
    assert final.status_code == 200 and final.json()["status"] == "accepted"


def test_invalid_transitions_return_409_with_guidance(client, auth):
    created = make_app(client, auth)
    url = f"/applications/{created['id']}/status"
    resp = client.post(url, json={"status": "offer"}, headers=auth)
    assert resp.status_code == 409 and "applied" in resp.json()["detail"]

    client.post(url, json={"status": "withdrawn"}, headers=auth)
    resp = client.post(url, json={"status": "applied"}, headers=auth)
    assert resp.status_code == 409 and "final state" in resp.json()["detail"]
    assert client.post(url, json={"status": "nonsense"}, headers=auth).status_code == 422


# ---- delete ---------------------------------------------------------------

def test_delete(client, auth):
    created = make_app(client, auth)
    url = f"/applications/{created['id']}"
    assert client.delete(url, headers=auth).status_code == 204
    assert client.get(url, headers=auth).status_code == 404
    assert client.delete(url, headers=auth).status_code == 404


# ---- stats ----------------------------------------------------------------

def test_stats(client, auth, other_auth):
    empty = client.get("/stats", headers=auth).json()
    assert empty["total"] == 0 and empty["response_rate"] == 0.0

    make_app(client, auth, company="wish")                      # wishlist
    ids = [make_app(client, auth, company=f"c{i}")["id"] for i in range(4)]
    for app_id in ids:
        client.post(f"/applications/{app_id}/status", json={"status": "applied"}, headers=auth)
    client.post(f"/applications/{ids[0]}/status", json={"status": "interview"}, headers=auth)
    client.post(f"/applications/{ids[1]}/status", json={"status": "rejected"}, headers=auth)
    make_app(client, other_auth, company="not mine")

    stats = client.get("/stats", headers=auth).json()
    assert stats["total"] == 5 and stats["submitted"] == 4
    assert stats["by_status"]["applied"] == 2 and stats["by_status"]["interview"] == 1
    assert stats["response_rate"] == 50.0    # interview + rejected of 4 submitted
    assert stats["interview_rate"] == 25.0
