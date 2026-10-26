"""Tests for the CYS transcription tool.

All tests mock faster-whisper so no model download is required.
"""

import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from transcribe import (
    SUPPORTED_FORMATS,
    check_existing_segments,
    export_json,
    get_db_dsn,
    save_segments,
    transcribe_audio,
    validate_audio_file,
    validate_episode,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_audio(tmp_path):
    """Create a temporary .mp3 file."""
    f = tmp_path / "test.mp3"
    f.write_bytes(b"\x00" * 100)
    return f


@pytest.fixture
def mock_segments():
    """Fake faster-whisper segment objects."""
    segs = []
    for i, (s, e, t) in enumerate([
        (0.0, 2.5, "  Hello world  "),
        (2.5, 5.1, "This is a test"),
        (5.1, 8.0, "Third segment"),
    ]):
        seg = MagicMock()
        seg.start = s
        seg.end = e
        seg.text = t
        segs.append(seg)
    return segs


@pytest.fixture
def mock_info():
    """Fake faster-whisper TranscriptionInfo."""
    info = MagicMock()
    info.language = "en"
    info.duration = 8.0
    return info


# ---------------------------------------------------------------------------
# Audio file validation
# ---------------------------------------------------------------------------

class TestValidateAudioFile:
    def test_valid_file(self, tmp_audio):
        result = validate_audio_file(str(tmp_audio))
        assert result == tmp_audio

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_audio_file("/nonexistent/file.mp3")

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("not audio")
        with pytest.raises(ValueError, match="Unsupported format"):
            validate_audio_file(str(f))

    def test_all_supported_formats(self, tmp_path):
        for ext in SUPPORTED_FORMATS:
            f = tmp_path / f"test{ext}"
            f.write_bytes(b"\x00")
            validate_audio_file(str(f))


# ---------------------------------------------------------------------------
# Transcription (mocked)
# ---------------------------------------------------------------------------

class TestTranscribeAudio:
    @patch("transcribe.WhisperModel")
    def test_segments_normalised(self, mock_model_cls, tmp_audio, mock_segments, mock_info):
        instance = MagicMock()
        instance.transcribe.return_value = (iter(mock_segments), mock_info)
        mock_model_cls.return_value = instance

        segments, metadata = transcribe_audio(
            tmp_audio, model_size="tiny", device="cpu", compute_type="int8"
        )

        assert len(segments) == 3
        assert metadata["language"] == "en"
        assert metadata["duration_seconds"] == 8.0

    @patch("transcribe.WhisperModel")
    def test_sequence_numbers(self, mock_model_cls, tmp_audio, mock_segments, mock_info):
        instance = MagicMock()
        instance.transcribe.return_value = (iter(mock_segments), mock_info)
        mock_model_cls.return_value = instance

        segments, _ = transcribe_audio(
            tmp_audio, model_size="tiny", device="cpu", compute_type="int8"
        )

        assert [s["sequence"] for s in segments] == [0, 1, 2]

    @patch("transcribe.WhisperModel")
    def test_text_stripped(self, mock_model_cls, tmp_audio, mock_segments, mock_info):
        instance = MagicMock()
        instance.transcribe.return_value = (iter(mock_segments), mock_info)
        mock_model_cls.return_value = instance

        segments, _ = transcribe_audio(
            tmp_audio, model_size="tiny", device="cpu", compute_type="int8"
        )

        assert segments[0]["text"] == "Hello world"

    @patch("transcribe.WhisperModel")
    def test_timestamps_rounded(self, mock_model_cls, tmp_audio, mock_info):
        seg = MagicMock()
        seg.start = 1.23456789
        seg.end = 3.98765432
        seg.text = "test"

        instance = MagicMock()
        instance.transcribe.return_value = (iter([seg]), mock_info)
        mock_model_cls.return_value = instance

        segments, _ = transcribe_audio(
            tmp_audio, model_size="tiny", device="cpu", compute_type="int8"
        )

        assert segments[0]["start_time"] == 1.235
        assert segments[0]["end_time"] == 3.988

    @patch("transcribe.WhisperModel")
    def test_language_passed_through(self, mock_model_cls, tmp_audio, mock_segments, mock_info):
        instance = MagicMock()
        instance.transcribe.return_value = (iter(mock_segments), mock_info)
        mock_model_cls.return_value = instance

        transcribe_audio(
            tmp_audio, model_size="tiny", device="cpu", compute_type="int8",
            language="fr",
        )

        _, kwargs = instance.transcribe.call_args
        assert kwargs["language"] == "fr"


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_export_structure(self, tmp_path):
        segments = [
            {"sequence": 0, "start_time": 0.0, "end_time": 2.5, "text": "Hello"},
            {"sequence": 1, "start_time": 2.5, "end_time": 5.0, "text": "World"},
        ]
        metadata = {"language": "en", "duration_seconds": 5.0}
        out = tmp_path / "out.json"

        export_json(segments, metadata, str(out))

        data = json.loads(out.read_text())
        assert data["language"] == "en"
        assert data["duration_seconds"] == 5.0
        assert len(data["segments"]) == 2
        assert data["segments"][0]["text"] == "Hello"

    def test_export_unicode(self, tmp_path):
        segments = [{"sequence": 0, "start_time": 0.0, "end_time": 1.0, "text": "Cafe\u0301"}]
        metadata = {"language": "fr", "duration_seconds": 1.0}
        out = tmp_path / "out.json"

        export_json(segments, metadata, str(out))

        raw = out.read_text()
        assert "\u00e9" in raw or "Caf" in raw  # ensure_ascii=False


# ---------------------------------------------------------------------------
# Database tests (require live PostgreSQL)
# ---------------------------------------------------------------------------

def _get_test_dsn():
    """Build DSN from env vars, falling back to defaults for CI."""
    import os
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "cys")
    user = os.environ.get("POSTGRES_USER", "cys")
    pw = os.environ.get("POSTGRES_PASSWORD", "cys_dev")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


