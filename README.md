# Site Audit AI Backend

API for website auditing and analysis, built with FastAPI, SQLAlchemy (async), Alembic, and a vertical slice architecture.

## 🚀 Project Structure

```bash
├── alembic/                # Database migrations
├── app/
│   ├── api_routers/        # API router registration
│   ├── features/           # Vertical slice features (auth, waitlist, health, etc.)
│   │   └── <feature>/
│   │       ├── models/     # SQLAlchemy models for this feature
│   │       ├── routes/     # FastAPI routers/endpoints for this feature
│   │       ├── schemas/    # Pydantic schemas for this feature
│   │       ├── services/   # Business logic for this feature
│   │       └── utils/      # Feature-specific utilities
│   ├── platform/           # Shared platform services (db, config, email, response, etc.)
│   └── main.py             # FastAPI app entrypoint
├── scripts/                # Utility scripts
├── tests/                  # Unit tests
├── pyproject.toml          # Project dependencies and metadata
├── uv.lock                 # Locked dependencies (for uv)
└── README.md
```

## 🏗️ Vertical Slice Architecture

- **Features**: Each feature (e.g., auth, waitlist) is self-contained with its own models, routes, schemas, services, and utilities
- **Platform**: Shared code (database, config, email, response formatting, etc.) lives in the `platform` directory
- **API Routers**: All feature routers are registered in `v1.py` and included in `main.py`

## 💻 Contributing

### Adding a New Feature

1. Create a new folder under `features` (e.g., `app/features/yourfeature/`)
2. Add subfolders as needed:
   - `models/` for SQLAlchemy models
   - `routes/` for FastAPI routers
   - `schemas/` for Pydantic schemas
   - `services/` for business logic
   - `utils/` for feature-specific helpers
3. Register your router in `v1.py`

### Working on Platform Services

- Add shared services (e.g., email, database session, config) in the `platform` directory
- Use these services in your features by importing from `app.platform`

### Where to Find Things

- **Feature endpoints**: `app/features/<feature>/routes/`
- **Feature models**: `app/features/<feature>/models/`
- **Feature schemas**: `app/features/<feature>/schemas/`
- **Feature logic**: `app/features/<feature>/services/`
- **Shared services**: `app/platform/services/`
- **Database/session/config**: `app/platform/db/`, `app/platform/config.py`
- **API router registration**: `app/api_routers/v1.py`
- **App entrypoint**: `app/main.py`

##  Setup & Development

### Clone the Repository

```bash
git clone <repo-url> && cd site-audit-ai-be
```

### Install Dependencies

```bash
uv sync
```

> **Note**: Or use `pip install -e .` if not using uv

### Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your values.

### Run Migrations

```bash
alembic upgrade head
```

### Start the Application

```bash
uvicorn app.main:app --reload
```

### Run Tests

```bash
pytest
```

## 📝 Notes

- Use the vertical slice pattern: keep all code for a feature together
- Shared logic goes in `platform`, not in individual features
- Register new routers in `api_routers/v1.py`
- Keep the codebase modular and easy to navigate

---

Built with ❤️ using FastAPI and modern Python tools
