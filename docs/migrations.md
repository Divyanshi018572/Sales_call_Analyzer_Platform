# Database Migrations

This document tracks schema modifications for the FitNova Full-Stack Platform.

## Run Migrations Locally
To apply SQL migrations to the Docker Postgres database:
```bash
Get-Content migrations/0001_add_users_table.sql | docker exec -i fitnova_postgres psql -U postgres -d fitnova_db
```

## Rollback Migrations Locally
To roll back the migrations:
```bash
Get-Content migrations/0001_add_users_table_rollback.sql | docker exec -i fitnova_postgres psql -U postgres -d fitnova_db
```

## Migrations Log
- **0001_add_users_table.sql**: Created the `users` table supporting roles (`director`, `team_leader`, `advisor`) and foreign keys to `advisors.id` and `teams.id` for role filtering.
