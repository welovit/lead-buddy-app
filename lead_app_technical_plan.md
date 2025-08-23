# Lead App – Technical Build Plan

## 1 Overview

This document outlines the architecture and implementation strategy for the **Lead App**, an AI‑powered tool designed to help multi‑level marketing (MLM) professionals find, organize and nurture potential leads.  The application focuses on individuals who are already engaged in network‑marketing opportunities and presents them with a fresh opportunity in a structured, automated way.  It sources leads, manages them through a CRM‑like dashboard, uses AI to generate outreach sequences and handles subscription billing.  The conceptual requirements were defined by the user specification; this plan translates them into a technical design.

## 2 Architecture Summary

### 2.1 High‑Level Components

| Component             | Role/Responsibilities                                                                                                                                                   |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Frontend**         | User interface for sign‑up, login, profile management, lead display, note taking, folder organization, reminder scheduling and subscription management.                   |
| **Backend API**      | Authentication, business logic, user and lead management, scheduled lead delivery, AI‑assisted message generation, payment handling, and data persistence.              |
| **Database**         | Persistent storage for users, companies, categories, leads, notes, reminders, folders and subscription status.                                                           |
| **Scheduler/Worker** | Background jobs to fetch new leads daily at 09:00 local time per user and send reminder e‑mails.                                                                        |
| **AI Service**       | Integration with OpenAI’s GPT‑5 API (or other generative model) for automated messaging sequences (connect, qualify, invite).                                            |
| **Payment Gateway**  | Integration with Stripe to manage subscriptions, billing and cancellations.                                                                                                |

### 2.2 Suggested Technology Stack

- **Frontend**: React (with Next.js for SSR) or Vue.js; TypeScript recommended.
- **Backend**: Node.js with Express or NestJS; alternatively Python with Django/DRF or Flask.  Either stack can integrate easily with OpenAI and Stripe.
- **Database**: PostgreSQL for structured relational data.  Use an ORM (Sequelize for Node or SQLAlchemy/Django ORM for Python) to manage models and migrations.
- **Scheduler/Worker**: Use a job queue such as BullMQ or Agenda (Node) or Celery/RQ (Python) to run scheduled tasks; rely on cron‑like expressions for daily triggers.
- **AI Integration**: OpenAI GPT‑5 API for generating outreach messages; store API keys securely in environment variables.
- **Authentication**: JSON Web Tokens (JWT) or session cookies for secure login; hashed passwords with bcrypt or Argon2.
- **Email Delivery**: Use a transactional email service (SendGrid, Amazon SES, etc.) to send daily leads and follow‑up reminders.
- **Payment**: Stripe Subscriptions API with webhook handling to update subscription status on payment events.

## 3 Data Model

### 3.1 Entities and Relationships

- **User**
  - `id` (PK), `name`, `email`, `phone`, `password_hash`, `company_name`, `company_overview`, `country_preferences`, `category_preferences`, `subscription_status`, `stripe_customer_id`, `created_at`, `updated_at`.
  - `timezone` to determine 09:00 local time for deliveries.
- **Category**
  - `id` (PK), `name` (e.g. *Health & Nutrition*, *Beauty*, *Essential Oils*), `description`.
- **Company**
  - `id` (PK), `name`, `category_id` (FK to Category), `overview`, `website_url`, `country`.
- **Lead**
  - `id` (PK), `full_name`, `email`, `phone`, `country`, `company_id` (FK), `source_info` (raw JSON or metadata), `created_at`.
- **UserLeadStatus** (junction table between User and Lead)
  - `id` (PK), `user_id` (FK), `lead_id` (FK), `status` (`not_interested`, `maybe`, `interested`), `next_action_date`, `notes`, `folder_id`.
- **Folder**
  - `id` (PK), `user_id` (FK), `name` (default: *Not Interested*, *Maybe*, *Interested*; user may create custom folders).
