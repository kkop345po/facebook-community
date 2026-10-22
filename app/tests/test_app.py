import uuid
from urllib.parse import urlparse, parse_qs

import psycopg
import pytest
from psycopg import sql

import server


@pytest.fixture
def env(monkeypatch):
    cfg = server.settings()
    namespace = 'test_' + uuid.uuid4().hex
    with server.connect(cfg) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(namespace)))
    cfg = dict(cfg, DATABASE_URL=cfg['DATABASE_URL'] + '?options=-csearch_path%3D' + namespace,
               RESEND_API_KEY='', MAIL_FROM='', PUBLIC_URL='http://localhost:5080',
               INVITE_CODE='test-invite', REGISTRATION_OPEN='true')
    monkeypatch.setattr(server, 'settings', lambda: cfg)
    server.initialize()
    app = server.create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False})
    yield app
    with server.connect(cfg) as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(namespace)))


def client(app):
    c = app.test_client()
    token = c.get('/api/session').json['csrf']
    return c, token


def call(c, csrf, path, data=None, method='POST'):
    if path == 'verify' and data is not None:
        data = dict(data, password=data.get('password', 'a-strong-password-123'))
    return c.open('/api/' + path, method=method, json=data or {}, headers={'X-CSRF-Token': csrf})


def register(c, csrf, name, address):
    result = call(c, csrf, 'register', {'name': name, 'email': address, 'password': 'a-strong-password-123'})
    assert result.status_code == 202
    assert result.json['sent'] is False
    with server.connect() as conn:
        row = conn.execute('SELECT encrypted_payload FROM mail_jobs m JOIN users u ON m.user_id=u.id WHERE u.email=%s ORDER BY m.created_at DESC LIMIT 1', (address,)).fetchone()
    url = server.cipher().decrypt(row['encrypted_payload'].encode()).decode()
    return parse_qs(urlparse(url).query)['token'][0]


def verified(app, name, address):
    c, csrf = client(app)
    token = register(c, csrf, name, address)
    assert call(c, csrf, 'verify', {'token': token}).status_code == 200
    r = call(c, csrf, 'login', {'email': address, 'password': 'a-strong-password-123'})
    assert r.status_code == 200
    return c, r.json['csrf'], r.json['user']


def test_member_lifecycle_and_permissions(env):
    alice, a, au = verified(env, 'Alice', 'alice@example.test')
    bob, b, bu = verified(env, 'Bob', 'bob@example.test')
    rid = str(uuid.uuid4())
    r = call(alice, a, 'posts', {'body': 'Hello <script>alert(1)</script>', 'request_id': rid})
    assert r.status_code == 201
    pid = r.json['post']['id']
    assert call(alice, a, 'posts', {'body': 'same request', 'request_id': rid}).json['post']['id'] == pid
    feed = bob.get('/api/posts').json['posts']
    assert len(feed) == 1 and feed[0]['body'].startswith('Hello <script>')
    assert call(bob, b, f'posts/{pid}', {'body': 'stolen'}, 'PATCH').status_code == 403
    assert call(bob, b, f'posts/{pid}', {}, 'DELETE').status_code == 403
    assert call(bob, b, f'posts/{pid}/like', {'liked': True}, 'PUT').json['post']['likes'] == 1
    assert call(bob, b, f'posts/{pid}/like', {'liked': True}, 'PUT').json['post']['likes'] == 1
    assert call(bob, b, f'posts/{pid}/like', {'liked': False}, 'PUT').json['post']['likes'] == 0
    crid = str(uuid.uuid4())
    assert call(bob, b, f'posts/{pid}/comments', {'body': 'Nice!', 'request_id': crid}).status_code == 201
    call(bob, b, f'posts/{pid}/comments', {'body': 'Nice!', 'request_id': crid})
    comments = alice.get(f'/api/posts/{pid}/comments').json['comments']
    assert len(comments) == 1
    assert call(alice, a, f'comments/{comments[0]["id"]}', {}, 'DELETE').status_code == 403
    assert call(bob, b, f'comments/{comments[0]["id"]}', {}, 'DELETE').status_code == 200
    assert call(alice, a, f'posts/{pid}', {'body': 'Edited'}, 'PATCH').status_code == 200
    assert bob.get('/api/posts?q=Edited').json['posts'][0]['edited']
    assert call(alice, a, f'posts/{pid}', {}, 'DELETE').status_code == 200
    assert bob.get('/api/posts').json['posts'] == []
    assert call(bob, b, f'posts/{pid}/comments', {'body': 'late', 'request_id': str(uuid.uuid4())}).status_code == 404


