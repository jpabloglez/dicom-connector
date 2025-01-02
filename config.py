# config.py

PACS_CONFIG = {
    'host': 'pacs_server_address',
    'port': 11112,  # Default DICOM port
    'ae_title': 'MYAETITLE'
}

DB_CONFIG = {
    'dbname': 'dicom_db',
    'user': 'dicom_user',
    'password': 'dicom_password',
    'host': 'db',  # This should match the service name in docker-compose.yml
    'port': '5432'
}