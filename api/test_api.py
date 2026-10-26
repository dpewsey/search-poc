"""Tests for the CYS API.

Requires a running PostgreSQL with migrations and seed applied.
"""

import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from main import app, get_dsn

client = TestClient(app, raise_server_exceptions=True)
client.__enter__()  # trigger lifespan to init pool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dsn():
    return get_dsn()


def _db_available():
    try:
        with psycopg.connect(_dsn(), connect_timeout=3):
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(), reason="PostgreSQL not available"
)

TEST_EPISODE_IDS: list[str] = []


@pytest.fixture(autouse=True, scope="module")
def _seed_test_data():
    """Insert a test episode with transcript segments for search tests."""
    conn = psycopg.connect(_dsn())

    podcast = conn.execute(
        "SELECT id FROM podcasts WHERE slug = 'the-yard'"
    ).fetchone()
    if podcast is None:
        conn.close()
        pytest.skip("Seed data not present")
    podcast_id = podcast[0]

    episode_id = str(uuid.uuid4())
    TEST_EPISODE_IDS.append(episode_id)
    conn.execute(
        """
        INSERT INTO episodes (id, podcast_id, title, episode_number)
        VALUES (%s, %s, %s, %s)
        """,
        (episode_id, podcast_id, "TEST_api_episode", 999),
    )
    conn.execute(
        """
        INSERT INTO transcript_segments (episode_id, sequence, start_time, end_time, text)
        VALUES
            (%s, 0, 0.0, 5.0, 'Welcome to the podcast about basketball'),
            (%s, 1, 5.0, 10.0, 'Today we discuss the championship game'),
            (%s, 2, 10.0, 15.0, 'The final score was incredible')
        """,
        (episode_id, episode_id, episode_id),
    )
    conn.commit()

    yield

    conn.execute("DELETE FROM episodes WHERE id = %s", (episode_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@requires_db
class TestSearch:
    def test_search_existing_term(self):
        res = client.get("/api/search", params={"q": "basketball"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert any("basketball" in r["text"].lower() for r in data["results"])

    def test_search_no_results(self):
        res = client.get("/api/search", params={"q": "xylophone"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_empty_query(self):
        res = client.get("/api/search", params={"q": ""})
        assert res.status_code == 200
        data = res.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_search_result_shape(self):
        res = client.get("/api/search", params={"q": "championship"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["results"]) >= 1
        r = data["results"][0]
        for key in ["segment_id", "episode_id", "episode_title", "start_time", "end_time", "text", "rank"]:
            assert key in r


# ---------------------------------------------------------------------------
# Episodes list
# ---------------------------------------------------------------------------

@requires_db
class TestEpisodesList:
    def test_list_episodes(self):
        res = client.get("/api/episodes")
        assert res.status_code == 200
        data = res.json()
        assert "episodes" in data
        assert len(data["episodes"]) >= 1

    def test_episode_shape(self):
        res = client.get("/api/episodes")
        data = res.json()
        ep = data["episodes"][0]
        for key in ["id", "title", "episode_number", "description", "published_at", "duration_seconds"]:
            assert key in ep


# ---------------------------------------------------------------------------
# Episode detail
# ---------------------------------------------------------------------------

@requires_db
class TestEpisodeDetail:
    def test_get_episode(self):
        eid = TEST_EPISODE_IDS[0]
        res = client.get(f"/api/episodes/{eid}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == eid
        assert data["title"] == "TEST_api_episode"
        assert len(data["transcript"]) == 3

    def test_transcript_order(self):
        eid = TEST_EPISODE_IDS[0]
        res = client.get(f"/api/episodes/{eid}")
        data = res.json()
        sequences = [s["sequence"] for s in data["transcript"]]
        assert sequences == [0, 1, 2]

    def test_episode_not_found(self):
        fake_id = str(uuid.uuid4())
        res = client.get(f"/api/episodes/{fake_id}")
        assert res.status_code == 404
