import os
from pathlib import Path
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .schemas import Credentials, DraftPatch
from .security import admin_token_valid

app = FastAPI(title="Credit Draft Vault", version="2.0.0")
STATIC = Path(__file__).parent / "static"
SESSION_COOKIE = "vault_session"


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def current_client(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> str:
    client_id = db.user_by_session(session)
    if not client_id:
        raise HTTPException(401, "Войдите в аккаунт")
    return client_id


@app.post("/api/auth/register", status_code=201)
def register(payload: Credentials):
    if not db.create_user(payload.client_id.strip(), payload.password):
        raise HTTPException(409, "Такой ID клиента уже зарегистрирован")
    return {"registered": True}


@app.post("/api/auth/login")
def login(payload: Credentials, response: Response):
    result = db.authenticate_user(payload.client_id.strip(), payload.password)
    if not result:
        raise HTTPException(401, "Неверный ID клиента или пароль")
    session_token, client_id = result
    secure = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, secure=secure, samesite="lax", max_age=7 * 24 * 3600, path="/")
    return {"authenticated": True, "client_id": client_id}


@app.post("/api/auth/logout")
def logout(response: Response, session: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    db.delete_session(session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"authenticated": False}


@app.get("/api/auth/me")
def me(client_id: str = Depends(current_client)):
    return {"authenticated": True, "client_id": client_id}


@app.get("/api/draft")
def read_draft(client_id: str = Depends(current_client)):
    return db.ensure_draft(client_id)


@app.patch("/api/draft")
def patch_draft(payload: DraftPatch, client_id: str = Depends(current_client)):
    result = db.patch_draft(client_id, payload.field, payload.value, payload.version)
    if result is None:
        raise HTTPException(409, "Заявка изменилась на другом устройстве; обновите страницу")
    return result


def require_admin(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not admin_token_valid(token):
        raise HTTPException(401, "Требуется токен администратора")


@app.get("/api/admin/drafts", dependencies=[Depends(require_admin)])
def admin_list():
    return {"items": db.list_drafts()}


@app.delete("/api/admin/drafts/{draft_id}", dependencies=[Depends(require_admin)])
def admin_delete(draft_id: str):
    if not db.delete_draft(draft_id):
        raise HTTPException(404, "Черновик не найден")
    return {"deleted": True, "id": draft_id}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/admin")
def admin_page():
    return FileResponse(STATIC / "admin.html")


@app.get("/manus-routes.json")
def route_manifest():
    return FileResponse(STATIC / "manus-routes.json", media_type="application/json")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
