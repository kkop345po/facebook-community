from __future__ import annotations

import base64
import hashlib
import hmac
import html
import logging
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from email.utils import parseaddr
from functools import wraps
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psycopg
import requests
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request as GoogleRequest
from cryptography.fernet import Fernet
from dotenv import dotenv_values
from flask import Flask, g, jsonify, request, send_from_directory, session
from psycopg.rows import dict_row
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
log = logging.getLogger('connect')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id UUID PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 password_hash TEXT NOT NULL, bio TEXT NOT NULL DEFAULT '', verified BOOLEAN NOT NULL DEFAULT FALSE,
 active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TIMESTAMPTZ NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (
 token_hash TEXT PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 purpose TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL, used BOOLEAN NOT NULL DEFAULT FALSE);
CREATE TABLE IF NOT EXISTS posts (
 id BIGSERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), edited BOOLEAN NOT NULL DEFAULT FALSE,
 request_id UUID, UNIQUE(user_id,request_id));
CREATE TABLE IF NOT EXISTS comments (
 id BIGSERIAL PRIMARY KEY, post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, body TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), request_id UUID, UNIQUE(user_id,request_id));
CREATE TABLE IF NOT EXISTS likes (
 post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, PRIMARY KEY(post_id,user_id));
CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL);
CREATE TABLE IF NOT EXISTS mail_jobs (
 id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 purpose TEXT NOT NULL, encrypted_payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 retry_at TIMESTAMPTZ NOT NULL DEFAULT now(), provider_id TEXT);
