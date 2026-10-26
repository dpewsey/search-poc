"""CYS API - FastAPI backend for Community Yard Search."""

import os
from contextlib import asynccontextmanager

import psycopg
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, HTTPException, Query


def get_dsn() -> str:
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "cys")
    user = os.environ.get("POSTGRES_USER", "cys")
    password = os.environ.get("POSTGRES_PASSWORD", "cys_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = ConnectionPool(get_dsn(), min_size=2, max_size=10)
    yield
    pool.close()


app = FastAPI(title="CYS API", lifespan=lifespan)


def get_conn():
    return pool.connection()


# ──────────────────────────────────────────────
# GET /api/search
# ──────────────────────────────────────────────

@app.get("/api/search")
def search(
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if not q.strip():
        return {"results": [], "total": 0, "query": q}

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                ts.id AS segment_id,
                ts.episode_id,
                e.title AS episode_title,
                e.episode_number,
                e.published_at,
                ts.sequence,
                ts.start_time,
                ts.end_time,
                ts.text,
                ts_rank(ts.search_vector, websearch_to_tsquery('english', %(q)s)) AS rank
            FROM transcript_segments ts
            JOIN episodes e ON e.id = ts.episode_id
            WHERE ts.search_vector @@ websearch_to_tsquery('english', %(q)s)
            ORDER BY rank DESC, ts.start_time
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"q": q, "limit": limit, "offset": offset},
        ).fetchall()

        total_row = conn.execute(
            """
            SELECT COUNT(*)
            FROM transcript_segments
            WHERE search_vector @@ websearch_to_tsquery('english', %(q)s)
            """,
            {"q": q},
        ).fetchone()

    results = []
    for row in rows:
        results.append({
            "segment_id": str(row[0]),
            "episode_id": str(row[1]),
            "episode_title": row[2],
            "episode_number": row[3],
            "published_at": row[4].isoformat() if row[4] else None,
            "sequence": row[5],
            "start_time": row[6],
            "end_time": row[7],
            "text": row[8],
            "rank": float(row[9]),
        })

    return {
        "results": results,
        "total": total_row[0] if total_row else 0,
        "query": q,
    }


# ──────────────────────────────────────────────
# GET /api/episodes
# ──────────────────────────────────────────────

@app.get("/api/episodes")
def list_episodes():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, episode_number, description,
                   published_at, duration_seconds, artwork_url
            FROM episodes
            ORDER BY published_at DESC NULLS LAST
            """
        ).fetchall()

    episodes = []
    for row in rows:
        episodes.append({
            "id": str(row[0]),
            "title": row[1],
            "episode_number": row[2],
            "description": row[3],
            "published_at": row[4].isoformat() if row[4] else None,
            "duration_seconds": row[5],
            "artwork_url": row[6],
        })

    return {"episodes": episodes}


# ──────────────────────────────────────────────
# GET /api/episodes/{episode_id}
# ──────────────────────────────────────────────

@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: str):
    try:
        import uuid as _uuid
        _uuid.UUID(episode_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Episode not found")

    with get_conn() as conn:
        ep = conn.execute(
            """
            SELECT id, title, episode_number, description,
                   published_at, duration_seconds, artwork_url, original_url
            FROM episodes
            WHERE id = %s
            """,
            (episode_id,),
        ).fetchone()

        if ep is None:
            raise HTTPException(status_code=404, detail="Episode not found")

        segments = conn.execute(
            """
            SELECT id, sequence, start_time, end_time, text
            FROM transcript_segments
            WHERE episode_id = %s
            ORDER BY sequence
            """,
            (episode_id,),
        ).fetchall()

    return {
        "id": str(ep[0]),
        "title": ep[1],
        "episode_number": ep[2],
        "description": ep[3],
        "published_at": ep[4].isoformat() if ep[4] else None,
        "duration_seconds": ep[5],
        "artwork_url": ep[6],
        "original_url": ep[7],
        "transcript": [
            {
                "id": str(s[0]),
                "sequence": s[1],
                "start_time": s[2],
                "end_time": s[3],
                "text": s[4],
            }
            for s in segments
        ],
    }
