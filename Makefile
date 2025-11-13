.PHONY: help up down dev logs logs-api logs-web shell-api shell-web migrate seed reset-db test clean

help:
	@echo "AkayDepo - Makefile Komutları"
	@echo ""
	@echo "  make up          - Tüm servisleri başlat (arka planda)"
	@echo "  make down        - Tüm servisleri durdur"
	@echo "  make dev         - Geliştirme modunda başlat (logları göster)"
	@echo "  make logs        - Tüm servislerin loglarını izle"
	@echo "  make logs-api    - Sadece API loglarını izle"
	@echo "  make logs-web    - Sadece Web loglarını izle"
	@echo "  make shell-api   - API container'ına bağlan"
	@echo "  make shell-web   - Web container'ına bağlan"
	@echo "  make migrate     - Veritabanı migrasyonunu çalıştır"
	@echo "  make seed        - Seed data yükle"
	@echo "  make reset-db    - Veritabanını sıfırla ve seed yükle"
	@echo "  make test        - Testleri çalıştır"
	@echo "  make clean       - Tüm container ve volume'leri temizle"

up:
	docker-compose up -d

down:
	docker-compose down

dev:
	docker-compose up

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-web:
	docker-compose logs -f web

shell-api:
	docker-compose exec api bash

shell-web:
	docker-compose exec web sh

migrate:
	docker-compose exec api alembic upgrade head

seed:
	docker-compose exec api python seed.py

reset-db:
	docker-compose down -v
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 5
	docker-compose up -d api
	@echo "Waiting for API to be ready..."
	@sleep 3
	docker-compose exec api alembic upgrade head
	docker-compose exec api python seed.py
	@echo "Database reset complete!"

test:
	docker-compose exec api pytest -v

clean:
	docker-compose down -v
	docker system prune -f
	@echo "Cleanup complete!"
