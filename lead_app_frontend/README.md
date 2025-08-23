# Lead Buddy Front‑End

This directory contains a simple web front‑end for the Lead Buddy application.
It allows users to register, log in, view their daily leads, update lead
statuses and add notes.  The UI is implemented with plain HTML, CSS and
JavaScript, and communicates with the back‑end via HTTP.

## Running the front‑end

You have two options to run the front‑end:

### 1. Serve via a static file server

Using the bundled `http-server` package (already installed in this project), you can serve the front‑end directory:

```bash
npm run start-frontend
```

This command maps to `http-server -p 8080 lead_app_frontend`.  Once running, open your browser and navigate to `http://localhost:8080`.
For the front‑end to work correctly, ensure the back‑end server from
`lead_app_backend/lead_app_server.py` is also running on `http://localhost:8000`.

### 2. Open directly in the browser

Alternatively, you can open `lead_app_frontend/index.html` directly in your
browser (e.g. by double‑clicking the file).  Because the back‑end allows
CORS, the page can make requests to `http://localhost:8000`.  However, some
browsers may restrict `file://` origins; serving via a local server is
preferred.

## Features

* **Registration**: Enter your name, email, password and optional details.  Preferences for countries and categories can be provided as comma‑separated lists.  Category IDs correspond to those displayed on the main page after logging in.
* **Login**: Authenticate with your email and password.
* **Leads**: After logging in, click **Refresh Leads** to load up to seven leads for today.  Each lead card displays contact information, company details and allows you to:
  * Update the lead status (Not Interested, Maybe, Interested).  If you choose **Maybe** or **Interested**, you can specify a next action date.
  * Add notes, which are saved with a timestamp.  Notes can be viewed and updated by re‑loading leads.
* **Manage All Leads**: Click **Manage Leads** to view every lead that has been delivered to you.  You can filter by status (all, Not Interested, Maybe or Interested), review existing notes and next action dates, and update a lead’s status or add new notes.  This helps organise your leads into folders/follow‑up lists.
* **Settings**: Use the **Settings** button in the top‑right to edit your phone number, company name, company overview, timezone and preferred countries and categories.  Changes are saved to your profile and influence which leads you receive each day.
* **Logout**: Clear the session and return to the authentication screen.

This front‑end is a prototype and already includes basic folder management (via lead statuses), settings editing and a simple dashboard for managing all your leads.  Future enhancements could include integration with messaging services or more advanced AI‑driven lead scoring.