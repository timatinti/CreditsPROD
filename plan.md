# Система сохранения и восстановления кредитной заявки

## Реализация

MVP использует простую модель: пользователь регистрирует внутренний **ID клиента и пароль**, а затем при каждом новом устройстве входит с этими данными. После входа сервер создаёт случайную сессию, хранит только её хэш и отправляет оригинал в `HttpOnly`, `SameSite=Lax` cookie. Без действующей сессии API черновика всегда отвечает `401`, поэтому один ID клиента не раскрывает историю заявки.

Backend — FastAPI + SQLite. Пароли хэшируются PBKDF2-SHA256 с индивидуальной солью и 600 000 итерациями. Содержимое заявки шифруется Fernet до записи в БД. Каждый PATCH содержит версию; SQLite-транзакция с `BEGIN IMMEDIATE` отклоняет устаревшее изменение кодом `409`. Один клиент имеет один черновик, который автоматически создаётся после входа.

Frontend — статический HTML/CSS/JS. При закрытии вкладки cookie сессии остаётся, а после повторного входа GET `/api/draft` загружает последнюю версию. После каждого изменения поля выполняется debounced PATCH. Администратор по-прежнему удаляет черновики через отдельный Bearer-токен.

## Дизайн

Спокойный fintech editorial: глубокий emerald для доверия, молочный фон, строгая типографика и карточки-состояния. Главная страница сначала показывает регистрацию/вход, а форму заявки раскрывает только после успешной авторизации. Статус сообщает, когда данные загружены, сохранены или конфликтуют с изменениями другого устройства.

## Структура проекта

- `app/main.py` — auth, session-protected draft routes, admin routes, static serving.
- `app/db.py` — SQLite schema, user/session repository, encrypted draft repository.
- `app/security.py` — password hashing, Fernet encryption, session hashing.
- `app/schemas.py` — credentials and patch models.
- `app/static/index.html` / `app.js` — auth flow, restore on login and autosave form.
- `app/static/admin.html` / `admin.js` — admin cleanup panel.
- `tests/test_api.py` — auth requirement, restore, isolation and admin tests.
- `ER.md` — entity relationship diagram.
