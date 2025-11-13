# Backend Tests

## Test Yapısı

```
tests/
├── conftest.py          # Pytest fixtures ve config
├── test_auth.py         # Auth API testleri
├── test_api.py          # Temel API testleri
└── README.md           # Bu dosya
```

## Testleri Çalıştırma

### Docker İçinde
```bash
docker-compose exec api pytest
```

### Makefile ile
```bash
make test
```

### Coverage ile
```bash
docker-compose exec api pytest --cov=app --cov-report=html
```

Coverage raporu `htmlcov/index.html` dosyasında oluşur.

## Test Yazma

### Fixture Kullanımı

```python
def test_example(client: TestClient, auth_headers: dict):
    response = client.get("/v1/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### Mevcut Fixtures
- `session`: Test database session
- `client`: FastAPI TestClient
- `auth_token`: JWT token
- `auth_headers`: Authorization headers

## Test Kapsamı

- ✅ Auth API (login, logout, protected endpoints)
- ✅ Health check ve root endpoint
- ⏳ Cycles API (Excel upload, status)
- ⏳ Planning API (create plan, get plan)
- ⏳ Loadsheets API (station loadsheets, complete)
- ⏳ Counters API (save reading, get counters)

## Not

Test veritabanı olarak in-memory SQLite kullanılır.
Her test için temiz bir veritabanı oluşturulur.
