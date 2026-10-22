"""Local-only browser regression harness. Uses disposable data; never sends mail/AI requests."""
import json
import secrets
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from flask import request,session
from psycopg import sql
from psycopg.conninfo import make_conninfo
from werkzeug.serving import make_server

root=server.ROOT
cfg=server.settings();base=dict(cfg);schema='uiqa_'+uuid.uuid4().hex
with server.connect(base) as conn:
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
cfg.update(DATABASE_URL=make_conninfo(base['DATABASE_URL'],options='-c search_path='+schema),SECRET_KEY=secrets.token_urlsafe(32),RESEND_API_KEY='',MAIL_FROM='',GOOGLE_CLIENT_ID='',PUBLIC_URL='http://127.0.0.1:5091',COOKIE_SECURE='false',REGISTRATION_OPEN='false')
server.settings=lambda:cfg
server.initialize()
me,slow,fast=[uuid.uuid4() for _ in range(3)]
with server.connect() as conn:
    for uid,name in [(me,'QA Browser'),(slow,'QA Slow Contact'),(fast,'QA Fast Contact')]:
        conn.execute('INSERT INTO users(id,email,name,password_hash,verified) VALUES(%s,%s,%s,%s,TRUE)',(uid,str(uid)+'@example.test',name,server.generate_password_hash('local-ui-test-password-123')))
    for uid,text in [(slow,'Message from slow contact'),(fast,'Message from fast contact')]:
        conn.execute('INSERT INTO messages(sender_id,recipient_id,body,request_id) VALUES(%s,%s,%s,%s)',(uid,me,text,uuid.uuid4()))
app=server.create_app({'TESTING':True,'SESSION_COOKIE_SECURE':False})
@app.before_request
def seed_browser_session():
    if request.path=='/' and not session.get('sid'):
        sid=secrets.token_urlsafe(40)
        with server.connect() as conn:
            conn.execute("INSERT INTO sessions VALUES(%s,%s,now()+interval '1 hour')",(server.digest(sid),me))
        session['sid']=sid;session['csrf']=secrets.token_urlsafe(32)
@app.after_request
def delay_slow_contact(response):
    if request.path=='/api/messages/'+str(slow) and 'after' not in request.args:
        time.sleep(2)
        counter=root/'.runtime/ui-slow-count.txt'
        counter.write_text(str(int(counter.read_text() or '0')+1),encoding='ascii')
        print('SLOW_RESPONSE_FINISHED',flush=True)
    return response
(root/'.runtime/ui-harness.json').write_text(json.dumps({'url':cfg['PUBLIC_URL'],'schema':schema,'slow':str(slow),'fast':str(fast)}),encoding='utf-8')
(root/'.runtime/ui-slow-count.txt').write_text('0',encoding='ascii')
print('UI_HARNESS_READY http://127.0.0.1:5091',flush=True)
try:
    make_server('127.0.0.1',5091,app,threaded=True).serve_forever()
finally:
    with server.connect(base) as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
    print('UI_HARNESS_CLEANED',flush=True)
