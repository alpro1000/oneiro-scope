-- Initialize database with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial schema
-- Tables will be created by Alembic migrations
