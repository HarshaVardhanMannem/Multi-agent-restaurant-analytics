-- Initialization script for Restaurant Analytics Database
-- This will run when the container is first created

-- Create database if it doesn't exist (NOTE: The DB specified in POSTGRES_DB is created automatically, 
-- but this script runs inside that DB, so we can set up extensions or schemas here if needed)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- We can leave schema creation to the python scripts, checking connection is enough.
