CREATE TABLE IF NOT EXISTS transcript_segments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id    UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    sequence      INTEGER NOT NULL,
    start_time    DOUBLE PRECISION NOT NULL,
    end_time      DOUBLE PRECISION NOT NULL,
    text          TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_sequence_non_negative CHECK (sequence >= 0),
    CONSTRAINT chk_start_time_non_negative CHECK (start_time >= 0),
    CONSTRAINT chk_end_time_gte_start_time CHECK (end_time >= start_time),
    CONSTRAINT uq_episode_sequence UNIQUE (episode_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_transcript_segments_episode_sequence
    ON transcript_segments(episode_id, sequence);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_search_vector
    ON transcript_segments USING GIN(search_vector);
