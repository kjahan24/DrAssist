-- Extensions required by the application layer (UUID generation, etc.).
-- Runs once, automatically, on first container initialization only.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
