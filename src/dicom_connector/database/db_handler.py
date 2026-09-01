# database/db_handler.py
"""
This DatabaseHandler class provides methods for connecting to
the PostgreSQL database, creating the necessary table,
inserting DICOM records, and retrieving records.
"""
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)


class DatabaseHandler:
    def __init__(self, db_config):
        self.db_config = db_config

    @contextmanager
    def _connection(self):
        """Open a connection/cursor for one unit of work and always close it.

        Commits on a clean exit, rolls back and re-raises on error - callers
        see failures instead of a swallowed exception and a stale cursor.
        """
        connection = psycopg2.connect(**self.db_config)
        try:
            with connection, connection.cursor() as cursor:
                yield cursor
        except (Exception, psycopg2.Error):
            logger.exception("Database operation failed")
            raise
        finally:
            connection.close()

    def create_tables(self):
        with self._connection() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dicom_files (
                    id SERIAL PRIMARY KEY,
                    patient_name VARCHAR(255),
                    study_date DATE,
                    modality VARCHAR(50),
                    study_description TEXT,
                    file_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def insert_dicom_record(self, metadata, file_path):
        with self._connection() as cursor:
            cursor.execute("""
                INSERT INTO dicom_files (patient_name, study_date, modality, study_description, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (metadata['PatientName'], metadata['StudyDate'], metadata['Modality'],
                  metadata['StudyDescription'], file_path))

    def get_all_records(self):
        with self._connection() as cursor:
            cursor.execute("SELECT * FROM dicom_files ORDER BY created_at DESC")
            return cursor.fetchall()

    def search_records(self, search_term):
        with self._connection() as cursor:
            query = sql.SQL("""
                SELECT * FROM dicom_files
                WHERE patient_name ILIKE %s
                OR study_description ILIKE %s
                ORDER BY created_at DESC
            """)
            cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
            return cursor.fetchall()
