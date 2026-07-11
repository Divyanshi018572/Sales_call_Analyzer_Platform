-- Migration: Add users table for authentication and authorization
-- Path: migrations/0001_add_users_table.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('advisor', 'team_leader', 'director')),
    advisor_id INT REFERENCES advisors(id) ON DELETE SET NULL,
    team_id INT REFERENCES teams(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
