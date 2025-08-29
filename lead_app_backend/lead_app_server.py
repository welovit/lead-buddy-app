"""
lead_app_server.py
===================

Minimal HTTP server providing a basic backend for the Lead App.
Uses only the Python standard library and a local SQLite database.

Run:
    python lead_app_server.py
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

# Database file name. If you remove this file, a new database will be created on startup.
DB_NAME = os.path.join(os.path.dirname(__file__), "lead_app.db")


# ---------------------------
# Database bootstrap & helpers
# ---------------------------

def init_db() -> None:
    """Create database tables if they do not already exist and seed initial data."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            company_name TEXT,
            company_overview TEXT,
            timezone TEXT,
            country_preferences TEXT,
            category_preferences TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Sessions
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS session (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
        """
    )

    # Categories
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
        """
    )

    # Companies
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category_id INTEGER NOT NULL,
            overview TEXT,
            website_url TEXT,
            country TEXT,
            FOREIGN KEY(category_id) REFERENCES category(id)
        )
        """
    )

    # Leads
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lead (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            country TEXT,
            company_id INTEGER NOT NULL,
            source_info TEXT,
            FOREIGN KEY(company_id) REFERENCES company(id)
        )
        """
    )

    # UserLeadStatus
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_lead_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            delivery_date TEXT NOT NULL,
            status TEXT,
            next_action_date TEXT,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(lead_id) REFERENCES lead(id)
        )
        """
    )

    # Seed categories
    c.execute("SELECT COUNT(*) FROM category")
    if c.fetchone()[0] == 0:
        categories = [
            ("Health & Nutrition", "Dietary supplements, weight-management and wellness products"),
            ("Beauty", "Skincare, cosmetics and personal care items"),
            ("Essential Oils", "Aromatherapy oils and diffusers"),
            ("Financial Services", "Insurance, investments and fintech offerings"),
            ("Travel", "Travel clubs and discount packages"),
            ("Education", "Online courses and coaching"),
            ("Home Goods", "Household products and cleaning supplies"),
        ]
        c.executemany("INSERT INTO category (name, description) VALUES (?, ?)", categories)

    # Seed companies
    c.execute("SELECT COUNT(*) FROM company")
    if c.fetchone()[0] == 0:
        companies = [
            ("NutriLife", 1, "Global provider of nutritional supplements.", "https://www.nutrilife.example", "United States"),
            ("Beauty Bloom", 2, "Skin care and beauty products.", "https://www.beautybloom.example", "Canada"),
            ("AromaCo", 3, "Essential oils and diffusers.", "https://www.aromaco.example", "United Kingdom"),
            ("FinSecure", 4, "Network marketing with insurance and investment products.", "https://www.finsecure.example", "Australia"),
            ("TravelWell", 5, "Discount travel packages and memberships.", "https://www.travelwell.example", "South Africa"),
            ("EduWorks", 6, "Online coaching and business courses.", "https://www.eduworks.example", "India"),
            ("HomeBright", 7, "Home goods and eco-friendly cleaning supplies.", "https://www.homebright.example", "United States"),
        ]
        c.executemany(
            "INSERT INTO company (name, category_id, overview, website_url, country) VALUES (?, ?, ?, ?, ?)",
            companies,
        )

    # Seed leads
    c.execute("SELECT COUNT(*) FROM lead")
    if c.fetchone()[0] == 0:
        sample_leads = []
        names = [
            "Alice Brown", "Bob Smith", "Carlos Diaz", "Diana Evans", "Ethan Fox",
            "Fiona Green", "George Harris", "Hannah Ito", "Ivan Jensen", "Julia Kim",
            "Kyle Lee", "Lina Martinez", "Mohamed Nasir", "Nina O’Connor", "Oscar Perez",
            "Patricia Quinn", "Quincy Rogers", "Riya Singh", "Sam Taylor", "Tamara Upton",
        ]
        for idx, name in enumerate(names, start=1):
            company_id = (idx % 7) + 1  # rotate 1..7
            email = f"user{idx}@example.com"
            phone = f"+100000000{idx:02d}"
            # company table seeded above, pick country by that index
            c2 = companies[company_id - 1]
            country = c2[4]
            sample_leads.append((name, email, phone, country, company_id, json.dumps({"source": "seed"})))
        c.executemany(
            "INSERT INTO lead (full_name, email, phone, country, company_id, source_info) VALUES (?, ?, ?, ?, ?, ?)",
            sample_leads,
        )

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(salt + dk).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    data = base64.b64decode(stored_hash)
    salt, expected = data[:16], data[16:]
    test = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(expected, test)


def create_session(user_id: int, duration_hours: int = 24) -> str:
    token = str(uuid.uuid4())
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)).isoformat()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO session (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires_at))
    conn.commit()
    conn.close()
    return token


def get_user_id_by_session(token: str) -> Optional[int]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, expires_at FROM session WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    user_id, expires_at = row
    if datetime.datetime.fromisoformat(expires_at) < datetime.datetime.utcnow():
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM session WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    return user_id


def get_user_preferences(user_id: int) -> Tuple[List[str], List[int]]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT country_preferences, category_preferences FROM user WHERE id = ?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    countries_str, categories_str = row if row else ("", "")
    countries = [cc.strip() for cc in countries_str.split(",") if cc.strip()]
    category_ids: List[int] = []
    for cat in categories_str.split(","):
        cat = cat.strip()
        if cat:
            try:
                category_ids.append(int(cat))
            except ValueError:
                pass
    return countries, category_ids


def deliver_daily_leads(user_id: int) -> List[Dict[str, Any]]:
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Already delivered today?
    c.execute(
        """
        SELECT lead.id, lead.full_name, lead.email, lead.phone, lead.country, company.name,
               category.name, company.overview, company.website_url
        FROM user_lead_status AS uls
        JOIN lead ON uls.lead_id = lead.id
        JOIN company ON lead.company_id = company.id
        JOIN category ON company.category_id = category.id
        WHERE uls.user_id = ? AND uls.delivery_date = ?
        """,
        (user_id, today),
    )
    delivered = c.fetchall()
    if delivered:
        conn.close()
        return [
            {
                "lead_id": row[0],
                "full_name": row[1],
                "email": row[2],
                "phone": row[3],
                "country": row[4],
                "company": row[5],
                "category": row[6],
                "company_overview": row[7],
                "company_website": row[8],
            }
            for row in delivered
        ]

    # New picks based on preferences
    countries, category_ids = get_user_preferences(user_id)

    query = (
        "SELECT lead.id, lead.full_name, lead.email, lead.phone, lead.country, company.name, category.name, "
        "company.overview, company.website_url FROM lead "
        "JOIN company ON lead.company_id = company.id "
        "JOIN category ON company.category_id = category.id "
        "WHERE lead.id NOT IN (SELECT lead_id FROM user_lead_status WHERE user_id = ?)"
    )
    params: List[Any] = [user_id]
    if countries:
        query += " AND lead.country IN (" + ",".join(["?"] * len(countries)) + ")"
        params += countries
    if category_ids:
        query += " AND category.id IN (" + ",".join(["?"] * len(category_ids)) + ")"
        params += category_ids
    query += " ORDER BY RANDOM() LIMIT 7"

    c.execute(query, params)
    rows = c.fetchall()

    for row in rows:
        lead_id = row[0]
        c.execute(
            "INSERT INTO user_lead_status (user_id, lead_id, delivery_date, status) VALUES (?, ?, ?, NULL)",
            (user_id, lead_id, today),
        )

    conn.commit()
    conn.close()

    return [
        {
            "lead_id": row[0],
            "full_name": row[1],
            "email": row[2],
            "phone": row[3],
            "country": row[4],
            "company": row[5],
            "category": row[6],
            "company_overview": row[7],
            "company_website": row[8],
        }
        for row in rows
    ]


# ---------------------------
# HTTP Handler
# ---------------------------

class LeadAppRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Lead App API."""
    protocol_version = "HTTP/1.1"

    # ---- utilities ----
    def _set_json_headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200) -> None:
        self._set_json_headers(status)
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _parse_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _get_session_token(self) -> Optional[str]:
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        token_list = params.get("token")
        return token_list[0] if token_list else None

    # ---- HTTP verbs ----
    def do_POST(self) -> None:
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path == "/register":
            self.handle_register()
        elif path == "/login":
            self.handle_login()
        elif path == "/lead_status":
            self.handle_lead_status_update()
        elif path == "/notes":
            self.handle_add_note()
        elif path == "/user/profile":
            self.handle_update_profile()  # allow POST as fallback for clients without PUT
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/health":
            self._send_json({"status": "ok"})
            return

        if path == "/categories":
            self.handle_get_categories()
        elif path == "/leads/daily":
            self.handle_get_daily_leads()
        elif path == "/leads":
            self.handle_get_user_leads()
        elif path in ("/user/profile", "/profile"):
            self.handle_get_profile()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)  # No Content
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_PUT(self) -> None:
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path == "/user/profile":
            self.handle_update_profile()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    # ---- endpoint handlers ----
    def handle_register(self) -> None:
        data = self._parse_json_body()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        if not name or not email or not password:
            self._send_json({"error": "Name, email and password are required"}, status=400)
            return

        phone = data.get("phone") or ""
        company_name = data.get("company_name") or ""
        company_overview = data.get("company_overview") or ""
        timezone = data.get("timezone") or "UTC"
        countries = data.get("countries") or []
        categories = data.get("categories") or []

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # categories → ids
        cat_ids: List[int] = []
        for cat in categories:
            if isinstance(cat, int):
                cat_ids.append(cat)
            else:
                c.execute("SELECT id FROM category WHERE name = ?", (cat,))
                row = c.fetchone()
                if row:
                    cat_ids.append(row[0])

        cat_ids_str = ",".join(str(cid) for cid in cat_ids)
        country_str = ",".join(countries)
        password_hash = hash_password(password)

        try:
            c.execute(
                """
                INSERT INTO user (name, email, phone, password_hash, company_name, company_overview, timezone,
                                  country_preferences, category_preferences, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    phone,
                    password_hash,
                    company_name,
                    company_overview,
                    timezone,
                    country_str,
                    cat_ids_str,
                    datetime.datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            self._send_json({"status": "ok"}, status=201)
        except sqlite3.IntegrityError:
            self._send_json({"error": "User with this email already exists"}, status=409)
        finally:
            conn.close()

    def handle_login(self) -> None:
        data = self._parse_json_body()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            self._send_json({"error": "Email and password are required"}, status=400)
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM user WHERE email = ?", (email,))
        row = c.fetchone()
        if not row:
            conn.close()
            self._send_json({"error": "Invalid credentials"}, status=401)
            return

        user_id, stored_hash = row
        if not verify_password(password, stored_hash):
            conn.close()
            self._send_json({"error": "Invalid credentials"}, status=401)
            return

        token = create_session(user_id)
        conn.close()
        self._send_json({"token": token})

    def handle_get_categories(self) -> None:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, name, description FROM category ORDER BY name")
        categories = [{"id": row[0], "name": row[1], "description": row[2]} for row in c.fetchall()]
        conn.close()
        self._send_json({"categories": categories})

    def handle_get_daily_leads(self) -> None:
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return
        leads = deliver_daily_leads(user_id)
        self._send_json({"leads": leads})

    def handle_get_user_leads(self) -> None:
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        status_filter = params.get("status", [None])[0]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        base_query = (
            "SELECT lead.id, lead.full_name, lead.email, lead.phone, lead.country, "
            "company.name, category.name, uls.status, uls.next_action_date, "
            "uls.delivery_date, uls.notes, company.overview, company.website_url "
            "FROM user_lead_status AS uls "
            "JOIN lead ON uls.lead_id = lead.id "
            "JOIN company ON lead.company_id = company.id "
            "JOIN category ON company.category_id = category.id "
            "WHERE uls.user_id = ?"
        )
        params_list: List[Any] = [user_id]
        if status_filter:
            base_query += " AND uls.status = ?"
            params_list.append(status_filter)
        base_query += " ORDER BY uls.delivery_date DESC, lead.full_name ASC"
        c.execute(base_query, params_list)
        rows = c.fetchall()
        conn.close()

        leads = []
        for (lead_id, full_name, email, phone, country, company_name, category_name,
             status, next_action_date, delivery_date, notes, company_overview, company_website) in rows:
            leads.append({
                "lead_id": lead_id,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "country": country,
                "company": company_name,
                "category": category_name,
                "status": status,
                "next_action_date": next_action_date,
                "delivery_date": delivery_date,
                "notes": notes,
                "company_overview": company_overview,
                "company_website": company_website,
            })
        self._send_json({"leads": leads})

    def handle_lead_status_update(self) -> None:
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return

        data = self._parse_json_body()
        lead_id = data.get("lead_id")
        status = data.get("status")
        next_action_date = data.get("next_action_date")
        if not lead_id or not status:
            self._send_json({"error": "lead_id and status are required"}, status=400)
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            """
            UPDATE user_lead_status
            SET status = ?, next_action_date = ?
            WHERE user_id = ? AND lead_id = ?
            """,
            (status, next_action_date, user_id, lead_id),
        )
        if c.rowcount == 0:
            conn.close()
            self._send_json({"error": "Lead not found for this user"}, status=404)
            return
        conn.commit()
        conn.close()
        self._send_json({"status": "ok"})

    def handle_add_note(self) -> None:
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return

        data = self._parse_json_body()
        lead_id = data.get("lead_id")
        content = data.get("content")
        if not lead_id or not content:
            self._send_json({"error": "lead_id and content are required"}, status=400)
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT notes FROM user_lead_status WHERE user_id = ? AND lead_id = ?", (user_id, lead_id))
        row = c.fetchone()
        if not row:
            conn.close()
            self._send_json({"error": "Lead not found for this user"}, status=404)
            return
        existing_notes = row[0] or ""
        timestamp = datetime.datetime.utcnow().isoformat()
        note_entry = f"[{timestamp}] {content}\n"
        updated_notes = existing_notes + note_entry
        c.execute(
            "UPDATE user_lead_status SET notes = ? WHERE user_id = ? AND lead_id = ?",
            (updated_notes, user_id, lead_id),
        )
        conn.commit()
        conn.close()
        self._send_json({"status": "ok"})

    def handle_get_profile(self) -> None:
        """Return the authenticated user’s profile and preferences."""
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "SELECT name, email, phone, company_name, company_overview, timezone, country_preferences, category_preferences "
            "FROM user WHERE id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if not row:
            conn.close()
            self._send_json({"error": "User not found"}, status=404)
            return

        name, email, phone, company_name, company_overview, timezone, country_prefs_str, category_prefs_str = row
        countries = [cc.strip() for cc in (country_prefs_str or "").split(",") if cc.strip()]
        category_ids: List[int] = []
        if category_prefs_str:
            for part in category_prefs_str.split(","):
                part = part.strip()
                if part:
                    try:
                        category_ids.append(int(part))
                    except ValueError:
                        pass

        categories_info: List[Dict[str, Any]] = []
        if category_ids:
            placeholders = ",".join(["?"] * len(category_ids))
            c.execute(
                f"SELECT id, name FROM category WHERE id IN ({placeholders}) ORDER BY id",
                category_ids,
            )
            categories_info = [{"id": cid, "name": cname} for cid, cname in c.fetchall()]
        conn.close()

        self._send_json(
            {
                "name": name,
                "email": email,
                "phone": phone,
                "company_name": company_name,
                "company_overview": company_overview,
                "timezone": timezone,
                "countries": countries,
                "categories": categories_info,
            }
        )

    def handle_update_profile(self) -> None:
        """Update the authenticated user’s profile and preferences."""
        token = self._get_session_token()
        if not token:
            self._send_json({"error": "Authentication required"}, status=401)
            return
        user_id = get_user_id_by_session(token)
        if not user_id:
            self._send_json({"error": "Invalid or expired session"}, status=401)
            return

        data = self._parse_json_body()
        phone = data.get("phone")
        company_name = data.get("company_name")
        company_overview = data.get("company_overview")
        timezone = data.get("timezone")
        countries = data.get("countries")
        categories = data.get("categories")

        fields: List[str] = []
        values: List[Any] = []

        if phone is not None:
            fields.append("phone = ?")
            values.append(phone)
        if company_name is not None:
            fields.append("company_name = ?")
            values.append(company_name)
        if company_overview is not None:
            fields.append("company_overview = ?")
            values.append(company_overview)
        if timezone is not None:
            fields.append("timezone = ?")
            values.append(timezone)
        if countries is not None:
            if isinstance(countries, list):
                country_str = ",".join([c.strip() for c in countries if c.strip()])
            else:
                country_str = ""
            fields.append("country_preferences = ?")
            values.append(country_str)
        if categories is not None:
            cat_ids: List[int] = []
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for cat in categories:
                if isinstance(cat, int):
                    cat_ids.append(cat)
                elif isinstance(cat, str):
                    c.execute("SELECT id FROM category WHERE name = ?", (cat,))
                    r = c.fetchone()
                    if r:
                        cat_ids.append(r[0])
            conn.close()
            cat_str = ",".join(str(cid) for cid in cat_ids)
            fields.append("category_preferences = ?")
            values.append(cat_str)

        if not fields:
            self._send_json({"status": "ok"})
            return

        values.append(user_id)
        set_clause = ", ".join(fields)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(f"UPDATE user SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        self._send_json({"status": "ok"})


# ---------------------------
# Server bootstrap
# ---------------------------

def run_server(server_class=HTTPServer, handler_class=LeadAppRequestHandler, port: int = 8000) -> None:
    server_address = ("", port)   # bind on all interfaces
    httpd = server_class(server_address, handler_class)
    print(f"Lead App server running on http://localhost:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped")


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8080"))
    run_server(port=port)

