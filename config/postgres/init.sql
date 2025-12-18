-- Initialize databases for Hydra and Kratos
-- This script runs on PostgreSQL container startup

-- Database is already created by POSTGRES_DB env var
-- Just grant permissions
GRANT ALL PRIVILEGES ON DATABASE bindu_auth TO bindu;

