# Async Site Checker

REST API сервис для мониторинга доступности сайтов. Асинхронные проверки на базе FastAPI + httpx, хранение в SQLite.

## Стек

- Python 3.11+ (требуется `asyncio.TaskGroup`)
- FastAPI
- httpx (async HTTP-клиент)
- SQLAlchemy 2.0 (async) + aiosqlite
- pytest + pytest-asyncio

---

## Установка зависимостей

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Запуск приложения

```bash
uvicorn app.main:app --reload
```

Сервис будет доступен на `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

---

## Запуск тестов

```bash
pytest tests/ -v
```

---

## Docker

```bash
docker compose up --build
```

Сервис поднимается на порту `8000`. База данных сохраняется в `./data/sites.db` на хосте через volume.

---

## API

### POST /sites — добавить сайт

```bash
curl -X POST http://localhost:8000/sites \
  -H "Content-Type: application/json" \
  -d '{"name": "Example", "url": "https://example.com"}'
```

Ответ `201`:
```json
{
  "id": 1,
  "name": "Example",
  "url": "https://example.com/",
  "created_at": "2026-06-09T12:00:00"
}
```

---

### GET /sites — список сайтов

Параметры запроса: `limit` (1–100, по умолчанию 20), `offset` (по умолчанию 0).

```bash
curl http://localhost:8000/sites
curl "http://localhost:8000/sites?limit=10&offset=20"
```

---

### POST /checks/run — запустить проверку всех сайтов

Все сайты проверяются параллельно через `asyncio.TaskGroup` (Python 3.11+).
В отличие от `asyncio.gather`, при падении одной корутины все остальные задачи немедленно
отменяются — никаких утечек фоновых задач.

```bash
curl -X POST http://localhost:8000/checks/run
```

Ответ `200`:
```json
{
  "total": 2,
  "available": 1,
  "unavailable": 1,
  "results": [
    {
      "id": 1,
      "site_id": 1,
      "is_available": true,
      "status_code": 200,
      "response_time_ms": 143.7,
      "checked_at": "2026-06-09T12:00:01"
    }
  ]
}
```

---

### GET /checks/latest — последние результаты проверок

```bash
curl http://localhost:8000/checks/latest
```

Ответ `200`:
```json
[
  {
    "id": 1,
    "site_id": 1,
    "is_available": true,
    "status_code": 200,
    "response_time_ms": 143.7,
    "checked_at": "2026-06-09T12:00:01"
  }
]
```