def test_unverified_csrf_and_token_reuse(env):
    c, csrf = client(env)
    token = register(c, csrf, 'Pending', 'pending@example.test')
    assert c.get('/api/posts').status_code == 401
    assert call(c, csrf, 'login', {'email': 'pending@example.test', 'password': 'a-strong-password-123'}).status_code == 401
    assert c.post('/api/verify', json={'token': token}).status_code == 403
    assert call(c, csrf, 'verify', {'token': token}).status_code == 200
    assert call(c, csrf, 'verify', {'token': token}).status_code == 400
    assert call(c, csrf, 'reset', {'token': token, 'password': 'another-strong-password'}).status_code == 400
    assert call(c, csrf, 'verify', {'token': 'fake'}).status_code == 400


def test_expired_token_and_revoked_session(env):
    c, csrf = client(env)
    token = register(c, csrf, 'Expired', 'expired@example.test')
    with server.connect() as conn:
        conn.execute("UPDATE tokens SET expires_at=now()-interval '1 second'")
    assert call(c, csrf, 'verify', {'token': token}).status_code == 400
    d, token2, user = verified(env, 'Valid', 'valid@example.test')
    old_cookie = d.get_cookie('session').value
    assert call(d, token2, 'logout').status_code == 200
    replay = env.test_client(); replay.set_cookie('session', old_cookie)
    assert replay.get('/api/posts').status_code == 401


def test_password_reset_invalidates_all_sessions(env):
    c, csrf, user = verified(env, 'Reset', 'reset@example.test')
    old_cookie = c.get_cookie('session').value
    with server.connect() as conn:
        conn.execute('DELETE FROM limits')
    assert call(c, csrf, 'email', {'email': 'reset@example.test', 'purpose': 'reset'}).status_code == 202
    with server.connect() as conn:
        row = conn.execute("SELECT encrypted_payload FROM mail_jobs WHERE purpose='reset'").fetchone()
    token = parse_qs(urlparse(server.cipher().decrypt(row['encrypted_payload'].encode()).decode()).query)['token'][0]
    assert call(c, csrf, 'reset', {'token': token, 'password': 'new-password-123456'}).status_code == 200
    replay = env.test_client(); replay.set_cookie('session', old_cookie)
    assert replay.get('/api/posts').status_code == 401
    fresh, fcsrf = client(env)
    assert call(fresh, fcsrf, 'reset', {'token': token, 'password': 'new-password-987654'}).status_code == 400
    assert call(fresh, fcsrf, 'login', {'email': 'reset@example.test', 'password': 'a-strong-password-123'}).status_code == 401
    assert call(fresh, fcsrf, 'login', {'email': 'reset@example.test', 'password': 'new-password-123456'}).status_code == 200


def test_pagination_and_persistent_data(env):
    c, csrf, user = verified(env, 'Pages', 'pages@example.test')
    with server.connect() as conn:
        for i in range(45):
            conn.execute('INSERT INTO posts(user_id,body) VALUES(%s,%s)', (user['id'], f'Post {i}'))
    ids=[]; path='/api/posts'
    while True:
        r=c.get(path).json; ids += [p['id'] for p in r['posts']]
        if not r['next']: break
        path='/api/posts?before='+str(r['next'])
    assert len(ids)==len(set(ids))==45
    # A new application instance sees the same persisted database records.
    clone = server.create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False}).test_client()
    clone.set_cookie('session', c.get_cookie('session').value)
    assert len(clone.get('/api/posts').json['posts']) == 20


def test_open_registration_email_cooldown_and_private_settings(env):
    c, csrf = client(env)
    # Registration requires neither an invite code nor allowlist membership.
    assert call(c, csrf, 'register', {'name':'Open','email':'open@example.test','password':'a-strong-password-123'}).status_code == 202
    assert c.get('/api/posts').status_code == 401
    register(c, csrf, 'Limited', 'limited@example.test')
    assert call(c, csrf, 'email', {'email': 'limited@example.test'}).status_code == 429
    for path in ('/.env','/.pgdata/PG_VERSION','/api/missing'):
        r=c.get(path);assert r.status_code==404
        assert 'DATABASE_URL' not in r.get_data(as_text=True)
    assert c.get('/api/session').headers['Cache-Control']=='no-store'


