# config.py
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env (if present) into the process environment. This only matters
# when running the app directly on the host (uv run ...) - docker-compose
# already injects these as real container env vars via its own .env
# handling, so this is a no-op there. Resolved relative to this file so it
# works regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PACS_CONFIG = {
    'host': os.environ.get('DICOM_PACS_HOST', 'localhost'),
    'port': int(os.environ.get('DICOM_PACS_PORT', '4242')),  # matches orthanc's DICOM port in docker-compose.yml
    'ae_title': os.environ.get('DICOM_PACS_AE_TITLE', 'ORTHANC'),
    'calling_ae_title': os.environ.get('DICOM_CALLING_AE_TITLE', 'MYAETITLE'),
}

DB_CONFIG = {
    'dbname': os.environ.get('DICOM_DB_NAME', 'dicom_db'),
    'user': os.environ.get('DICOM_DB_USER', 'dicom_user'),
    'password': os.environ.get('DICOM_DB_PASSWORD', 'dicom_password'),
    'host': os.environ.get('DICOM_DB_HOST', 'localhost'),  # docker-compose.yml always sets this explicitly for dicom_app
    'port': os.environ.get('DICOM_DB_PORT', '5432'),
}

ORTHANC_HTTP_CONFIG = {
    'url': os.environ.get('ORTHANC_HTTP_URL', 'http://localhost:8042'),
    'username': os.environ.get('ORTHANC_HTTP_USERNAME', 'orthanc'),
    'password': os.environ.get('ORTHANC_HTTP_PASSWORD', 'orthanc'),
}
