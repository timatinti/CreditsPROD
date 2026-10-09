# ER-диаграмма

```mermaid
erDiagram
    USER ||--o{ SESSION : authenticates
    USER ||--o| DRAFT : owns
    USER {
        string id PK
        string client_id UK
        string password_hash
        datetime created_at
    }
    SESSION {
        string session_hash PK
        string user_id FK
        datetime expires_at
    }
    DRAFT {
        string id PK
        string client_id UK
        text encrypted_payload
        int version
        datetime updated_at
    }
```

Доступ к `DRAFT` идёт только через активную `SESSION`, найденную по HttpOnly-cookie. В базе нет открытого пароля: `password_hash` содержит PBKDF2-SHA256 с солью. В `DRAFT` содержимое заявки хранится в зашифрованном blob, а проверка версии обеспечивает атомарность и не даёт старому устройству затереть более новую версию.