def test_profile_limits_and_origin_guard(env):
    c, csrf, user = verified(env, 'Profile', 'profile@example.test')
    assert call(c, csrf, 'profile', {'name': 'New Name', 'bio':'Hello'}, 'PATCH').json['user']['name']=='New Name'
    assert c.get('/api/session').json['user']['bio']=='Hello'
    assert call(c, csrf, 'posts', {'body':'  ','request_id':str(uuid.uuid4())}).status_code==400
    response=c.post('/api/logout',json={},headers={'X-CSRF-Token':csrf,'Origin':'https://evil.test'})
    assert response.status_code==403


def test_private_message_privacy_pagination_and_retry(env):
    a, ac, alice = verified(env, 'Alice', 'a@message.test')
    b, bc, bob = verified(env, 'Bob', 'b@message.test')
    outsider, oc, _ = verified(env, 'Outsider', 'c@message.test')
    rid = str(uuid.uuid4())
    first = call(a, ac, 'messages', {'to': bob['id'], 'body': 'Hello Bob', 'request_id': rid})
    assert first.status_code == 201
    retry = call(a, ac, 'messages', {'to': bob['id'], 'body': 'different retry', 'request_id': rid})
    assert retry.json['message'] == first.json['message']
    assert b.get('/api/conversations').json['unread'] == 1
    assert outsider.get('/api/messages/' + alice['id']).json['messages'] == []
    assert b.get('/api/messages/' + alice['id']).json['messages'][0]['body'] == 'Hello Bob'
    assert b.get('/api/conversations').json['unread'] == 0
    with server.connect() as conn:
        for i in range(55):
            conn.execute('INSERT INTO messages(sender_id,recipient_id,body,request_id) VALUES(%s,%s,%s,%s)', (alice['id'], bob['id'], str(i), uuid.uuid4()))
    latest = b.get('/api/messages/' + alice['id']).json
    older = b.get('/api/messages/' + alice['id'] + '?before=' + str(latest['next'])).json
    assert len(latest['messages']) == 50 and len(older['messages']) == 6
    assert len({m['id'] for m in latest['messages'] + older['messages']}) == 56


def test_google_login_challenge_and_identity(env, monkeypatch):
    cfg = server.settings()
    cfg['GOOGLE_CLIENT_ID'] = 'test.apps.googleusercontent.com'
    c, csrf = client(env)
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims = {'sub':'google-test-123','email':'google.member@gmail.com','email_verified':True,'nonce':challenge['nonce'],'name':'Google Member'}
    monkeypatch.setattr(server.google_id_token, 'verify_oauth2_token', lambda credential, transport, audience: dict(claims))
    result = call(c, csrf, 'auth/google', {'credential':'signed-token'})
    assert result.status_code == 200
    identity = result.json['user']['id']
    assert c.get('/api/session').json['user']['id'] == identity
    csrf = result.json['csrf']
    assert call(c, csrf, 'auth/google', {'credential':'signed-token'}).status_code == 401
    call(c, csrf, 'logout')
    csrf = c.get('/api/session').json['csrf']
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims['nonce'] = 'wrong-nonce'
    assert call(c, csrf, 'auth/google', {'credential':'signed-token'}).status_code == 401
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims['nonce'] = challenge['nonce']
    claims['email'] = 'changed@gmail.com'
    assert call(c, csrf, 'auth/google', {'credential':'signed-token'}).json['user']['id'] == identity


def test_google_rejects_invalid_and_non_authoritative_identity(env, monkeypatch):
    cfg = server.settings(); cfg['GOOGLE_CLIENT_ID'] = 'test.apps.googleusercontent.com'
    c, csrf = client(env)
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims = {'sub':'third-party','email':'third@example.test','email_verified':True,'nonce':challenge['nonce']}
    monkeypatch.setattr(server.google_id_token, 'verify_oauth2_token', lambda *args: dict(claims))
    assert call(c, csrf, 'auth/google', {'credential':'token'}).status_code == 403
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims.update(email='unverified@gmail.com',email_verified=False,nonce=challenge['nonce'])
    assert call(c, csrf, 'auth/google', {'credential':'token'}).status_code == 401
    def invalid(*args):
        raise ValueError('Bad signature/audience/expiry')
    monkeypatch.setattr(server.google_id_token, 'verify_oauth2_token', invalid)
    call(c, csrf, 'auth/google/challenge')
    assert call(c, csrf, 'auth/google', {'credential':'invalid'}).status_code == 401


