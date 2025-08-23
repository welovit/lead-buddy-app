# Lead App Backend (Prototype)

This directory contains a lightweight prototype backend for the **Lead App**.  It provides
a simple HTTP API for user registration, authentication, category listing,
daily lead delivery, lead status updates and note taking.  The server uses
Python’s standard library only—there are **no external dependencies**—and
stores data in an SQLite database.

> **Note**: This prototype does **not** implement payment processing,
> subscription management or AI‑generated messaging.  Those features require
> integration with external services (e.g. Stripe, OpenAI) that are beyond
> the scope of this demonstration.

## Running the server

1. Ensure you have Python 3.7 or newer installed.
2. Open a terminal in the `lead_app_backend` directory.
3. Run the server:

   ```bash
   python lead_app_server.py
   ```

   The server will start listening on `http://localhost:8000/` and create
   a database file (`lead_app.db`) if one does not already exist.

## API Endpoints

All requests and responses use JSON.  Endpoints that modify or retrieve
user‑specific data require a session token; the token can be provided
either via the `Authorization: Bearer <token>` header or as a `token`
query parameter.

### `POST /register`

Create a new user account.

Request body:

```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "password": "yourpassword",
  "phone": "+12025550123",           // optional
  "company_name": "My MLM Co",       // optional
  "company_overview": "A brief description",  // optional
  "timezone": "Europe/London",       // optional (default UTC)
  "countries": ["United States", "Canada"], // optional preferences
  "categories": [1, 3]                // optional: category IDs or names
}
```

Responses:

* `201 Created` on success: `{ "status": "ok" }`
* `400 Bad Request` if required fields are missing.
* `409 Conflict` if an account with the given email already exists.

### `POST /login`

Authenticate a user and obtain a session token.

Request body:

```json
{
  "email": "you@example.com",
  "password": "yourpassword"
}
```

Response:

* `200 OK`: `{ "token": "<session-token>" }`
* `401 Unauthorized` if credentials are invalid.

### `GET /categories`

Retrieve the list of predefined company categories.

Response:

```json
{
  "categories": [
    {"id": 1, "name": "Health & Nutrition", "description": "..."},
    ...
  ]
}
```

### `GET /leads/daily`

Deliver up to seven leads for the authenticated user for the current date.
If the user has already received leads today, the same leads are returned.

Requires a valid session token.

Response:

```json
{
  "leads": [
    {
      "lead_id": 5,
      "full_name": "Alice Brown",
      "email": "user5@example.com",
      "phone": "+10000000005",
      "country": "United States",
      "company": "NutriLife",
      "category": "Health & Nutrition",
      "company_overview": "Global provider of nutritional supplements.",
      "company_website": "https://www.nutrilife.example"
    },
    ... up to 7 entries ...
  ]
}
```

### `POST /lead_status`

Update the status of a delivered lead and optionally schedule a next action.

Request headers:

```
Authorization: Bearer <token>
```

Request body:

```json
{
  "lead_id": 5,
  "status": "interested",             // one of: not_interested, maybe, interested
  "next_action_date": "2025-10-01"    // optional ISO date string
}
```

Response:

* `200 OK`: `{ "status": "ok" }`
* `404 Not Found` if the lead does not belong to the user.

### `POST /notes`

Add a note to a delivered lead.  Notes are appended to any existing notes with a timestamp.

Request headers:

```
Authorization: Bearer <token>
```

Request body:

```json
{
  "lead_id": 5,
  "content": "Followed up via email."
}
```

Response:

* `200 OK`: `{ "status": "ok" }`
* `404 Not Found` if the lead does not belong to the user.

## Example usage with cURL

```bash
# Register a new user
curl -X POST http://localhost:8000/register \
     -H "Content-Type: application/json" \
     -d '{
          "name": "Demo User",
          "email": "demo@example.com",
          "password": "password123",
          "countries": ["United States"],
          "categories": [1, 2]
        }'

# Log in and capture the token
TOKEN=$(curl -s -X POST http://localhost:8000/login \
            -H "Content-Type: application/json" \
            -d '{"email":"demo@example.com","password":"password123"}' | jq -r .token)

# Fetch categories
curl -X GET http://localhost:8000/categories

# Get daily leads
curl -X GET http://localhost:8000/leads/daily -H "Authorization: Bearer $TOKEN"

# Mark a lead as interested
curl -X POST http://localhost:8000/lead_status \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"lead_id":1,"status":"interested","next_action_date":"2025-10-01"}'

# Add a note to that lead
curl -X POST http://localhost:8000/notes \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"lead_id":1,"content":"Sent initial introduction email."}'
```

This prototype should serve as a starting point for developing the full Lead App.  You can extend it
with additional endpoints, subscription management, AI messaging and a user interface as needed.