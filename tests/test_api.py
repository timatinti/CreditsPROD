import os
from cryptography.fernet import Fernet
os.environ['APP_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
os.environ['ADMIN_TOKEN'] = 'test-admin'
os.environ['COOKIE_SECURE'] = 'false'
from fastapi.testclient import TestClient
from app.main import app
from app import db


def setup_function():
    if db.DB_PATH.exists(): db.DB_PATH.unlink()
    db.init_db()


def test_auth_required_and_draft_restore_after_login():
    c = TestClient(app)
    assert c.get('/api/draft').status_code == 401
    assert c.post('/api/auth/register', json={'client_id':'client-42','password':'strong-pass-1'}).status_code == 201
    assert c.post('/api/auth/login', json={'client_id':'client-42','password':'wrong-pass'}).status_code == 401
    assert c.post('/api/auth/login', json={'client_id':'client-42','password':'strong-pass-1'}).status_code == 200
    draft = c.get('/api/draft').json()
    assert draft['client_id'] == 'client-42'
    saved = c.patch('/api/draft', json={'field':'income','value':'180000','version':0})
    assert saved.status_code == 200 and saved.json()['version'] == 1
    c.post('/api/auth/logout')
    assert c.get('/api/draft').status_code == 401
    c.post('/api/auth/login', json={'client_id':'client-42','password':'strong-pass-1'})
    restored = c.get('/api/draft').json()
    assert restored['fields']['income'] == '180000'


def test_other_user_cannot_read_or_modify_first_users_draft():
    c = TestClient(app)
    c.post('/api/auth/register', json={'client_id':'owner','password':'owner-pass-1'})
    c.post('/api/auth/login', json={'client_id':'owner','password':'owner-pass-1'})
    c.patch('/api/draft', json={'field':'passport','value':'secret','version':0})
    c.post('/api/auth/logout')
    c.post('/api/auth/register', json={'client_id':'intruder','password':'intruder-1'})
    c.post('/api/auth/login', json={'client_id':'intruder','password':'intruder-1'})
    assert c.get('/api/draft').json()['fields'] == {}


def test_admin_delete():
    c = TestClient(app)
    c.post('/api/auth/register', json={'client_id':'abc','password':'abc-pass-1'})
    c.post('/api/auth/login', json={'client_id':'abc','password':'abc-pass-1'})
    draft = c.get('/api/draft').json()
    assert c.get('/api/admin/drafts', headers={'Authorization':'Bearer test-admin'}).status_code == 200
    assert c.delete('/api/admin/drafts/'+draft['id'], headers={'Authorization':'Bearer test-admin'}).json()['deleted'] is True