def test_google_claims_pending_account_safely_and_rejects_disabled_accounts(env, monkeypatch):
    cfg = server.settings(); cfg['GOOGLE_CLIENT_ID'] = 'test.apps.googleusercontent.com'
    c, csrf = client(env)
    old_token = register(c, csrf, 'Pending', 'pending.google@gmail.com')
    claims = {'sub':'pending-google','email':'pending.google@gmail.com','email_verified':True}
    monkeypatch.setattr(server.google_id_token, 'verify_oauth2_token', lambda *args: dict(claims))
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims['nonce'] = challenge['nonce']
    result = call(c, csrf, 'auth/google', {'credential':'token'})
    assert result.status_code == 200
    csrf = result.json['csrf']
    assert result.json['user']['name'] == 'pending.google'
    assert call(c, csrf, 'verify', {'token':old_token}).status_code == 400
    other, other_csrf = client(env)
    assert call(other, other_csrf, 'login', {'email':claims['email'], 'password':'a-strong-password-123'}).status_code == 401
    with server.connect() as conn:
        assert conn.execute('SELECT verified FROM users WHERE email=%s', (claims['email'],)).fetchone()['verified'] is True
        assert conn.execute("SELECT count(*) AS n FROM mail_jobs m JOIN users u ON u.id=m.user_id WHERE u.email=%s AND m.status='pending'", (claims['email'],)).fetchone()['n'] == 0
        conn.execute('UPDATE users SET verified=TRUE,active=FALSE WHERE email=%s', (claims['email'],))
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims['nonce'] = challenge['nonce']
    assert call(c, csrf, 'auth/google', {'credential':'token'}).status_code == 403
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims['nonce'] = challenge['nonce']
    with server.connect() as conn:
        conn.execute("UPDATE google_challenges SET expires_at=now()-interval '1 minute'")
    assert call(c, csrf, 'auth/google', {'credential':'token'}).status_code == 401


def test_successful_logins_do_not_consume_failed_login_quota(env):
    c, csrf, user = verified(env, 'Member', 'quota@example.test')
    for _ in range(11):
        result = call(c, csrf, 'login', {'email':'quota@example.test','password':'a-strong-password-123'})
        assert result.status_code == 200
        csrf = result.json['csrf']
    for _ in range(10):
        assert call(c, csrf, 'login', {'email':'quota@example.test','password':'incorrect-password-123'}).status_code == 401
    assert call(c, csrf, 'login', {'email':'quota@example.test','password':'a-strong-password-123'}).status_code == 429
    with server.connect() as conn:
        conn.execute("UPDATE limits SET expires_at=now()-interval '1 second'")
    assert call(c, csrf, 'login', {'email':'quota@example.test','password':'a-strong-password-123'}).status_code == 200


def test_cache_policy_separates_static_assets_from_private_data(env):
    c, csrf, _ = verified(env, 'Cache', 'cache@example.test')
    for path in ('/api/session','/api/posts','/api/conversations'):
        response = c.get(path)
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store'
    assets = list((server.ROOT / 'dist' / 'assets').glob('*.js'))
    assert assets, 'Build the frontend before running cache verification'
    path = '/assets/' + assets[0].name
    response = c.get(path)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'public, max-age=31536000, immutable'
    assert 'Set-Cookie' not in response.headers
    revalidated = c.get(path, headers={'If-None-Match': response.headers['ETag']})
    assert revalidated.status_code == 304
    assert 'immutable' in revalidated.headers['Cache-Control']
    assert c.get('/').headers['Cache-Control'] == 'no-cache'
    assert c.get('/profile').headers['Cache-Control'] == 'no-cache'


def test_malformed_and_oversized_private_requests(env):
    c, csrf, _ = verified(env, 'Input', 'input@example.test')
    assert call(c, csrf, 'messages', {'to':'bad-id','body':'hello','request_id':str(uuid.uuid4())}).status_code == 400
    assert c.get('/api/messages/' + str(uuid.uuid4()) + '?before=not-a-number').status_code == 400
    response = call(c, csrf, 'posts', {'body':'x'*40000,'request_id':str(uuid.uuid4())})
    assert response.status_code == 413
    assert response.is_json


