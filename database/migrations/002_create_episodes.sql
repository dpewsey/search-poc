CREATE TABLE IF NOT EXISTS episodes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    podcast_id       UUID NOT NULL REFERENCES podcasts(id),
    title            VARCHAR(500) NOT NULL,
    episode_number   INTEGER,
    description      TEXT,
    published_at     TIMESTAMPTZ,
    duration_seconds INTEGER,
    original_url     TEXT,
    artwork_url      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_podcast_id ON episodes(podcast_id);
CREATE INDEX IF NOT EXISTS idx_episodes_published_at ON episodes(published_at);
