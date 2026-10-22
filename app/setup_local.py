"""Create an isolated, password-protected PostgreSQL cluster for this project."""
from pathlib import Path
import os, secrets, subprocess
from dotenv import dotenv_values, set_key

ROOT=Path(__file__).resolve().parent
env_path=ROOT/'.env'
values=dotenv_values(env_path)
def ensure(name,value):
    if not values.get(name):
        set_key(str(env_path),name,value)
        values[name]=value
    return values[name]

secret=ensure('SECRET_KEY',secrets.token_urlsafe(48))
invite=ensure('INVITE_CODE',secrets.token_urlsafe(12))
ensure('PUBLIC_URL','http://127.0.0.1:5080')
ensure('COOKIE_SECURE','false')
ensure('REGISTRATION_OPEN','true')
ensure('ALLOWED_EMAILS','')
if not values.get('DATABASE_URL'):
    password=secrets.token_urlsafe(32)
    data=ROOT/'.pgdata'
    pg=Path(r'C:\Program Files\PostgreSQL\18\bin')
    runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    if data.exists():
        raise SystemExit('Cluster exists but DATABASE_URL is missing; restore .env before continuing.')
    pw=runtime/'init-password'
    pw.write_text(password,encoding='utf-8')
    try:
        subprocess.run([str(pg/'initdb.exe'),'-D',str(data),'-U','connect_owner','--auth=scram-sha-256','--pwfile',str(pw),'--encoding=UTF8','--locale=C'],check=True,stdout=subprocess.DEVNULL)
    finally:
        pw.unlink(missing_ok=True)
    with (data/'postgresql.conf').open('a',encoding='utf-8') as f:
        f.write("\nlisten_addresses = '127.0.0.1'\nport = 55438\n")
    subprocess.run([str(pg/'pg_ctl.exe'),'-D',str(data),'-l',str(runtime/'postgres.log'),'start'],check=True)
    env=os.environ.copy();env['PGPASSWORD']=password
    subprocess.run([str(pg/'createdb.exe'),'-h','127.0.0.1','-p','55438','-U','connect_owner','connect_community'],env=env,check=True)
    ensure('DATABASE_URL',f'postgresql://connect_owner:{password}@127.0.0.1:55438/connect_community')
(ROOT/'TEST-ACCESS.md').write_text(f'# Internal test access\n\nInvite code: `{invite}`\n\nShare this code only with intended testers. Every tester must verify their own email.\nThe database listens on loopback only; the tunnel exposes only the Flask HTTP service.\n',encoding='utf-8')
print('Local settings prepared. Secrets were not printed.')
