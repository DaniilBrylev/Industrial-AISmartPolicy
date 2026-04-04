# Industrial AISmartPolicy

Демонстрационный прототип для ВКР: формирование политики информационной безопасности промышленного предприятия с опорой на ИИ (на последующих этапах).

**Этап 1** — каркас full-stack приложения: FastAPI + PostgreSQL + Alembic, React (Vite) + TypeScript, Docker Compose. Авторизация, Redis, Nginx и вызовы внешних LLM на этом этапе не подключены; предусмотрены точки расширения (модули API и `app/services/ai`).

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Pydantic / pydantic-settings  
- **Frontend:** React 18, TypeScript, Vite 5  
- **Инфраструктура:** Docker, docker-compose  

## Быстрый старт (Docker Compose)

1. Скопируйте переменные окружения:

   ```bash
   cp .env.example .env
   ```

   В PowerShell: `Copy-Item .env.example .env`

   При необходимости отредактируйте `.env` (пароль БД, порты).

2. Запустите сервисы:

   ```bash
   docker compose up --build
   ```

3. Откройте в браузере:

   | Назначение        | URL                          |
   |-------------------|------------------------------|
   | Frontend (дашборд)| http://localhost:5173        |
   | Backend API       | http://localhost:8000        |
   | OpenAPI (Swagger) | http://localhost:8000/docs   |
   | Health            | http://localhost:8000/api/health |

При первом старте контейнер `backend` выполняет `alembic upgrade head`, затем поднимает Uvicorn.

## Локальная разработка без Docker (опционально)

**База:** поднимите PostgreSQL и задайте `DATABASE_URL` (например, `postgresql+psycopg2://user:pass@localhost:5432/aisec_policy`).

**Backend** (из каталога `backend`):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (из каталога `frontend`):

```bash
npm install
set VITE_API_URL=http://localhost:8000
npm run dev
```

На Linux/macOS: `export VITE_API_URL=http://localhost:8000`.

## Миграции

Из каталога `backend` после добавления моделей:

```bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
```

## Структура репозитория (логическая)

- `backend/app/api` — маршруты и сборка API  
- `backend/app/core` — конфигурация  
- `backend/app/db` — движок, сессии, `Base`  
- `backend/app/models` — ORM-модели  
- `backend/app/schemas` — Pydantic-схемы  
- `backend/app/services` — бизнес-логика; `services/ai` — заготовка под ИИ  
- `frontend/src/app` — корень приложения, стили  
- `frontend/src/pages` — страницы  
- `frontend/src/shared` — общие утилиты (в т.ч. HTTP к API)  

## Лицензия

Учебный проект (ВКР).
