"""CYS audio transcription tool.

Transcribes audio files using faster-whisper and optionally persists
transcript segments into the existing CYS PostgreSQL database.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import psycopg
from faster_whisper import WhisperModel

SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".aac", ".wma"}

log = logging.getLogger("cys-transcribe")


# ---------------------------------------------------------------------------
# Audio file validation
# ---------------------------------------------------------------------------

def validate_audio_file(path: str) -> Path:
    """Validate that the audio file exists and has a supported extension."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if p.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{p.suffix}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    return p


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe_audio(
    audio_path: Path,
    model_size: str,
    device: str,
    compute_type: str,
    language: str | None = None,
) -> tuple[list[dict], dict]:
    """Transcribe an audio file and return (segments, info).

    Returns a list of segment dicts and a metadata dict containing
    language and duration.
    """
    log.info("Loading model '%s' (device=%s, compute=%s)...", model_size, device, compute_type)
    t0 = time.time()
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    log.info("Model loaded in %.1fs", time.time() - t0)

    transcribe_kwargs: dict = {}
    if language:
        transcribe_kwargs["language"] = language

    log.info("Transcribing %s...", audio_path.name)
    t0 = time.time()
    whisper_segments, info = model.transcribe(str(audio_path), **transcribe_kwargs)

    segments: list[dict] = []
    for seg in whisper_segments:
        segments.append(
            {
                "sequence": len(segments),
                "start_time": round(seg.start, 3),
                "end_time": round(seg.end, 3),
                "text": seg.text.strip(),
            }
        )
        if len(segments) % 50 == 0:
            log.info("  ...%d segments processed", len(segments))

    elapsed = time.time() - t0
    duration = getattr(info, "duration", 0) or 0

    log.info("Transcription complete in %.1fs", elapsed)
    log.info("Audio duration: %.1fs", duration)
    log.info("Total segments: %d", len(segments))

    metadata = {
        "language": getattr(info, "language", language or "unknown"),
        "duration_seconds": round(duration, 1),
    }

    return segments, metadata


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(segments: list[dict], metadata: dict, output_path: str) -> None:
    """Write transcript segments to a JSON file."""
    payload = {
        "language": metadata["language"],
        "duration_seconds": metadata["duration_seconds"],
        "segments": segments,
    }
    Path(output_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info("JSON exported to %s", output_path)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db_dsn() -> str:
    """Build a PostgreSQL DSN from environment variables."""
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "cys")
    user = os.environ.get("POSTGRES_USER", "cys")
    password = os.environ.get("POSTGRES_PASSWORD", "cys_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def validate_episode(conn: psycopg.Connection, episode_id: str) -> None:
    """Check that the episode exists in the database."""
    row = conn.execute(
        "SELECT id FROM episodes WHERE id = %s", (episode_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Episode not found: {episode_id}")


def check_existing_segments(conn: psycopg.Connection, episode_id: str) -> int:
    """Return the count of existing transcript segments for an episode."""
    row = conn.execute(
        "SELECT COUNT(*) FROM transcript_segments WHERE episode_id = %s",
        (episode_id,),
    ).fetchone()
    return row[0] if row else 0


def save_segments(
    conn: psycopg.Connection,
    episode_id: str,
    segments: list[dict],
    replace: bool = False,
) -> None:
    """Persist transcript segments to PostgreSQL in a transaction."""
    existing = check_existing_segments(conn, episode_id)

    if existing > 0 and not replace:
        raise RuntimeError(
            f"Episode {episode_id} already has {existing} transcript segments. "
            "Use --replace to overwrite."
        )

    with conn.transaction():
        if existing > 0 and replace:
            conn.execute(
                "DELETE FROM transcript_segments WHERE episode_id = %s",
                (episode_id,),
            )
            log.info("Deleted %d existing segments", existing)

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO transcript_segments (episode_id, sequence, start_time, end_time, text)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (episode_id, s["sequence"], s["start_time"], s["end_time"], s["text"])
                    for s in segments
                ],
            )
        log.info("Inserted %d segments for episode %s", len(segments), episode_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CYS audio transcription tool",
    )
    parser.add_argument(
        "--input", required=True, help="Path to audio file"
    )
    parser.add_argument(
        "--episode-id",
        default=None,
        help="Episode UUID (required for database import)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WHISPER_MODEL", "small"),
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--language",
        default=os.environ.get("WHISPER_LANGUAGE"),
        help="Language override (e.g. en)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to export transcript as JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Transcribe without writing to PostgreSQL",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing transcript segments for the episode",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    args = parse_args(argv)

    # Validate audio file
    audio_path = validate_audio_file(args.input)

    # DB writes require an episode ID
    if not args.dry_run and not args.episode_id:
        log.error("--episode-id is required when writing to the database. Use --dry-run to skip DB writes.")
        sys.exit(1)

    # Transcribe
    device = os.environ.get("WHISPER_DEVICE", "cpu")
    compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

    segments, metadata = transcribe_audio(
        audio_path,
        model_size=args.model,
        device=device,
        compute_type=compute_type,
        language=args.language,
    )

    if not segments:
        log.warning("No segments were generated")
        sys.exit(0)

    # JSON export
    if args.output:
        export_json(segments, metadata, args.output)

    # Database persistence
    if args.dry_run:
        log.info("Dry run - skipping database writes")
        return

    dsn = get_db_dsn()
    log.info("Connecting to database...")
    with psycopg.connect(dsn) as conn:
        validate_episode(conn, args.episode_id)
        save_segments(conn, args.episode_id, segments, replace=args.replace)

    log.info("Done.")


if __name__ == "__main__":
    main()
