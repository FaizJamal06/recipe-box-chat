"""API (PRD 7) on the fixture DB: chat shape + post-check, sticky refine + trace, chip PATCH re-run, recipe by id,
rate limit, reset, health, and the reply-ID post-check itself."""
import pytest
from fastapi.testclient import TestClient

from app import api, web


@pytest.fixture
def client(mini, monkeypatch):
    """A TestClient over the fixture DB with fresh sessions."""
    monkeypatch.setattr(api, "DB", mini[0])
    monkeypatch.setattr(api, "SESSIONS", {})
    with TestClient(api.app) as c:
        yield c


def ids_in(md: str) -> set[str]:
    return set(web.ID_RX.findall(md))


def test_chat_shape_postcheck_and_sticky_refine(client):
    r = client.post("/api/chat", json={"message": "Find a rice recipe"}).json()
    assert set(r) == {"session_id", "reply_md", "voice", "payload", "state", "trace", "planner", "suggestions"}
    assert r["voice"] is None and 2 <= len(r["suggestions"]) <= 3  # no LLM in tests: template only
    assert r["planner"]["kind"] == "rule" and r["payload"]["type"] == "search"
    assert ids_in(r["reply_md"]) <= {c["id"] for c in r["payload"]["cards"]} and ids_in(r["reply_md"])
    assert r["payload"]["calc"][0]["sql"].startswith("SELECT") and r["payload"]["postcheck"]["stripped"] == []
    sid, before = r["session_id"], r["payload"]["total"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "I cannot have dairy"}).json()
    assert r["state"]["exclude_tags"] == ["dairy"] and r["planner"]["detail"] == "rule_direct"
    assert any(t.startswith(f"Filtered: {before} → ") for t in r["trace"])
    assert all(any(ch["label"] == "no dairy" for ch in c["chips"]) for c in r["payload"]["cards"])


def test_patch_removes_chip_and_reruns(client):
    sid = client.post("/api/chat", json={"message": "Find a rice recipe"}).json()["session_id"]
    client.post("/api/chat", json={"session_id": sid, "message": "I cannot have dairy"})
    r = client.patch(f"/api/session/{sid}/state", json={"op": "remove", "field": "exclude_tags", "value": "dairy"})
    assert r.status_code == 200 and r.json()["state"]["exclude_tags"] == [] and r.json()["planner"]["kind"] == "ui"
    assert "fn:f04" in {c["id"] for c in r.json()["payload"]["cards"]}  # the buttery rice recipe is back
    r = client.patch(f"/api/session/{sid}/state", json={"op": "set", "field": "strict_may_contain", "value": True})
    assert r.json()["state"]["strict_may_contain"] is True
    assert client.patch(f"/api/session/{sid}/state", json={"op": "remove", "field": "exclude", "value": "x"}).status_code == 400
    assert client.patch("/api/session/nope/state", json={"op": "set", "field": "staples", "value": False}).status_code == 404


def test_recipe_detail_and_get_recipe(client):
    sid = client.post("/api/chat", json={"message": "Find a rice recipe"}).json()["session_id"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "show me the first one"}).json()
    rec = r["payload"]["recipe"]
    assert r["payload"]["type"] == "recipe" and rec["steps"] and rec["ingredients"]
    got = client.get("/api/recipe/" + rec["id"].replace(":", "%3A"))
    assert got.status_code == 200 and got.json()["title"] == rec["title"] and got.json()["parsed"]
    assert client.get("/api/recipe/ar%3Anope").status_code == 404


def test_unsupported_reply_ids_are_in_payload(client):
    sid = client.post("/api/chat", json={"message": "Find a rice recipe"}).json()["session_id"]
    client.post("/api/chat", json={"session_id": sid, "message": "show me the first one"})
    r = client.post("/api/chat", json={"session_id": sid, "message": "How many calories are in that one?"}).json()
    assert r["planner"]["kind"] == "guard" and "no nutrition fields" in r["reply_md"]
    assert ids_in(r["reply_md"]) and ids_in(r["reply_md"]) <= {c["id"] for c in r["payload"]["cards"]}


def test_rate_limit_reset_and_health(client):
    sid = client.post("/api/chat", json={"message": "hello"}).json()["session_id"]
    codes = [client.post("/api/chat", json={"session_id": sid, "message": "hello"}).status_code for _ in range(10)]
    assert codes[:9] == [200] * 9 and codes[9] == 429
    assert client.post(f"/api/session/{sid}/reset").json()["state"]["active_task"] is None
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["valid"] == 23 and h["llm"]["status"] == "not configured"


def test_postcheck_strips_ids_missing_from_payload():
    payload = {"cards": [{"id": "ar:a01"}]}
    md = web.postcheck("see `ar:a01` and `fn:made-up`", payload)
    assert "`ar:a01`" in md and "fn:made-up" not in md and payload["postcheck"]["stripped"] == ["fn:made-up"]