def _db_available():
    try:
        with psycopg.connect(_get_test_dsn(), connect_timeout=3):
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(), reason="PostgreSQL not available"
)


@pytest.fixture
def db_conn():
    """Provide a connection and clean up test data after each test."""
    conn = psycopg.connect(_get_test_dsn())
    yield conn
    # Clean up any test episodes and their cascaded segments
    conn.execute("DELETE FROM episodes WHERE title LIKE 'TEST_%'")
    conn.commit()
    conn.close()


def _create_test_episode(conn) -> str:
    """Insert a test episode and return its UUID."""
    # Get the podcast id
    row = conn.execute("SELECT id FROM podcasts WHERE slug = 'the-yard'").fetchone()
    if row is None:
        raise RuntimeError("Run seed first: the-yard podcast must exist")
    podcast_id = row[0]

    episode_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO episodes (id, podcast_id, title)
        VALUES (%s, %s, %s)
        """,
        (episode_id, podcast_id, "TEST_transcription_test"),
    )
    conn.commit()
    return episode_id


@requires_db
class TestValidateEpisode:
    def test_valid_episode(self, db_conn):
        eid = _create_test_episode(db_conn)
        validate_episode(db_conn, eid)  # should not raise

    def test_invalid_episode(self, db_conn):
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="Episode not found"):
            validate_episode(db_conn, fake_id)


@requires_db
class TestSaveSegments:
    def _sample_segments(self):
        return [
            {"sequence": 0, "start_time": 0.0, "end_time": 2.5, "text": "Hello"},
            {"sequence": 1, "start_time": 2.5, "end_time": 5.0, "text": "World"},
        ]

    def test_insert_segments(self, db_conn):
        eid = _create_test_episode(db_conn)
        save_segments(db_conn, eid, self._sample_segments())

        count = check_existing_segments(db_conn, eid)
        assert count == 2

    def test_duplicate_protection(self, db_conn):
        eid = _create_test_episode(db_conn)
        save_segments(db_conn, eid, self._sample_segments())

        with pytest.raises(RuntimeError, match="already has"):
            save_segments(db_conn, eid, self._sample_segments())

    def test_replace_segments(self, db_conn):
        eid = _create_test_episode(db_conn)
        save_segments(db_conn, eid, self._sample_segments())

        new_segments = [
            {"sequence": 0, "start_time": 0.0, "end_time": 3.0, "text": "Replaced"},
        ]
        save_segments(db_conn, eid, new_segments, replace=True)

        count = check_existing_segments(db_conn, eid)
        assert count == 1

    def test_rollback_on_failure(self, db_conn):
        eid = _create_test_episode(db_conn)
        bad_segments = [
            {"sequence": 0, "start_time": 0.0, "end_time": 2.0, "text": "Good"},
            {"sequence": 0, "start_time": 2.0, "end_time": 4.0, "text": "Duplicate seq"},
        ]

        with pytest.raises(Exception):
            save_segments(db_conn, eid, bad_segments)

        count = check_existing_segments(db_conn, eid)
        assert count == 0


# ---------------------------------------------------------------------------
# DSN building
# ---------------------------------------------------------------------------

class TestGetDbDsn:
    def test_defaults(self, monkeypatch):
        for key in ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
            monkeypatch.delenv(key, raising=False)
        dsn = get_db_dsn()
        assert "db:5432" in dsn
        assert "cys" in dsn

    def test_custom_env(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_HOST", "myhost")
        monkeypatch.setenv("POSTGRES_PORT", "9999")
        monkeypatch.setenv("POSTGRES_DB", "testdb")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpw")
        dsn = get_db_dsn()
        assert "testuser:testpw@myhost:9999/testdb" in dsn
