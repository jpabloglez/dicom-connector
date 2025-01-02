# database/db_handler.py
"""
This DatabaseHandler class provides methods for connecting to 
the PostgreSQL database, creating the necessary table, 
inserting DICOM records, and retrieving records.
"""
import psycopg2
from psycopg2 import sql

class DatabaseHandler:
    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL", error)

    def disconnect(self):
        if self.connection:
            self.cursor.close()
            self.connection.close()

    def create_tables(self):
        self.connect()
        try:
            self.cursor.execute("""
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
            self.connection.commit()
        except (Exception, psycopg2.Error) as error:
            print("Error creating tables:", error)
        finally:
            self.disconnect()

    def insert_dicom_record(self, metadata, file_path):
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO dicom_files (patient_name, study_date, modality, study_description, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (metadata['PatientName'], metadata['StudyDate'], metadata['Modality'], 
                  metadata['StudyDescription'], file_path))
            self.connection.commit()
        except (Exception, psycopg2.Error) as error:
            print("Error inserting record:", error)
        finally:
            self.disconnect()

    def get_all_records(self):
        self.connect()
        try:
            self.cursor.execute("SELECT * FROM dicom_files ORDER BY created_at DESC")
            return self.cursor.fetchall()
        except (Exception, psycopg2.Error) as error:
            print("Error fetching records:", error)
            return []
        finally:
            self.disconnect()

    def search_records(self, search_term):
        self.connect()
        try:
            query = sql.SQL("""
                SELECT * FROM dicom_files 
                WHERE patient_name ILIKE %s 
                OR study_description ILIKE %s 
                ORDER BY created_at DESC
            """)
            self.cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
            return self.cursor.fetchall()
        except (Exception, psycopg2.Error) as error:
            print("Error searching records:", error)
            return []
        finally:
            self.disconnect()