# test_db_handler.py
"""Unit tests for DatabaseHandler against a mocked psycopg2 - no live
Postgres needed. See test_orthanc_connection.py for the live-service
integration test of the DB path via main.py's actual startup sequence.
"""
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from dicom_connector.database.db_handler import DatabaseHandler

DB_CONFIG = {"dbname": "d", "user": "u", "password": "p", "host": "h", "port": "5432"}


def make_mock_connection():
    """A connection/cursor pair that behaves like psycopg2's under `with`.

    MagicMock's default __exit__ already returns False (verified), so
    exceptions propagate correctly without this - __exit__ is pinned
    explicitly anyway just to make that behavior self-documenting rather
    than relying on an unstated default.
    """
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value = cursor

    return connection, cursor


@pytest.fixture
def mock_db():
    connection, cursor = make_mock_connection()
    with patch("dicom_connector.database.db_handler.psycopg2.connect", return_value=connection) as connect:
        yield connect, connection, cursor


def test_create_tables_executes_create_table_sql(mock_db):
    connect, connection, cursor = mock_db

    DatabaseHandler(DB_CONFIG).create_tables()

    connect.assert_called_once_with(**DB_CONFIG)
    sql_text = cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS dicom_files" in sql_text
    connection.close.assert_called_once()


def test_insert_dicom_record_passes_correct_params(mock_db):
    _connect, _connection, cursor = mock_db
    metadata = {
        "PatientName": "Doe^John", "StudyDate": "20240101",
        "Modality": "CT", "StudyDescription": "Chest",
    }

    DatabaseHandler(DB_CONFIG).insert_dicom_record(metadata, "/tmp/x.dcm")

    sql_text, params = cursor.execute.call_args[0]
    assert "INSERT INTO dicom_files" in sql_text
    assert params == ("Doe^John", "20240101", "CT", "Chest", "/tmp/x.dcm")


def test_get_all_records_returns_fetchall_result(mock_db):
    _connect, _connection, cursor = mock_db
    cursor.fetchall.return_value = [(1, "Doe^John")]

    result = DatabaseHandler(DB_CONFIG).get_all_records()

    assert result == [(1, "Doe^John")]
    assert "ORDER BY created_at DESC" in cursor.execute.call_args[0][0]


def test_search_records_wraps_term_for_ilike(mock_db):
    _connect, _connection, cursor = mock_db
    cursor.fetchall.return_value = [(1, "Doe^John")]

    result = DatabaseHandler(DB_CONFIG).search_records("doe")

    assert result == [(1, "Doe^John")]
    _query, params = cursor.execute.call_args[0]
    assert params == ("%doe%", "%doe%")


def test_connection_closed_even_when_query_raises(mock_db):
    _connect, connection, cursor = mock_db
    cursor.execute.side_effect = psycopg2.OperationalError("connection lost")

    with pytest.raises(psycopg2.OperationalError):
        DatabaseHandler(DB_CONFIG).get_all_records()

    connection.close.assert_called_once()


def test_insert_with_missing_metadata_key_raises_not_silently_ignored(mock_db):
    # regression test for the original bug: a failed insert used to be
    # caught, printed, and swallowed - the caller saw a clean return
    with pytest.raises(KeyError):
        DatabaseHandler(DB_CONFIG).insert_dicom_record({"PatientName": "Doe^John"}, "/tmp/x.dcm")