CREATE TABLE IF NOT EXISTS audit (
 id BIGSERIAL PRIMARY KEY, action TEXT NOT NULL, target TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS post_time ON posts(created_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS comment_post ON comments(post_id,id);
CREATE INDEX IF NOT EXISTS session_user_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS token_user ON tokens(user_id,purpose);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_npc BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS messages (
 id BIGSERIAL PRIMARY KEY, sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, body TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), read_at TIMESTAMPTZ, request_id UUID,
 UNIQUE(sender_id,request_id));
CREATE INDEX IF NOT EXISTS msg_thread ON messages(sender_id,recipient_id,id DESC);
CREATE INDEX IF NOT EXISTS msg_inbox ON messages(recipient_id,id DESC);
CREATE TABLE IF NOT EXISTS bot_state (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS google_identities (
 sub TEXT PRIMARY KEY,user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS google_challenges (
 token_hash TEXT PRIMARY KEY,expires_at TIMESTAMPTZ NOT NULL);
'''


def settings():
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    return {k: v for k, v in values.items() if v is not None}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def mail_mode():
    cfg = settings()
    if not cfg.get('RESEND_API_KEY') or not cfg.get('MAIL_FROM'):
        return 'unconfigured'
    sender = parseaddr(cfg['MAIL_FROM'])[1].lower()
    return 'resend_test' if sender.endswith('@resend.dev') else 'custom_domain'


def connect(config=None):
    return psycopg.connect((config or settings())['DATABASE_URL'], row_factory=dict_row, connect_timeout=5)


def initialize():
    with connect() as conn:
        conn.execute(SCHEMA)


def cipher():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings()['SECRET_KEY'].encode()).digest()))


def dispatch_mail(job_id=None):
    cfg = settings()
    if not cfg.get('RESEND_API_KEY') or not cfg.get('MAIL_FROM'):
        return False
    with connect() as conn:
        conn.execute("UPDATE mail_jobs SET status='expired' WHERE status='pending' AND created_at < now() - CASE WHEN purpose='reset' THEN interval '30 minutes' ELSE interval '24 hours' END")
        query = "SELECT m.*,u.email FROM mail_jobs m JOIN users u ON u.id=m.user_id WHERE m.status='pending' AND m.retry_at<=now()"
        params = []
        if job_id:
            query += ' AND m.id=%s'; params.append(job_id)
        query += ' ORDER BY m.created_at LIMIT 1 FOR UPDATE OF m SKIP LOCKED'
        job = conn.execute(query, params).fetchone()
        if not job:
            return False
        link = cipher().decrypt(job['encrypted_payload'].encode()).decode()
        token = parse_qs(urlparse(link).query).get('token', [''])[0]
        if not token or not conn.execute('SELECT 1 FROM tokens WHERE token_hash=%s AND NOT used AND expires_at>now()', (digest(token),)).fetchone():
            conn.execute("UPDATE mail_jobs SET status='expired' WHERE id=%s", (job['id'],))
            return False
        title = '驗證你的信箱' if job['purpose'] == 'verify' else '重設你的密碼'
        expiry = '24 小時' if job['purpose'] == 'verify' else '30 分鐘'
        try:
            result = requests.post('https://api.resend.com/emails', headers={
                'Authorization': 'Bearer ' + cfg['RESEND_API_KEY'],
                'Idempotency-Key': 'connect/' + str(job['id']),
            }, json={
                'from': cfg['MAIL_FROM'], 'to': [job['email']], 'subject': f'Facebook｜{title}',
                'html': f'<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:32px"><h1 style="color:#1877f2">Facebook</h1><h2>{title}</h2><p>請在 {expiry}內開啟下方連結。連結僅能使用一次，重新申請會讓舊連結失效。</p><p><a href="{html.escape(link, quote=True)}">{title}</a></p><p>若不是你本人申請，請忽略這封信，不要轉寄此連結。</p></div>',
                'text': f'{title}：{link}\n有效期 {expiry}。若非本人申請請忽略，請勿轉寄。',
            }, timeout=8)
            if not result.ok:
                if 400 <= result.status_code < 500 and result.status_code not in (408, 429):
                    conn.execute("UPDATE mail_jobs SET status='failed',attempts=attempts+1 WHERE id=%s", (job['id'],))
                    log.warning('Mail rejected permanently; event=%s status=%s', job['id'], result.status_code)
                    return False
                raise ValueError('mail provider rejected request')
            provider_id = str(result.json().get('id', ''))
            conn.execute("UPDATE mail_jobs SET status='sent',provider_id=%s,attempts=attempts+1 WHERE id=%s", (provider_id, job['id']))
            return True
        except (requests.RequestException, ValueError):
            attempts = job['attempts'] + 1
            delay = min(60 * 2 ** min(attempts - 1, 6), 3600) + secrets.randbelow(15)
            status = 'failed' if attempts >= 6 else 'pending'
            conn.execute("UPDATE mail_jobs SET attempts=%s,status=%s,retry_at=now()+(%s * interval '1 second') WHERE id=%s", (attempts, status, delay, job['id']))
            log.warning('Mail pending retry; event=%s', job['id'])
            return False


def mail_loop():
    while True:
        try:
            dispatch_mail()
        except Exception:
            log.warning('Mail queue unavailable; will retry')
        time.sleep(30)


def create_app(test_config=None):
    cfg = settings()
    app = Flask(__name__, static_folder=None)
    app.config['BUILD_ID'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    app.config.update(SECRET_KEY=cfg.get('SECRET_KEY', ''), MAX_CONTENT_LENGTH=32 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=cfg.get('COOKIE_SECURE') == 'true')
    if test_config:
        app.config.update(test_config)
    if not app.secret_key:
        raise RuntimeError('Run setup_local.py first')

    def db():
        if 'db' not in g:
            g.db = connect(app.config.get('TEST_DATABASE_CONFIG'))
        return g.db

    def error(message, status=400):
        return jsonify(error=message), status

    @app.before_request
    def before():
        g.trace_id = str(uuid.uuid4())
        if request.path.startswith('/api/'):
            session.setdefault('csrf', secrets.token_urlsafe(32))
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                csrf = request.headers.get('X-CSRF-Token', '')
                if not hmac.compare_digest(csrf, session['csrf']):
                    return error('頁面已過期，請重新整理後再試。', 403)
                origin = request.headers.get('Origin')
                allowed = {settings().get('PUBLIC_URL', '').rstrip('/'), 'http://127.0.0.1:5080', 'http://localhost:5080'}
                if origin and origin not in allowed:
                    return error('此來源不允許提交操作。', 403)

    @app.after_request
    def after(response):
        if 'db' in g:
            if response.status_code < 400:
                g.db.commit()
            else:
                g.db.rollback()
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style; script-src 'self' https://accounts.google.com/gsi/client; connect-src 'self' https://accounts.google.com/gsi/; frame-src https://accounts.google.com/gsi/; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
        response.headers['X-Request-ID'] = g.get('trace_id', '')
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        elif response.status_code in (200, 304) and re.fullmatch(r'/assets/[^/]+-[A-Za-z0-9_-]{8,}\.(?:js|css)', request.path):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.teardown_request
    def close_db(_exc):
        if 'db' in g:
            g.db.close()

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return error('請求無法處理。' if exc.code != 404 else '找不到這個內容。', exc.code)

    @app.errorhandler(Exception)
    def unknown_error(exc):
        log.error('Request failed; event=%s type=%s', g.get('trace_id'), type(exc).__name__)
        return jsonify(error='服務暫時無法處理，請稍後重試。', trace_id=g.get('trace_id')), 503

    def current_user():
        raw = session.get('sid')
        if not raw:
            return None
        return db().execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=%s AND s.expires_at>now() AND u.active AND u.verified', (digest(raw),)).fetchone()

    def required(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            g.user = current_user()
            if not g.user:
                return error('請先登入已驗證的帳號。', 401)
            return fn(*args, **kwargs)
        return inner

    def public_user(user):
        return dict(id=str(user['id']), name=user['name'], bio=user['bio'], joined_at=user['created_at'].isoformat(),
                    is_npc=bool(user.get('is_npc')))

    def body_data():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {}
        return data

    def text(data, key, maximum, minimum=1):
        value = data.get(key)
        if not isinstance(value, str):
            raise ValueError('欄位格式不正確。')
        value = value.strip()
        if not minimum <= len(value) <= maximum:
            raise ValueError(f'內容需介於 {minimum}–{maximum} 字。')
        return value

    def email(data):
        value = text(data, 'email', 254).lower()
        if len(value.split('@')) != 2 or '.' not in value.split('@')[1] or any(c.isspace() for c in value):
            raise ValueError('請輸入有效的 Email。')
        return value

    def password(data):
        value = data.get('password', '')
        if not isinstance(value, str) or not 12 <= len(value) <= 128:
            raise ValueError('密碼需介於 12–128 字。')
        return value

    @app.errorhandler(ValueError)
    def validation_error(exc):
        return error(str(exc))

    def limit(key, maximum, seconds):
        hashed = digest(key)
        count = db().execute("INSERT INTO limits(key,count,expires_at) VALUES(%s,1,now()+(%s * interval '1 second')) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN limits.expires_at<now() THEN 1 ELSE limits.count+1 END,expires_at=CASE WHEN limits.expires_at<now() THEN excluded.expires_at ELSE limits.expires_at END RETURNING count", (hashed, seconds)).fetchone()['count']
        # Persist attempted requests even when the endpoint rejects them.
        db().commit()
        return count <= maximum

    def ip():
        # Only cloudflared on loopback is trusted to supply this header.
        return request.headers.get('CF-Connecting-IP', request.remote_addr or '') if request.remote_addr in ('127.0.0.1', '::1') else request.remote_addr

    def issue(user, purpose):
        raw = secrets.token_urlsafe(40)
        minutes = 1440 if purpose == 'verify' else 30
        db().execute('UPDATE tokens SET used=TRUE WHERE user_id=%s AND purpose=%s', (user['id'], purpose))
        db().execute("UPDATE mail_jobs SET status='superseded' WHERE user_id=%s AND purpose=%s AND status='pending'", (user['id'], purpose))
        db().execute("INSERT INTO tokens VALUES(%s,%s,%s,now()+(%s * interval '1 minute'),FALSE)", (digest(raw), user['id'], purpose, minutes))
        base = settings().get('PUBLIC_URL', '').rstrip('/')
        if not base.startswith(('https://', 'http://127.0.0.1', 'http://localhost')):
            raise ValueError('網站公開網址尚未設定。')
        link = base + '/?action=' + purpose + '&token=' + raw
        job = str(uuid.uuid4())
        db().execute('INSERT INTO mail_jobs(id,user_id,purpose,encrypted_payload) VALUES(%s,%s,%s,%s)', (job, user['id'], purpose, cipher().encrypt(link.encode()).decode()))
        db().commit()
        return dispatch_mail(job)

    @app.get('/api/session')
    def state():
        user = current_user()
        mode = mail_mode()
        return jsonify(user=public_user(user) if user else None, csrf=session['csrf'], mail_ready=mode != 'unconfigured', mail_mode=mode,
                       google_ready=bool(settings().get('GOOGLE_CLIENT_ID')))

    @app.post('/api/auth/google/challenge')
    def google_challenge():
        client_id = settings().get('GOOGLE_CLIENT_ID')
        if not client_id:
            return error('Google 登入設定中，請先使用 Email 登入。', 503)
        if not limit('google-challenge:' + str(ip()), 30, 600):
            return error('嘗試次數過多，請稍後再試。', 429)
        nonce = secrets.token_urlsafe(32)
        db().execute('DELETE FROM google_challenges WHERE expires_at<now()')
        db().execute("INSERT INTO google_challenges VALUES(%s,now()+interval '10 minutes')", (digest(nonce),))
        session['google_nonce'] = nonce
        return jsonify(client_id=client_id, nonce=nonce)

    @app.post('/api/auth/google')
    def google_login():
        client_id = settings().get('GOOGLE_CLIENT_ID')
        if not client_id:
            return error('Google 登入尚未設定。', 503)
        nonce = session.pop('google_nonce', '')
        challenge = db().execute('DELETE FROM google_challenges WHERE token_hash=%s AND expires_at>now() RETURNING token_hash', (digest(nonce),)).fetchone()
        db().commit()  # A challenge is single-use even when token verification fails.
        if not nonce or not challenge:
            return error('Google 登入已過期，請重新按 Google 登入。', 401)
        if not limit('google-login:' + str(ip()), 20, 900):
            return error('嘗試次數過多，請稍後再試。', 429)
        credential = body_data().get('credential')
        if not isinstance(credential, str) or len(credential)>12000:
            return error('Google 登入資料不正確。', 401)
        try:
            claims = google_id_token.verify_oauth2_token(credential, GoogleRequest(), client_id)
            if not hmac.compare_digest(str(claims.get('nonce', '')), nonce) or claims.get('email_verified') is not True:
                raise ValueError('Invalid identity')
            sub = claims['sub']
            if not isinstance(sub, str) or not sub or len(sub)>255:
                raise ValueError('Invalid subject')
            address = email({'email': claims.get('email', '')})
        except (ValueError, KeyError):
            return error('無法確認 Google 身分，請重新登入。', 401)
        user = db().execute('SELECT u.* FROM users u JOIN google_identities i ON i.user_id=u.id WHERE i.sub=%s', (sub,)).fetchone()
        if not user:
            # Only Google-hosted email ownership is authoritative for email-based linking.
            if not (address.endswith('@gmail.com') or claims.get('hd')):
                return error('此 Google 帳號使用第三方信箱，請先使用 Email 註冊及驗證。', 403)
            db().execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('google:' + address,))
            user = db().execute('SELECT * FROM users WHERE email=%s FOR UPDATE', (address,)).fetchone()
            if user and (not user['active'] or user['is_npc']):
                return error('此帳號目前無法登入。', 403)
            if user and db().execute('SELECT 1 FROM google_identities WHERE user_id=%s', (user['id'],)).fetchone():
                return error('此 Email 已連結其他 Google 帳號。', 409)
            if user and not user['verified']:
                # Google has proven ownership of this Gmail/Workspace address.
                # Discard credentials and profile supplied by a potential pre-registrant.
                name = str(claims.get('name') or address.split('@')[0]).strip()[:40] or 'Google 成員'
                user = db().execute('UPDATE users SET password_hash=%s,name=%s,bio=%s,verified=TRUE WHERE id=%s RETURNING *',
                    (generate_password_hash(secrets.token_urlsafe(48)), name, '', user['id'])).fetchone()
                db().execute('DELETE FROM sessions WHERE user_id=%s', (user['id'],))
                db().execute('UPDATE tokens SET used=TRUE WHERE user_id=%s', (user['id'],))
                db().execute("UPDATE mail_jobs SET status='superseded' WHERE user_id=%s AND status='pending'", (user['id'],))
            if not user:
                if settings().get('REGISTRATION_OPEN', 'true') != 'true':
                    return error('目前暫停建立新帳號。', 403)
                name = str(claims.get('name') or address.split('@')[0]).strip()[:40] or 'Google 成員'
                user = db().execute('INSERT INTO users(id,email,name,password_hash,verified) VALUES(%s,%s,%s,%s,TRUE) RETURNING *',
                    (uuid.uuid4(), address, name, generate_password_hash(secrets.token_urlsafe(48)))).fetchone()
            else:
                user = db().execute('UPDATE users SET verified=TRUE WHERE id=%s RETURNING *', (user['id'],)).fetchone()
            db().execute('INSERT INTO google_identities VALUES(%s,%s)', (sub, user['id']))
        if not user['active'] or not user['verified']:
            return error('此帳號目前無法登入。', 403)
        raw = secrets.token_urlsafe(40)
        db().execute("INSERT INTO sessions VALUES(%s,%s,now()+interval '24 hours')", (digest(raw), user['id']))
        session.clear(); session['sid'] = raw; session['csrf'] = secrets.token_urlsafe(32)
        return jsonify(user=public_user(user), csrf=session['csrf'])

    @app.get('/api/health')
    def health():
        db().execute('SELECT 1')
        return jsonify(status='ok', database='postgresql', version='0.1.0', build=app.config['BUILD_ID'])

    @app.post('/api/register')
    def register():
        data = body_data(); address = email(data); pwd = password(data); name = text(data, 'name', 40)
        if not limit('register-ip:' + str(ip()), 10, 3600):
            return error('申請次數過多，請稍後再試。', 429)
        cfg = settings()
        if cfg.get('REGISTRATION_OPEN') != 'true':
            return error('目前暫停新帳號註冊，請稍後再試。', 403)
        if not limit('mail-hour:' + address, 5, 3600) or not limit('mail-minute:' + address, 1, 60):
            return error('請稍候 60 秒再申請驗證信。', 429)
        db().execute('INSERT INTO users(id,email,name,password_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(email) DO NOTHING', (str(uuid.uuid4()), address, name, generate_password_hash(pwd)))
        db().commit()
        user = db().execute('SELECT * FROM users WHERE email=%s FOR UPDATE', (address,)).fetchone()
        if not user['verified'] and user['active']:
            sent = issue(user, 'verify')
        else:
            sent = bool(cfg.get('RESEND_API_KEY') and cfg.get('MAIL_FROM'))
        return jsonify(message='如果此信箱符合申請條件，我們已安排寄出驗證信。', sent=sent), 202

    @app.post('/api/email')
    def request_email():
        data = body_data(); address = email(data)
        purpose = 'reset' if data.get('purpose') == 'reset' else 'verify'
        if not limit('mail-ip:' + str(ip()), 20, 3600) or not limit('mail-hour:' + address, 5, 3600) or not limit('mail-minute:' + address, 1, 60):
            return error('申請次數過多，請稍候再試。', 429)
        user = db().execute('SELECT * FROM users WHERE email=%s FOR UPDATE', (address,)).fetchone()
        sent = bool(settings().get('RESEND_API_KEY') and settings().get('MAIL_FROM'))
        if user and user['active'] and user['verified'] == (purpose == 'reset'):
            sent = issue(user, purpose)
        return jsonify(message='如果信箱符合條件，我們已安排寄出信件。', sent=sent), 202

    @app.post('/api/verify')
    def verify():
        data = body_data(); token = str(data.get('token', '')); pwd = password(data)
        row = db().execute("UPDATE tokens SET used=TRUE WHERE token_hash=%s AND purpose='verify' AND NOT used AND expires_at>now() RETURNING user_id", (digest(token),)).fetchone()
        if not row:
            return error('驗證連結無效、已使用或已過期，請重新申請。')
        db().execute('UPDATE users SET verified=TRUE,password_hash=%s WHERE id=%s AND active AND NOT verified', (generate_password_hash(pwd), row['user_id']))
        db().execute('DELETE FROM sessions WHERE user_id=%s', (row['user_id'],))
        db().execute('UPDATE tokens SET used=TRUE WHERE user_id=%s', (row['user_id'],))
        return jsonify(message='信箱驗證完成，現在可以登入了。')

    @app.post('/api/reset')
    def reset():
        data = body_data(); pwd = password(data)
        row = db().execute("UPDATE tokens SET used=TRUE WHERE token_hash=%s AND purpose='reset' AND NOT used AND expires_at>now() RETURNING user_id", (digest(str(data.get('token', ''))),)).fetchone()
        if not row:
            return error('重設連結無效、已使用或已過期。')
        db().execute('UPDATE users SET password_hash=%s WHERE id=%s AND active', (generate_password_hash(pwd), row['user_id']))
        db().execute('DELETE FROM sessions WHERE user_id=%s', (row['user_id'],))
        session.clear()
        return jsonify(message='密碼已更新，請使用新密碼登入。')

    @app.post('/api/login')
    def login():
        data = body_data(); address = email(data); pwd = password(data)
        failure_keys = (digest('login-email:' + address), digest('login-ip:' + str(ip())))
        if db().execute('SELECT 1 FROM limits WHERE key=ANY(%s) AND count>=10 AND expires_at>now() LIMIT 1', (list(failure_keys),)).fetchone():
            return error('嘗試次數過多，請 15 分鐘後再試。', 429)
        user = db().execute('SELECT * FROM users WHERE email=%s', (address,)).fetchone()
        if 'DUMMY_HASH' not in app.config:
            app.config['DUMMY_HASH'] = generate_password_hash('dummy-password-unavailable')
        dummy = app.config['DUMMY_HASH']
        valid = check_password_hash(user['password_hash'] if user else dummy, pwd)
        if not user or not valid or not user['active'] or not user['verified']:
            limit('login-email:' + address, 10, 900)
            limit('login-ip:' + str(ip()), 10, 900)
            return error('無法登入，請確認帳密、信箱驗證及帳號狀態。', 401)
        db().execute('DELETE FROM limits WHERE key=%s', (failure_keys[0],))
        raw = secrets.token_urlsafe(40)
        db().execute("INSERT INTO sessions VALUES(%s,%s,now()+interval '24 hours')", (digest(raw), user['id']))
        session.clear(); session['sid'] = raw; session['csrf'] = secrets.token_urlsafe(32)
        return jsonify(user=public_user(user), csrf=session['csrf'])

    @app.post('/api/logout')
    def logout():
        db().execute('DELETE FROM sessions WHERE token_hash=%s', (digest(session.get('sid', '')),))
        session.clear()
        return jsonify(message='已登出。')

    @app.get('/api/members')
    @required
    def members():
        after = uuid.UUID(request.args['after']) if request.args.get('after') else None
        rows = db().execute('SELECT id,name,bio,created_at,is_npc FROM users WHERE verified AND active AND (%s::uuid IS NULL OR id>%s::uuid) ORDER BY id LIMIT 31', (after, after)).fetchall()
        return jsonify(members=[public_user(u) for u in rows[:30]], next=str(rows[29]['id']) if len(rows)>30 else None)

    @app.patch('/api/profile')
    @required
    def profile():
        data = body_data(); name = text(data, 'name', 40); bio = text(data, 'bio', 300, 0)
        row = db().execute('UPDATE users SET name=%s,bio=%s WHERE id=%s RETURNING *', (name, bio, g.user['id'])).fetchone()
        return jsonify(user=public_user(row))

    post_select = '''SELECT p.id,p.body,p.created_at,p.edited,u.id AS user_id,u.name,
       (SELECT count(*) FROM likes l WHERE l.post_id=p.id)::int AS likes,
       EXISTS(SELECT 1 FROM likes l WHERE l.post_id=p.id AND l.user_id=%s) AS liked,
       (SELECT count(*) FROM comments c WHERE c.post_id=p.id)::int AS comment_count
       FROM posts p JOIN users u ON u.id=p.user_id WHERE u.active'''

    def post_json(row):
        return {**row, 'user_id': str(row['user_id']), 'created_at': row['created_at'].isoformat()}

    @app.get('/api/posts')
    @required
    def posts():
        query = post_select; params = [g.user['id']]
        if request.args.get('q'):
            query += ' AND p.body ILIKE %s'; params.append('%' + request.args['q'][:100] + '%')
        if request.args.get('author'):
            query += ' AND u.id=%s'; params.append(uuid.UUID(request.args['author']))
        if request.args.get('before'):
            query += ' AND p.id<%s'; params.append(int(request.args['before']))
        query += ' ORDER BY p.id DESC LIMIT 21'
        rows = db().execute(query, params).fetchall()
        return jsonify(posts=[post_json(r) for r in rows[:20]], next=rows[19]['id'] if len(rows) > 20 else None)

    @app.post('/api/posts')
    @required
    def create_post():
        data = body_data(); body = text(data, 'body', 3000); rid = uuid.UUID(str(data.get('request_id', '')))
        if not limit('post:' + str(g.user['id']), 30, 60):
            return error('發布太頻繁，請稍候。', 429)
        row = db().execute('INSERT INTO posts(user_id,body,request_id) VALUES(%s,%s,%s) ON CONFLICT(user_id,request_id) DO UPDATE SET request_id=excluded.request_id RETURNING id', (g.user['id'], body, rid)).fetchone()
        return jsonify(post=post_json(db().execute(post_select + ' AND p.id=%s', (g.user['id'], row['id'])).fetchone())), 201

    @app.route('/api/posts/<int:post_id>', methods=['PATCH', 'DELETE'])
    @required
    def change_post(post_id):
        if request.method == 'DELETE':
            row = db().execute('DELETE FROM posts WHERE id=%s AND user_id=%s RETURNING id', (post_id, g.user['id'])).fetchone()
        else:
            body = text(body_data(), 'body', 3000)
            row = db().execute('UPDATE posts SET body=%s,edited=TRUE WHERE id=%s AND user_id=%s RETURNING id', (body, post_id, g.user['id'])).fetchone()
        return jsonify(ok=True) if row else error('內容不存在，或你沒有修改權限。', 403)

    @app.put('/api/posts/<int:post_id>/like')
    @required
    def like(post_id):
        if not db().execute('SELECT 1 FROM posts WHERE id=%s', (post_id,)).fetchone():
            return error('貼文已不存在。', 404)
        if body_data().get('liked') is True:
            db().execute('INSERT INTO likes VALUES(%s,%s) ON CONFLICT DO NOTHING', (post_id, g.user['id']))
        else:
            db().execute('DELETE FROM likes WHERE post_id=%s AND user_id=%s', (post_id, g.user['id']))
        row = db().execute(post_select + ' AND p.id=%s', (g.user['id'], post_id)).fetchone()
        return jsonify(post=post_json(row)) if row else error('貼文已不存在。', 404)

    @app.get('/api/posts/<int:post_id>/comments')
    @required
    def comments(post_id):
        if not db().execute('SELECT 1 FROM posts WHERE id=%s', (post_id,)).fetchone():
            return error('貼文已不存在。', 404)
        after = int(request.args.get('after', 0))
        rows = db().execute('SELECT c.id,c.body,c.created_at,u.id AS user_id,u.name FROM comments c JOIN users u ON u.id=c.user_id WHERE post_id=%s AND c.id>%s AND u.active ORDER BY c.id LIMIT 21', (post_id, after)).fetchall()
        return jsonify(comments=[{**r, 'user_id': str(r['user_id']), 'created_at': r['created_at'].isoformat()} for r in rows[:20]], next=rows[19]['id'] if len(rows) > 20 else None)

    @app.post('/api/posts/<int:post_id>/comments')
    @required
    def add_comment(post_id):
        data = body_data(); body = text(data, 'body', 1000); rid = uuid.UUID(str(data.get('request_id', '')))
        if not limit('comment:' + str(g.user['id']), 60, 60):
            return error('留言太頻繁，請稍候。', 429)
        if not db().execute('SELECT id FROM posts WHERE id=%s FOR KEY SHARE', (post_id,)).fetchone():
            return error('貼文已不存在。', 404)
        db().execute('INSERT INTO comments(post_id,user_id,body,request_id) VALUES(%s,%s,%s,%s) ON CONFLICT(user_id,request_id) DO NOTHING', (post_id, g.user['id'], body, rid))
        return jsonify(ok=True), 201

    @app.delete('/api/comments/<int:comment_id>')
    @required
    def delete_comment(comment_id):
        row = db().execute('DELETE FROM comments WHERE id=%s AND user_id=%s RETURNING id', (comment_id, g.user['id'])).fetchone()
        return jsonify(ok=True) if row else error('內容不存在，或你沒有刪除權限。', 403)

    thread_select = '''SELECT u.id,u.name,u.bio,u.is_npc,u.created_at,
       last.id AS last_id,last.body AS last_body,last.created_at AS last_at,last.sender_id AS last_sender,
       (SELECT count(*) FROM messages m2 WHERE m2.sender_id=u.id AND m2.recipient_id=%s AND m2.read_at IS NULL)::int AS unread
       FROM users u
       JOIN LATERAL (SELECT m.id,m.body,m.created_at,m.sender_id FROM messages m
         WHERE (m.sender_id=%s AND m.recipient_id=u.id) OR (m.sender_id=u.id AND m.recipient_id=%s)
         ORDER BY m.id DESC LIMIT 1) last ON TRUE
       WHERE u.id<>%s AND u.active AND u.verified'''

    @app.get('/api/conversations')
    @required
    def conversations():
        me = g.user['id']
        before = int(request.args.get('before', 0)) or None
        rows = db().execute(thread_select + ' AND (%s::bigint IS NULL OR last.id<%s::bigint) ORDER BY last.id DESC LIMIT 51', (me, me, me, me, before, before)).fetchall()
        threads = [{**public_user(r), 'last': r['last_body'], 'last_at': r['last_at'].isoformat(),
                    'last_mine': r['last_sender'] == me, 'unread': r['unread']} for r in rows[:50]]
        unread = db().execute('SELECT count(*) AS n FROM messages m JOIN users u ON u.id=m.sender_id WHERE m.recipient_id=%s AND m.read_at IS NULL AND u.active AND u.verified', (me,)).fetchone()['n']
        return jsonify(threads=threads, unread=unread, next=rows[49]['last_id'] if len(rows)>50 else None)

    @app.get('/api/messages/<uuid:other_id>')
    @required
    def messages(other_id):
        me = g.user['id']
        before = int(request.args.get('before', 0)) or None
        after = int(request.args['after']) if 'after' in request.args else None
        rows = db().execute('''SELECT id,body,created_at,sender_id FROM messages
            WHERE ((sender_id=%s AND recipient_id=%s) OR (sender_id=%s AND recipient_id=%s))
              AND (%s::bigint IS NULL OR id<%s::bigint)
              AND (%s::bigint IS NULL OR id>%s::bigint)
            ORDER BY ''' + ('id ASC' if after is not None else 'id DESC') + ' LIMIT 51', (me, other_id, other_id, me, before, before, after, after)).fetchall()
        delivered = rows[:50]
        if delivered:
            db().execute('UPDATE messages SET read_at=now() WHERE sender_id=%s AND recipient_id=%s AND read_at IS NULL AND id=ANY(%s)', (other_id, me, [r['id'] for r in delivered]))
            db().commit()
        items = [{'id': r['id'], 'mine': r['sender_id'] == me, 'body': r['body'], 'at': r['created_at'].isoformat()}
                 for r in (delivered if after is not None else reversed(delivered))]
        return jsonify(messages=items, next=rows[49]['id'] if after is None and len(rows)>50 else None,
                       next_after=rows[49]['id'] if after is not None and len(rows)>50 else None)

    @app.post('/api/messages')
    @required
    def send_message():
        data = body_data(); body = text(data, 'body', 1000); rid = uuid.UUID(str(data.get('request_id', '')))
        try:
            to = uuid.UUID(str(data.get('to', '')))
        except ValueError:
            raise ValueError('收件對象不正確。')
        if to == g.user['id']:
            raise ValueError('不能傳訊息給自己。')
        if not limit('msg:' + str(g.user['id']), 30, 60):
            return error('傳訊息太頻繁，請稍候。', 429)
        if not db().execute('SELECT 1 FROM users WHERE id=%s AND verified AND active', (to,)).fetchone():
            return error('找不到這位成員，或對方已停用。', 404)
        row = db().execute('''INSERT INTO messages(sender_id,recipient_id,body,request_id) VALUES(%s,%s,%s,%s)
            ON CONFLICT(sender_id,request_id) DO UPDATE SET request_id=excluded.request_id
            RETURNING id,body,recipient_id,created_at''', (g.user['id'], to, body, rid)).fetchone()
        if row['recipient_id'] != to:
            return error('這次傳送編號已用於其他對話，請重新傳送。', 409)
        return jsonify(message={'id': row['id'], 'mine': True, 'body': row['body'], 'at': row['created_at'].isoformat()}), 201

    @app.get('/', defaults={'path': ''})
    @app.get('/<path:path>')
    def frontend(path):
        if path.startswith(('api/', '.')):
            return error('找不到這個內容。', 404)
        dist = ROOT / 'dist'
        if path and (dist / path).is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, 'index.html')

    return app


if __name__ == '__main__':
    from waitress import serve
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    initialize()
    threading.Thread(target=mail_loop, daemon=True).start()
    print('Connect ready at http://127.0.0.1:5080', flush=True)
    serve(create_app(), host='127.0.0.1', port=5080, threads=8, clear_untrusted_proxy_headers=True)
