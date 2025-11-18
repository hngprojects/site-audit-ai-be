from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Note: Models will import this Base. Do not import models here to avoid circular imports.
# Import models in alembic/env.py instead for migrations.