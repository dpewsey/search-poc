# CYS - Community Yard Search

A searchable knowledge archive for The Yard podcast. Search conversations, quotes and moments across transcribed episodes.

This is a proof of concept.

## What it does

- Full-text search across podcast transcripts using PostgreSQL.
- Episode archive with timestamped transcript segments.
- Search result navigation directly to the matching transcript moment.
- Local audio transcription using faster-whisper (CPU, no GPU required).

## Technology

| Component | Stack |
|-----------|-------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| API | Python, FastAPI |
| Database | PostgreSQL 17 |
| Transcription | Python, faster-whisper (Whisper small model, INT8) |
| Infrastructure | Docker Compose |

## Prerequisites

- Docker and Docker Compose
- `psql` client (for running migrations and seeds)

## Quick start

```bash
cd poc

# 1. Configure environment
cp .env.example .env

# 2. Start services
docker compose up -d

# 3. Wait for the database to be healthy
docker compose ps

# 4. Run migrations and seed
./database/migrate.sh
./database/seed.sh

# 5. Build the transcription image
docker compose build transcription
```

- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000
- **PostgreSQL:** localhost:5432

## Environment configuration

All settings are in `.env`. Defaults work out of the box for local development.

```env
# Database
POSTGRES_DB=cys
POSTGRES_USER=cys
POSTGRES_PASSWORD=cys_dev
POSTGRES_PORT=5432

# Transcription
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=en
```

## Database

### Run migrations

```bash
./database/migrate.sh
```

Tracked in a `schema_migrations` table. Idempotent - safe to run repeatedly.

### Seed data

```bash
./database/seed.sh
```

Creates The Yard podcast record. Safe to run repeatedly.

### Connect

```bash
psql -h localhost -p 5432 -U cys -d cys
# password: cys_dev
```

Or: `docker compose exec db psql -U cys -d cys`

### Reset

```bash
docker compose down -v
docker compose up -d
# wait for db healthy
./database/migrate.sh
./database/seed.sh
```

## Transcribing an episode

Audio files are a local input to the archive. CYS does not host or play audio.

### 1. Place the audio file

Copy an MP3 (or WAV, M4A, FLAC, OGG) into `transcription/audio/`.

### 2. Run the helper script

```bash
./transcribe.sh transcription/audio/episode.mp3 "Episode Title" 123
```

This creates the episode record in the database and runs transcription. The Whisper model is downloaded on first run and cached in a Docker volume.

### 3. Verify

```bash
curl -s http://localhost:8000/api/episodes | python3 -m json.tool
```

The episode should appear in the list. Open http://localhost:5173 and search for a word from the episode.

### Manual transcription

```bash
# Create an episode record
docker compose exec db psql -U cys -d cys \
  -c "INSERT INTO episodes (podcast_id, title, episode_number)
      VALUES ('<podcast-id>', 'Episode Title', 1)
      RETURNING id;"

# Transcribe
docker compose run --rm transcription \
  python transcribe.py \
  --input /audio/episode.mp3 \
  --episode-id <episode-uuid>
```

### Dry run (transcribe without saving to database)

```bash
docker compose run --rm transcription \
  python transcribe.py \
  --input /audio/episode.mp3 \
  --dry-run \
  --output /audio/transcript.json
```

### Replace an existing transcript

```bash
docker compose run --rm transcription \
  python transcribe.py \
  --input /audio/episode.mp3 \
  --episode-id <episode-uuid> \
  --replace
```

### Whisper model configuration

| Variable | Default | Options |
|----------|---------|---------|
| `WHISPER_MODEL` | small | tiny, base, small, medium, large-v3 |
| `WHISPER_DEVICE` | cpu | cpu, cuda |
| `WHISPER_COMPUTE_TYPE` | int8 | int8, float16, float32 |
| `WHISPER_LANGUAGE` | en | Any language code |

## Searching

Open http://localhost:5173 and type a search query.

Search uses PostgreSQL full-text search (`websearch_to_tsquery`):
- Single words: `hat`
- Multiple words (AND): `dog medicine`
- Exact phrases: `"dog medicine"`
- Exclusions: `dog -cat`

Click a search result to navigate directly to the matching transcript segment.

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/search?q=word&limit=20&offset=0` | Full-text search |
| `GET /api/episodes` | List all episodes |
| `GET /api/episodes/{id}` | Episode detail with transcript |

Example:

```bash
curl "http://localhost:8000/api/search?q=hat"
```

## Running tests

```bash
# API tests
docker compose exec api python -m pytest test_api.py -v

# Transcription tests
docker compose run --rm --entrypoint python transcription -m pytest test_transcribe.py -v
```

## Troubleshooting

**Services won't start**

Check Docker is running and ports 5173, 8000, 5432 are free.

```bash
docker compose logs
```

**Migrations fail**

Ensure the database is healthy before running migrations:

```bash
docker compose ps  # db should show "healthy"
```

**Search returns no results**

Check the episode has been transcribed:

```bash
curl -s "http://localhost:8000/api/episodes" | python3 -m json.tool
curl -s "http://localhost:8000/api/episodes/<id>" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['transcript']), 'segments')"
```

Common stop words (the, a, is, it) are ignored by PostgreSQL full-text search.

**Transcription fails with PyAV error**

Rebuild the image: `docker compose build transcription`

**Frontend shows "Failed to load" errors**

Check the API is running: `curl http://localhost:8000/api/episodes`

The frontend proxies `/api` requests to the API container. If the API is down, all data pages will fail.

**Data is missing after restart**

Data persists in the `pgdata` Docker volume. It is only lost if you run `docker compose down -v` (which removes volumes).

## Project structure

```
poc/
├── docker-compose.yml
├── .env / .env.example
├── transcribe.sh            # helper: create episode + transcribe
├── database/
│   ├── migrations/          # SQL schema migrations
│   ├── seed.sql / seed.sh   # initial podcast record
│   └── migrate.sh           # migration runner
├── api/
│   ├── Dockerfile
│   ├── main.py              # FastAPI endpoints
│   ├── test_api.py
│   └── requirements.txt
├── transcription/
│   ├── Dockerfile
│   ├── transcribe.py        # faster-whisper transcription CLI
│   ├── test_transcribe.py
│   ├── requirements.txt
│   └── audio/               # mount point for audio files (gitignored)
└── frontend/
    ├── src/
    │   ├── api.ts            # API client
    │   ├── types.ts
    │   ├── pages/            # HomePage, SearchResultsPage, EpisodePage, EpisodesPage
    │   └── components/       # Header, SearchBar, Logo, HighlightedText
    ├── vite.config.ts        # dev server + API proxy
    └── index.html
```
