-- Migration Rollback: Drop users table
-- Path: migrations/0001_add_users_table_rollback.sql

DROP TABLE IF EXISTS users;
