#!/usr/bin/env bash
# Runs automatically on first init of the `db` container (via
# /docker-entrypoint-initdb.d/). Creates a separate role and database for
# Orthanc's own PostgreSQL index/storage, kept apart from the application's
# database (POSTGRES_DB/POSTGRES_USER) so the two services never share
# tables or credentials.
set -euo pipefail

: "${ORTHANC_DB_USER:?ORTHANC_DB_USER must be set}"
: "${ORTHANC_DB_PASSWORD:?ORTHANC_DB_PASSWORD must be set}"
: "${ORTHANC_DB_NAME:?ORTHANC_DB_NAME must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER "${ORTHANC_DB_USER}" WITH PASSWORD '${ORTHANC_DB_PASSWORD}';
    CREATE DATABASE "${ORTHANC_DB_NAME}" OWNER "${ORTHANC_DB_USER}";
EOSQL
