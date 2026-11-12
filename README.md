<<<<<<< HEAD
# FamilyGuard – AI-Powered Parental Payment Monitoring System

> **Tagline:** *“Smart spending for children. Intelligent protection for parents.”*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PayPal Sandbox](https://img.shields.io/badge/PayPal-Sandbox%20Verified-003087.svg)](https://developer.paypal.com/)

FamilyGuard is an AI-powered family payment management and financial protection platform that allows parents to monitor their children’s digital transactions, configure granular spending limits, receive intelligent transaction alerts, review AI-generated transaction risk reports, and manage payment approval requests.

---

## 🌟 Key Features & Core Innovations

1. **Dual Distinct Dashboards with 1-Click Role Switcher**:
   - **Parent Dashboard**: Real-time spending telemetry, family-wide and child-specific analytics, limits configuration, approval workflows, and interactive AI Assistant.
   - **Child Wallet Dashboard**: Educational demo balance, visual daily/weekly limit gauges, savings goals tracker, and payment initiation form.
2. **AI Transaction Monitoring Engine (Core Module 4)**:
   - Evaluates every transaction against historical velocity, categories, and parental guardrails.
   - Generates structured JSON assessments containing risk classification (`LOW`, `MEDIUM`, `HIGH`), parent-friendly explanations, allowance impact, and review recommendations.
   - Enforces strict fintech safety rules: AI never executes transfers or alters spending limits independently.
3. **Automatic Transaction Report & PDF Generator (Core Module 5)**:
   - For every transaction, generates a formal digital audit receipt and AI monitoring report (specifically labelled as a parental monitoring verification record, not a merchant tax invoice).
   - Generates downloadable, styled PDF receipts via ReportLab.
4. **Parent Approval Workflow (Core Module 7)**:
   - Purchases exceeding the configured approval threshold (default ₹300) pause automatically.
   - Parents review AI explanation, decide to Approve or Decline, and child wallet balances update immediately upon authorization.
5. **Interactive AI Parent Assistant (Core Module 8)**:
   - Built-in chat interface answering natural language parental questions grounded in verified database records (e.g., *"How much did Arjun spend today?"*, *"What was the highest transaction this week?"*, *"Show transactions above ₹200"*).
6. **PayPal Sandbox REST API Integration (Core Module 9)**:
   - Backend OAuth access token caching.
   - PayPal Orders API (`/v2/checkout/orders`) & Capture API (`/v2/checkout/orders/{id}/capture`).
   - Webhook signature verification and idempotent event handling.
   - Polished fallback Demo Sandbox Mode when external PayPal keys are not configured.

---

## 🏗️ Architecture

```
                                  FamilyGuard Frontend
                            (React 19 + TypeScript + Tailwind CSS)
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
             Parent Dashboard                                Child Wallet Dashboard
     (Analytics, Approvals, AI Chat)                     (Limits, Payments, Savings)
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │ REST APIs / JWT Auth
                                              ▼
                                   FastAPI Application
                                      (Python 3.9+)
                                              │
         ┌───────────────────┬────────────────┴───────────────────┬───────────────────┐
         ▼                   ▼                                    ▼                   ▼
   Auth & Family     Spending Rules &                     AI Monitoring       PayPal REST
     Management     Approval Workflow                         Engine            Sandbox
   (JWT / bcrypt)  (Daily/Weekly Limits)               (OpenAI + Heuristics) (Orders/Captures)
         │                   │                                    │                   │
         └───────────────────┴────────────────┬───────────────────┴───────────────────┘
                                              │ SQLAlchemy ORM
                                              ▼
                                       Database Layer
                          (PostgreSQL Ready / SQLite Zero-Friction)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.9+**
- **Node.js 18+ & npm**

### 1. Backend Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup & Build

```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Launch Application

Run the unified server launcher:
```bash
python3 run.py
```

Open your browser at:
- **Unified Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive REST API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

*(Optional: For frontend hot-reloading development, run `npm --prefix frontend run dev` and navigate to [http://127.0.0.1:5173](http://127.0.0.1:5173))*

---

## 🧑‍💻 Synthetic Demo Credentials

The database is pre-seeded with realistic financial records for immediate demonstration:

| Role | Name | Email | Password | Initial Balance | Settings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Parent** | Demo Parent | `parent@familyguard.demo` | `Password123!` | — | Daily: ₹500, Weekly: ₹2,000, Threshold: ₹300 |
| **Child** | Arjun | `arjun@familyguard.demo` | `Password123!` | ₹2,000 | Monitored Account |

> **Tip:** You can switch instantly between **Parent (Demo Parent)** and **Child (Arjun)** anytime by clicking the role buttons in the top navigation bar!

---

## 🎬 13-Step Hackathon Demonstration Script

Run the automated verification script to observe the entire 13-step flow:
```bash
python3 scripts/verify_demo_scenario.py
```

### Interactive Manual Walkthrough:
1. **Parent Login**: Open `http://127.0.0.1:8000`. By default, you are logged in as **Demo Parent**.
2. **View Overview**: Observe the 4 KPI stat cards, 7-day spending area chart, category pie chart, and Arjun's active limits.
3. **Switch to Arjun**: Click **Child (Arjun)** in the top bar. Note Arjun's available balance (₹2,000).
4. **Initiate Payment Within Limit**:
   - Go to **Make Payment**.
   - Click the preset: **School Books & Stationery (₹150)**.
   - Click **Confirm Payment**.
   - Notice the instant verification, balance reduction to ₹1,850, and AI explanation.
5. **View Receipt & PDF**: Click **Receipt & AI Risk Assessment**. View the spending allowance impact and click **Download Official PDF Receipt**.
6. **Switch to Parent**: Click **Parent (Demo Parent)**.
   - Notice the new purchase notification in the bell dropdown.
7. **Initiate High-Value Payment (Threshold Trigger)**:
   - Switch back to **Child (Arjun)**.
   - Click preset: **Apex Gaming Store (₹450)** (exceeds ₹300 threshold).
   - Click **Confirm Payment**.
   - Observe message: *"Transaction pending parental approval."* Note that wallet balance remains ₹1,850 intact.
8. **Parent Approval Workflow**:
   - Switch to **Parent (Demo Parent)**.
   - Click **Approval Requests** (marked with a red notification badge).
   - Review AI risk explanation (*"Exceeds single transaction approval threshold of ₹300.00"*).
   - Enter optional notes and click **Approve Purchase**.
   - Transaction status updates to `COMPLETED` and Arjun's balance updates to ₹1,400.
9. **AI Parent Assistant**:
   - Click the **AI Parent Assistant** button in the header.
   - Click suggested queries or ask:
     - *"How much did my child spend today?"*
     - *"What was the highest transaction this week?"*
     - *"Show transactions above ₹200"*
     - *"How much of the weekly allowance remains?"*
   - Observe accurate, database-verified responses!

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env`:

```env
# Database Configuration (Defaults to SQLite for instant local execution)
DATABASE_URL=sqlite:///./familyguard.db

# For PostgreSQL Production:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/familyguard

# JWT Security
JWT_SECRET_KEY=familyguard_super_secure_secret_key_2026_dev
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OpenAI API (Optional - built-in deterministic safety rules activate automatically if empty)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# PayPal REST API Sandbox (Optional - simulated sandbox mode activates automatically if empty)
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_MODE=sandbox
PAYPAL_WEBHOOK_ID=
```

### PostgreSQL Setup (Optional)
If running a PostgreSQL instance:
1. Create database: `createdb familyguard`
2. Update `.env`: `DATABASE_URL=postgresql://postgres:password@localhost:5432/familyguard`
3. Restart application: `python3 run.py` (SQLAlchemy will auto-generate all 13 relational tables).

### PayPal Sandbox Setup (Optional)
1. Go to [developer.paypal.com](https://developer.paypal.com/) and log into the Dashboard.
2. Under **REST API Apps**, create an app to obtain your **Sandbox Client ID** and **Secret**.
3. Add them to `.env`:
   ```env
   PAYPAL_CLIENT_ID=your_sandbox_client_id
   PAYPAL_CLIENT_SECRET=your_sandbox_client_secret
   ```
4. Restart application. The payment form will now create and capture live PayPal Sandbox orders!

---

## 🧪 Automated Testing

Run the full integration test suite:

```bash
python3 -m unittest tests/test_familyguard.py
```

All 9 integration tests cover:
- Health check & API readiness
- Parent & Child JWT authentication
- Child wallet limits telemetry
- Sub-threshold auto-approval workflow
- Super-threshold parental approval workflow
- Parent approval/decline actions & balance integrity
- AI Assistant natural language query engine
- ReportLab PDF receipt generator

---

## 📄 License
FamilyGuard is open-source software released under the [MIT License](LICENSE).
=======
# FamilyGuard
an special system run over paypal to let parents create an wallet for childern and moniter theor activities
>>>>>>> 1fc5b0ece6f12818f927a0f866db8c2ffc9e54eb