@pytest.mark.parametrize('provider_status,expected', [(403,'failed'), (429,'pending'), (503,'pending')])
def test_mail_retries_only_transient_errors(env, monkeypatch, provider_status, expected):
    from types import SimpleNamespace
    c, csrf = client(env)
    register(c, csrf, 'Mail', 'mail-retry@example.test')
    cfg = server.settings(); cfg.update(RESEND_API_KEY='mock-test-key', MAIL_FROM='test@example.test')
    calls = []
    def provider(*args, **kwargs):
        calls.append(kwargs['headers']['Idempotency-Key'])
        return SimpleNamespace(ok=False, status_code=provider_status)
    monkeypatch.setattr(server.requests, 'post', provider)
    with server.connect() as conn:
        job = conn.execute('SELECT id FROM mail_jobs').fetchone()['id']
    assert server.dispatch_mail(job) is False
    with server.connect() as conn:
        row = conn.execute('SELECT status,attempts,retry_at>now() AS delayed FROM mail_jobs WHERE id=%s', (job,)).fetchone()
        assert row['status'] == expected and row['attempts'] == 1
        if expected == 'pending':
            assert row['delayed']
            conn.execute('UPDATE mail_jobs SET retry_at=now() WHERE id=%s', (job,))
    server.dispatch_mail(job)
    assert len(calls) == (1 if expected == 'failed' else 2)
    assert len(set(calls)) == 1


def test_used_verification_link_is_not_emailed_again(env, monkeypatch):
    c, csrf = client(env)
    token = register(c, csrf, 'Mail', 'mail-expired@example.test')
    assert call(c, csrf, 'verify', {'token':token}).status_code == 200
    cfg = server.settings(); cfg.update(RESEND_API_KEY='mock-test-key', MAIL_FROM='test@example.test')
    def forbidden(*args, **kwargs):
        pytest.fail('Used verification links must never be sent')
    monkeypatch.setattr(server.requests, 'post', forbidden)
    assert server.dispatch_mail() is False
    with server.connect() as conn:
        assert conn.execute('SELECT status FROM mail_jobs').fetchone()['status'] == 'expired'


def test_resending_private_message_cannot_change_recipient(env):
    alice, csrf, _ = verified(env, 'Alice', 'retry-alice@example.test')
    bob, _, bob_user = verified(env, 'Bob', 'retry-bob@example.test')
    carol, _, carol_user = verified(env, 'Carol', 'retry-carol@example.test')
    request_id = str(uuid.uuid4())
    first = call(alice, csrf, 'messages', {'to':bob_user['id'],'body':'For Bob','request_id':request_id})
    assert first.status_code == 201
    changed = call(alice, csrf, 'messages', {'to':carol_user['id'],'body':'For Carol','request_id':request_id})
    assert changed.status_code == 409
    assert carol.get('/api/conversations').json['threads'] == []
    assert bob.get('/api/conversations').json['threads'][0]['last'] == 'For Bob'


def test_disabled_members_cannot_continue_private_messaging(env):
    alice, a, alice_user = verified(env, 'Alice', 'active-msg@example.test')
    bob, b, bob_user = verified(env, 'Bob', 'disabled-msg@example.test')
    with server.connect() as conn:
        conn.execute('UPDATE users SET active=FALSE WHERE id=%s', (bob_user['id'],))
    assert call(alice, a, 'messages', {'to':bob_user['id'],'body':'Hello','request_id':str(uuid.uuid4())}).status_code == 404
    assert call(bob, b, 'messages', {'to':alice_user['id'],'body':'Hello','request_id':str(uuid.uuid4())}).status_code == 401


def test_google_logout_invalidates_the_previous_session(env, monkeypatch):
    cfg = server.settings(); cfg['GOOGLE_CLIENT_ID'] = 'test.apps.googleusercontent.com'
    c, csrf = client(env)
    challenge = call(c, csrf, 'auth/google/challenge').json
    claims = {'sub':'logout-google','email':'logout.google@gmail.com','email_verified':True,'nonce':challenge['nonce'],'name':'Google Member'}
    monkeypatch.setattr(server.google_id_token, 'verify_oauth2_token', lambda *args: dict(claims))
    result = call(c, csrf, 'auth/google', {'credential':'signed-token'})
    assert result.status_code == 200
    old_cookie = c.get_cookie('session').value
    assert call(c, result.json['csrf'], 'logout').status_code == 200
    assert c.get('/api/session').json['user'] is None
    replay = env.test_client(); replay.set_cookie('session',old_cookie)
    assert replay.get('/api/posts').status_code == 401


def test_verification_owner_chooses_password_instead_of_preregistrant(env):
    c, csrf = client(env)
    token = register(c, csrf, 'Owner', 'owner.password@example.test')
    owner_password = 'only-owner-knows-this-password'
    assert call(c, csrf, 'verify', {'token':token,'password':owner_password}).status_code == 200
    assert call(c, csrf, 'login', {'email':'owner.password@example.test','password':'a-strong-password-123'}).status_code == 401
    assert call(c, csrf, 'login', {'email':'owner.password@example.test','password':owner_password}).status_code == 200


