# Credit Draft Vault

MVP-система для безопасного автосохранения и восстановления кредитной заявки. Backend — FastAPI, frontend — статический HTML/CSS/JS, storage — SQLite.

## Как работает доступ

Пользователь сначала регистрирует **ID клиента и пароль**. При входе сервер создаёт случайную сессию и отправляет её в `HttpOnly` cookie. Все маршруты черновика требуют эту сессию, поэтому одного знания ID клиента недостаточно. Пароль не хранится в открытом виде: используется PBKDF2-SHA256 с солью и 600 000 итерациями.

После закрытия вкладки пользователь снова открывает приложение, вводит ID и пароль, и сервер загружает его черновик. Другой пользователь видит только свой пустой черновик и не может прочитать или изменить чужой.

## Быстрый запуск

```bash
cd /home/ubuntu/credit-draft-app
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export APP_ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
export ADMIN_TOKEN=dev-admin-token
# для локального HTTP включить cookie без Secure-флага
export COOKIE_SECURE=false
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Откройте `http://localhost:8000`. Админ-панель доступна на `/admin`, Swagger — на `/docs`.

Для production необходимо передать стабильный `APP_ENCRYPTION_KEY` через secret manager, оставить `COOKIE_SECURE=true` на HTTPS и заменить `ADMIN_TOKEN`.

## API

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/auth/register` | Создать профиль по ID клиента и паролю |
| POST | `/api/auth/login` | Создать серверную сессию в HttpOnly cookie |
| POST | `/api/auth/logout` | Удалить текущую сессию |
| GET | `/api/auth/me` | Проверить текущую авторизацию |
| GET | `/api/draft` | Получить свой черновик |
| PATCH | `/api/draft` | Сохранить одно поле с проверкой версии |
| GET | `/api/admin/drafts` | Список черновиков с Bearer admin token |
| DELETE | `/api/admin/drafts/{id}` | Удалить черновик администратором |

Подробная схема хранения — в [`ER.md`](ER.md), план и дизайн — в [`plan.md`](plan.md).

## Проверка

```bash
. .venv/bin/activate
pytest -q
```