- **Note**
  - `id` (PK), `user_lead_status_id` (FK), `content`, `created_at`.
- **Reminder**
  - `id` (PK), `user_lead_status_id` (FK), `reminder_datetime`, `sent_at` (nullable).
- **SubscriptionEvent**
  - `id` (PK), `user_id` (FK), `stripe_event_id`, `event_type`, `event_data`, `created_at`.

### 3.2 Data Considerations

- Users may select multiple countries and categories; store these as arrays or use a many‑to‑many join table (e.g., `UserCountryPreference` and `UserCategoryPreference`).
- When a user cancels a subscription, record a `cancellation_date` and schedule a **data deletion** after 30 days if not reactivated.
- Leads delivered to multiple users should not be shared across users; each user receives their own copy to manage statuses privately.

## 4 Backend API Design

Below is a summary of key endpoints.  Adjust naming to match your framework’s conventions.

### 4.1 Authentication

- **POST /auth/register** – create a new user account.
- **POST /auth/login** – authenticate user and return JWT/session.
- **POST /auth/logout** – revoke session.

### 4.2 User Profile & Preferences

- **GET /users/me** – retrieve user profile.
- **PUT /users/me** – update profile (name, phone, company details, preferences, timezone).
- **GET /users/me/categories** – list available company categories.

### 4.3 Lead Management

- **GET /leads/daily** – fetch the 7 leads delivered for the current day; idempotent (returns the same leads if called multiple times that day).
- **GET /leads/:leadId** – get full details for a lead.
- **POST /leads/:leadId/status** – update lead status (`not_interested`, `maybe`, `interested`) and optionally set a `next_action_date`; when status is set to `interested` send AI‑generated info via email.
- **POST /leads/:leadId/notes** – add or update notes; allow file or voice transcription if implementing voice features.
- **POST /folders** – create a new custom folder.
- **PUT /folders/:folderId** – rename or move leads into the folder.
- **DELETE /folders/:folderId** – delete a folder (must handle leads within by reassigning or deleting statuses).

### 4.4 Messaging & AI

- **POST /ai/messages/connect** – generate an initial connection message for a lead; uses GPT‑5 with prompt including user/lead/company details.
- **POST /ai/messages/qualify** – generate a follow‑up message to gauge interest.
- **POST /ai/messages/invite** – generate an invitation message with the user’s business information.

### 4.5 Subscription & Billing

- **POST /subscriptions/create‑checkout‑session** – create a Stripe Checkout session for the $20/month plan.
- **POST /subscriptions/webhook** – Stripe webhook endpoint to listen for events (subscription activated, canceled, payment failed).  Update `subscription_status`, record `cancellation_date`, and schedule deletion if needed.
- **GET /subscriptions/status** – get the current subscription status and expiry date.

## 5 Lead Sourcing Strategy

1. **Target Audience**: People already involved in network‑marketing companies, which can be found by crawling distributor listings, public social media profiles or specialized directories like BusinessForHome.org.  Note that the BusinessForHome site lists companies, not individuals; scraping individuals’ data from there may not be allowed or possible (our attempt to fetch the site programmatically returned a 403 access denied).  Use caution and ensure compliance with terms of service and privacy laws when scraping or purchasing leads.
2. **External Data Sources**: Use social‑media APIs, LinkedIn search or third‑party lead providers.  The exact source is beyond this plan; you might need to sign agreements or use paid data providers.
3. **Lead Enrichment**: Once a prospect is identified, use third‑party services (people search, email/phone append) to enrich contact details and verify category/company involvement.

> **Note**: The current environment could not fetch `businessforhome.org` pages due to an access restriction (HTTP 403).  Consequently, categories and companies must be seeded manually or obtained from alternative sources.  The categories known for MLM companies include *Health & Nutrition*, *Beauty*, *Essential Oils*, *Financial Services*, *Travel*, *Education* and *Home Goods*【395707309552312†L135-L143】.

