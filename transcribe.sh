#!/usr/bin/env bash
set -euo pipefail

# CYS transcription helper
# Usage:
#   ./transcribe.sh <audio-file> <episode-title> [episode-number]
#   ./transcribe.sh transcription/audio/yard-272.mp3 "The One About Nothing" 272
#
# Creates the episode record and runs transcription in one step.

if [ $# -lt 2 ]; then
    echo "Usage: $0 <audio-file> <episode-title> [episode-number]"
    echo ""
    echo "Examples:"
    echo "  $0 transcription/audio/yard-272.mp3 \"The One About Nothing\" 272"
    echo "  $0 transcription/audio/yard-272.mp3 \"The One About Nothing\""
    exit 1
fi

AUDIO_FILE="$1"
EPISODE_TITLE="$2"
EPISODE_NUMBER="${3:-}"

# Check audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: Audio file not found: $AUDIO_FILE"
    echo "Place audio files in transcription/audio/"
    exit 1
fi

# Derive the container path (/audio/filename)
AUDIO_FILENAME="$(basename "$AUDIO_FILE")"
CONTAINER_AUDIO_PATH="/audio/$AUDIO_FILENAME"

# Load env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DB_USER="${POSTGRES_USER:-cys}"
DB_NAME="${POSTGRES_DB:-cys}"
export PGPASSWORD="${POSTGRES_PASSWORD:-cys_dev}"

PSQL="docker compose exec -T db psql -U $DB_USER -d $DB_NAME -t -A"

# Get podcast ID
PODCAST_ID=$($PSQL -c "SELECT id FROM podcasts WHERE slug = 'the-yard'" | tr -d '[:space:]')
if [ -z "$PODCAST_ID" ]; then
    echo "Error: 'the-yard' podcast not found. Run ./database/seed.sh first."
    exit 1
fi

# Check if episode already exists (by title)
EXISTING_ID=$($PSQL -c "SELECT id FROM episodes WHERE title = '$EPISODE_TITLE' AND podcast_id = '$PODCAST_ID'" | tr -d '[:space:]')

if [ -n "$EXISTING_ID" ]; then
    echo "Episode already exists: $EPISODE_TITLE"
    echo "Episode ID: $EXISTING_ID"
    EPISODE_ID="$EXISTING_ID"

    # Check for existing segments
    SEG_COUNT=$($PSQL -c "SELECT COUNT(*) FROM transcript_segments WHERE episode_id = '$EPISODE_ID'" | tr -d '[:space:]')
    if [ "$SEG_COUNT" -gt 0 ]; then
        echo "Episode already has $SEG_COUNT transcript segments."
        read -p "Replace them? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
        REPLACE_FLAG="--replace"
    else
        REPLACE_FLAG=""
    fi
else
    # Insert episode
    if [ -n "$EPISODE_NUMBER" ]; then
        EPISODE_ID=$($PSQL -c "INSERT INTO episodes (podcast_id, title, episode_number) VALUES ('$PODCAST_ID', '$EPISODE_TITLE', $EPISODE_NUMBER) RETURNING id" | tr -d '[:space:]')
    else
        EPISODE_ID=$($PSQL -c "INSERT INTO episodes (podcast_id, title) VALUES ('$PODCAST_ID', '$EPISODE_TITLE') RETURNING id" | tr -d '[:space:]')
    fi
    echo "Created episode: $EPISODE_TITLE"
    echo "Episode ID: $EPISODE_ID"
    REPLACE_FLAG=""
fi

echo ""
echo "Starting transcription..."
echo "Audio: $AUDIO_FILENAME"
echo "Model: ${WHISPER_MODEL:-small}"
echo ""

docker compose run --rm transcription \
    python transcribe.py \
    --input "$CONTAINER_AUDIO_PATH" \
    --episode-id "$EPISODE_ID" \
    --output "/audio/${AUDIO_FILENAME%.*}.json" \
    $REPLACE_FLAG
