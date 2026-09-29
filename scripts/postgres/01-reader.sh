#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv reader_password DB_READER_PASSWORD
CREATE ROLE demandsense_reader LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE demandsense TO demandsense_reader;
GRANT USAGE ON SCHEMA public TO demandsense_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE demandsense IN SCHEMA public GRANT SELECT ON TABLES TO demandsense_reader;
SQL
