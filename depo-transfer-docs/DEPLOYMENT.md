# DEPLOYMENT

## Stack
- Backend: FastAPI + SQLModel/SQLAlchemy + Alembic
- DB: PostgreSQL (>=14)
- Cache/Queue: Redis (RQ/Celery)
- Frontend: React + Vite + Tailwind
- PDF: WeasyPrint / Puppeteer (headless)

## Docker Compose
- Services: api, web, db, redis, worker
- Volumes: db_data
- Env: `.env` dosyasından

## Komutlar
- `docker compose up -d`
- `docker compose exec api alembic upgrade head`
- `docker compose exec api python seed.py`