## 6 Scheduling & Reminders

- Use a scheduler (e.g., cron jobs) to run a daily task per user at 09:00 in their timezone.  The task selects 7 new leads matching the user’s country and category preferences and creates `UserLeadStatus` records.  Send an email summarizing the leads.  If no new leads are available, send a message notifying the user.
- For leads in `maybe` status, schedule a follow‑up reminder at the `next_action_date`; the worker checks for reminders hourly and sends emails accordingly.
- Use the scheduler also for the 30‑day data retention timer: when a user cancels the subscription, schedule a deletion job 30 days later.  If the subscription is reactivated, cancel the deletion job.

## 7 AI‑Generated Messaging

- **Prompt Construction**: Build a prompt template including the user’s name, company overview, the lead’s current MLM company and category, and ask GPT‑5 to generate a concise, friendly outreach.  For example: “Draft a friendly LinkedIn message that introduces me (Name), mentions that we are both in the MLM industry, compliments their work at [Company], and asks if they are open to hearing about another opportunity.”
- **Sequence**: Save three separate prompts for the “connect”, “qualify”, and “invite” stages.  Respect platform guidelines (no spammy claims, no medical claims) and keep the tone professional.
- **Automation**: When a lead’s status transitions to “interested”, automatically send the AI‑generated information email using the user’s preferred email template.  Store message copies for compliance.

## 8 Frontend & User Experience

1. **Signup/Login**: A clean onboarding flow collecting user details (name, phone, email, company info).  Require email verification.
2. **Dashboard**: Cards or table listing daily leads; filters for status, category and country.  Each lead card shows contact info, company, category and an actions dropdown (mark status, add notes, schedule follow‑up, view message history).
3. **Folders**: Sidebar or tabbed interface to show default and custom folders.  Drag‑and‑drop or select‑and‑move to organize leads into folders.
4. **Notes**: Inline notes section with text area and voice recording (if using a speech‑to‑text API).  Notes can be timestamped and edited.
5. **Settings**: Manage profile, preferences (countries/categories), subscription status and billing details.
6. **Notifications**: Display reminders and subscription expiry countdown.  Provide a 30‑day countdown after cancellation with options to renew.

## 9 Security & Compliance

- **Data Protection**: Encrypt sensitive user data (especially phone and email) at rest.  Use HTTPS to secure data in transit.
- **GDPR/CCPA Compliance**: Provide mechanisms to export or delete personal data upon request.
- **Email & Anti‑Spam**: Ensure that automated outreach complies with CAN‑SPAM and other marketing regulations.  Provide unsubscribe/opt‑out mechanisms for prospects.
- **Scraping Ethics**: Respect website terms of service and privacy laws when scraping or purchasing leads.  Use data providers that have consented to data usage.

## 10 Roadmap & Future Enhancements

- **Mobile App**: Build a Progressive Web App first; then develop native iOS/Android apps for push notifications and offline access.
- **Messaging Integrations**: Add WhatsApp/Facebook Messenger API support for direct conversations from the dashboard.
- **Lead Scoring**: Implement machine‑learning models to score lead quality (hot/warm/cold) based on engagement signals.
- **Gamification**: Provide visual dashboards showing conversion rates, streaks and achievements to motivate users.
- **Multi‑Language Support**: Localize UI and AI prompts; store user language preference.
- **Analytics**: Show reports on lead sources, response rates, follow‑up outcomes and subscription metrics.

## 11 Conclusion

This plan converts the conceptual requirements of the Lead App into a feasible technical design.  The proposed stack leverages modern web technologies, robust databases, reliable scheduling and AI services to deliver a product that finds and nurtures MLM leads.  Key challenges include ethically sourcing lead data and complying with regulations; these must be addressed as the implementation progresses.  Once core features are stable, the roadmap offers several avenues for extending the product’s capabilities and market reach.
