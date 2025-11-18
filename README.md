# 🚀 **SiteMate AI — Backend**

Backend service powering SiteMate AI — an AI-driven website health auditor designed for non-technical website owners.
This service handles URL scanning, issue extraction, AI-generated explanations, reporting, and fix-request routing.

---

## 📖 **Overview**

SiteMate AI helps small business owners, creators, and non-technical entrepreneurs understand what’s wrong with their websites without needing technical skills.

While existing audit tools like Lighthouse overwhelm users with developer-level metrics, SiteMate AI returns **plain-English explanations**, **prioritized issue categories**, and a simple path to **hire a verified HNG developer** to fix identified issues.

The backend is responsible for the core functional loop:

1. **Scan** — Crawl a user’s website and extract structured metrics.
2. **Understand** — Translate SEO, performance, accessibility, and design problems into simple explanations using AI.
3. **Fix** — Accept “Hire a Pro” requests and route them to vetted developers.

This service is built using **FastAPI**, with a modular architecture for future scalability (microservices, workers, AI pipelines, and multi-scan history tracking).

---

## 🧱 **Architecture**

```
site-audit-ai-BE/
│
├── main.py                 # FastAPI entrypoint
├── requirements.txt        # Project dependencies
│
├── app/
│   ├── __init__.py
│   ├── api/
│   │   └── v1/              # Versioned API endpoints
│   ├── core/                # App settings and configuration
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic v2 schemas
│   ├── services/            # Business logic (scanning, AI, fix requests)
│   └── utils/               # Helpers, scanners, AI clients
│
└── tests/
    └── test_health.py       # Pytest suite for basic endpoint checks
```

### Architectural Goals

- **Separation of Concerns** — routing, logic, schemas, and models are isolated for clarity.
- **Versioned API** — `/api/v1` routing ensures forward-compatibility.
- **Pydantic v2 first** — modern validation and serialization.
- **Extensible Pipeline** — future modules (workers, crawlers, AI inference) can be dropped into `services/` with minimal impact.
- **Testability** — pytest-first design with isolated modules.

---

## ⚙️ **Installation & Setup**

### **1. Clone the Repository**

```bash
git clone https://github.com/hngprojects/site-audit-ai-BE.git
cd site-audit-ai-BE
```

### **2. Choose Your Installation Method**

#### **🚀 Option 1: Using uv (Recommended)**

[**uv**](https://docs.astral.sh/uv/) is an extremely fast Python package installer and resolver, written in Rust. It's 10-100x faster than pip and provides a better dependency management experience.

**Install uv (if not already installed):**
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip (not recommended, but available)
pip install uv
```

**Install dependencies with uv:**
```bash
uv sync
```

#### **📦 Option 2: Using pip (Traditional)**

**Create and activate a virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\Activate.ps1 # Windows (PowerShell)
```

**Install dependencies:**
```bash
pip install -r requirements.lock
```

### **3. Create a `.env` File**

```bash
echo "APP_NAME=SiteMate AI Backend
DEBUG=True" > .env
```

Or manually create:

```
APP_NAME=SiteMate AI Backend
DEBUG=True
```

### **4. Run the Development Server**

**With uv:**
```bash
uv run uvicorn main:app --reload
```

**With pip:**
```bash
uvicorn main:app --reload
```

Visit API Docs:

```
http://127.0.0.1:8000/docs
```

### **5. Run Tests**

**With uv:**
```bash
uv run pytest
```

**With pip:**
```bash
pytest
```

---