def test_successful_mail_is_recorded_and_never_resent(env, monkeypatch):
    from types import SimpleNamespace
    c, csrf = client(env); register(c, csrf, 'Mail', 'mail.success@example.test')
    cfg = server.settings(); cfg.update(RESEND_API_KEY='mock',MAIL_FROM='mock@example.test')
    sent=[]
    def provider(*args, **kwargs):
        sent.append(kwargs['headers']['Idempotency-Key'])
        return SimpleNamespace(ok=True,json=lambda:{'id':'provider-test-id'})
    monkeypatch.setattr(server.requests,'post',provider)
    assert server.dispatch_mail() is True
    assert server.dispatch_mail() is False
    with server.connect() as conn:
        row=conn.execute('SELECT status,provider_id,attempts FROM mail_jobs').fetchone()
    assert row=={'status':'sent','provider_id':'provider-test-id','attempts':1}
    assert len(sent)==1


def test_message_polling_and_read_acknowledges_only_delivered_messages(env):
    c, csrf, me=verified(env,'Reader','reader@example.test')
    other, _, sender=verified(env,'Sender','sender@example.test')
    with server.connect() as conn:
        for i in range(75):
            conn.execute('INSERT INTO messages(sender_id,recipient_id,body,request_id) VALUES(%s,%s,%s,%s)',(sender['id'],me['id'],str(i),uuid.uuid4()))
    latest=c.get('/api/messages/'+sender['id']).json
    assert len(latest['messages'])==50
    assert c.get('/api/conversations').json['unread']==25
    first=c.get('/api/messages/'+sender['id']+'?after=0').json
    second=c.get('/api/messages/'+sender['id']+'?after='+str(first['next_after'])).json
    assert len(first['messages'])==50 and len(second['messages'])==25
    assert len({m['id'] for m in first['messages']+second['messages']})==75
    assert c.get('/api/conversations').json['unread']==0


def test_member_and_conversation_pagination_include_older_contacts(env):
    c, csrf, me=verified(env,'Reader','directory-reader@example.test')
    with server.connect() as conn:
        for i in range(55):
            uid=uuid.uuid4()
            conn.execute('INSERT INTO users(id,email,name,password_hash,verified) VALUES(%s,%s,%s,%s,TRUE)',(uid,f'contact{i}@example.test',f'Contact {i}','unusable-test-hash'))
            conn.execute('INSERT INTO messages(sender_id,recipient_id,body,request_id) VALUES(%s,%s,%s,%s)',(uid,me['id'],str(i),uuid.uuid4()))
    first=c.get('/api/members').json
    second=c.get('/api/members?after='+first['next']).json
    assert len(first['members'])==30 and len(second['members'])==26
    assert len({u['id'] for u in first['members']+second['members']})==56
    first=c.get('/api/conversations').json
    second=c.get('/api/conversations?before='+str(first['next'])).json
    assert len(first['threads'])==50 and len(second['threads'])==5
    assert first['unread']==55 and second['unread']==55


def test_npc_reply_is_deduplicated_and_bounds_its_context(env):
    import npc_worker
    c, csrf, me=verified(env,'Sender','npc-sender@example.test')
    npc, _, npc_user=verified(env,'NPC','npc-test@example.test')
    ids=[]
    for text in ['before','processed','arrived later']:
        ids.append(call(c,csrf,'messages',{'to':npc_user['id'],'body':text,'request_id':str(uuid.uuid4())}).json['message']['id'])
    npc_id=uuid.UUID(npc_user['id']);user_id=uuid.UUID(me['id'])
    context=npc_worker.get_recent_thread(npc_id,user_id,through_id=ids[1])
    assert [m['body'] for m in context]==['before','processed']
    npc_worker.store_reply(npc_id,user_id,'reply once',ids[1])
    npc_worker.store_reply(npc_id,user_id,'duplicate attempt',ids[1])
    with server.connect() as conn:
        incoming=conn.execute('SELECT id,read_at IS NOT NULL AS seen FROM messages WHERE sender_id=%s ORDER BY id',(user_id,)).fetchall()
    assert [m['seen'] for m in incoming]==[True,True,False]
    messages=c.get('/api/messages/'+npc_user['id']).json['messages']
    assert len([m for m in messages if not m['mine']])==1
    assert messages[-1]['body']=='reply once'
