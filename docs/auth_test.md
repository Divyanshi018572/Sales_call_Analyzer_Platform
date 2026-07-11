# Authentication & Row-Level Authorization Verification

This document details how to verify JWT token role-scoping and row-level authorization constraints using `curl` against the local FastAPI instance.

## Seeding User Accounts
Before running these tests, ensure the local PostgreSQL database is seeded:
```bash
docker exec -e PYTHONPATH=. fitnova_api python scripts/seed_users.py
```
This seeds three users:
- **Director**: `director@fitnova.com` / `director_pass`
- **Team Leader**: `leader@fitnova.com` / `leader_pass` (Rohan's Team)
- **Advisor**: `rohan@fitnova.com` / `rohan_pass` (Advisor Rohan)

---

## 1. Acquire JWT Access Tokens

To get an access token, send a POST request to `/auth/login`:

### Request Director Token:
```bash
curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "director@fitnova.com", "password": "director_pass"}'
```
Response:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "role": "director",
  "email": "director@fitnova.com",
  ...
}
```

### Request Advisor Token (Rohan):
```bash
curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "rohan@fitnova.com", "password": "rohan_pass"}'
```

---

## 2. Test Row-Level and Role Authorization

### A. Director token hitting any endpoint (200 OK)
A director is allowed to view any advisor's summary:
```bash
curl -X GET http://localhost:8000/advisors/1/summary \
     -H "Authorization: Bearer <DIRECTOR_ACCESS_TOKEN>"
```
**Expected Response:** `200 OK` (with the summary statistics).

### B. Advisor token accessing another advisor's summary (403 Forbidden)
Seed another advisor or use a different advisor ID (e.g., `2`):
```bash
curl -X GET http://localhost:8000/advisors/999/summary \
     -H "Authorization: Bearer <ROHAN_ACCESS_TOKEN>"
```
**Expected Response:** `403 Forbidden`
```json
{
  "detail": "Access denied to this advisor's summary"
}
```

### C. Advisor token accessing another advisor's calls (403 Forbidden / Forced filter)
If Rohan lists calls with advisor_id of another advisor, the query filters it back to Rohan's ID:
```bash
curl -X GET "http://localhost:8000/calls?advisor_id=999" \
     -H "Authorization: Bearer <ROHAN_ACCESS_TOKEN>"
```
**Expected Response:** `200 OK` but returns Rohan's calls only (advisor_id is forced to `1` behind the scenes in the query layer).

If Rohan queries a call detail belonging to another advisor:
```bash
curl -X GET http://localhost:8000/calls/<OTHER_CALL_ID> \
     -H "Authorization: Bearer <ROHAN_ACCESS_TOKEN>"
```
**Expected Response:** `403 Forbidden`
```json
{
  "detail": "Access denied to this call details"
}
```
