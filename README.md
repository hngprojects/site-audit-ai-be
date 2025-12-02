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

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11**: Required for the project.
- **`uv`**: For package management. Install it via `pip install uv`.
- **Docker**: To run the PostgreSQL database.

## 💻 Setup & Development

1.  **Clone the Repository**
    ```bash
    git clone <repo-url> && cd site-audit-ai-be
    ```

2.  **Create and Activate Virtual Environment**
    ```bash
    uv venv site-audit
    source site-audit/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    uv sync
    ```

4.  **Start PostgreSQL Database (using Docker)**
    - Ensure Docker is running.
    - Run the following command to start a PostgreSQL container. This will create a database named `site_audit_db` with user `site_audit_user` and password `supersecret`, exposed on port `5433`.
    ```bash
    docker run --name site-audit-db -e POSTGRES_USER=site_audit_user -e POSTGRES_PASSWORD=supersecret -e POSTGRES_DB=site_audit_db -p 5433:5432 -v site-audit-db-data:/var/lib/postgresql/data -d postgres:16
    ```
    - If you need to stop or remove the container:
      ```bash
      docker stop site-audit-db
      docker rm site-audit-db
      docker volume rm site-audit-db-data
      ```

5.  **Set Up Environment Variables**
    - Copy `.env.example` to a new `.env` file:
      ```bash
      cp .env.example .env
      ```
    - Update the `.env` file. The `DATABASE_URL` should match the credentials used for the Docker container (e.g., `postgresql+asyncpg://site_audit_user:supersecret@localhost:5433/site_audit_db`). Fill in your JWT secret, email configuration, and other required values.

6.  **Run Database Migrations**
    ```bash
    alembic upgrade head
    ```

7.  **Start the Application**
    - To run the FastAPI server:
      ```bash
      uvicorn app.main:app --reload
      ```
    - To run the Celery worker for background tasks (requires RabbitMQ and Redis to be running separately):
      ```bash
      celery -A app.platform.celery_app.celery_app worker --loglevel=info
      ```

8.  **Run Tests**
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

## 📬 Postman Collection
https://elements.getpostman.com/redirect?entityId=41523557-0ef52a59-0512-40b8-a3db-9fd3fea0020f&entityType=collection