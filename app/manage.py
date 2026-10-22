"""Local-only administration. This file is never served by the website."""
import argparse
import secrets
import uuid
from pathlib import Path
from dotenv import set_key
from werkzeug.security import generate_password_hash
import server

parser = argparse.ArgumentParser(description='Connect internal test administration')
parser.add_argument('--version', action='version', version='connect-admin 0.1.0')
commands = parser.add_subparsers(dest='command', required=True)
commands.add_parser('init', help='Create database tables')
commands.add_parser('create-test-accounts', help='Create two explicitly synthetic, manually approved test accounts')
disable = commands.add_parser('disable', help='Disable an account and revoke all sessions')
disable.add_argument('email')
allow = commands.add_parser('allow-email', help='Allow a tester email to register without an invite code')
allow.add_argument('email')
public = commands.add_parser('set-url', help='Set the public HTTPS URL used in verification emails')
public.add_argument('url')
commands.add_parser('mail-status', help='Show only presence of email configuration; never print secrets')
npc = commands.add_parser('npc-create', help='Create or repair the NPC chat character account')
npc.add_argument('--name', default='小連')
npc.add_argument('--email', default='xiaolian@connect.invalid')
npc.add_argument('--bio', default='站上的小幫手，喜歡聽大家說話。想聊天隨時找我。')
args = parser.parse_args()
root = Path(__file__).resolve().parent

if args.command == 'init':
    server.initialize(); print('Tables ready.')
elif args.command == 'mail-status':
    cfg=server.settings()
    print('RESEND_API_KEY:', 'configured' if cfg.get('RESEND_API_KEY') else 'missing')
    print('MAIL_FROM:', 'configured' if cfg.get('MAIL_FROM') else 'missing')
    print('Delivery mode:', server.mail_mode())
elif args.command == 'npc-create':
    server.initialize()
    address=args.email.strip().lower()
    with server.connect() as conn:
        row=conn.execute('''INSERT INTO users(id,email,name,password_hash,verified,active,is_npc,bio)
            VALUES(%s,%s,%s,%s,TRUE,TRUE,TRUE,%s)
            ON CONFLICT(email) DO UPDATE SET name=excluded.name,verified=TRUE,active=TRUE,is_npc=TRUE,bio=excluded.bio
            RETURNING id''',(str(uuid.uuid4()),address,args.name,generate_password_hash(secrets.token_urlsafe(32)),args.bio)).fetchone()
        conn.execute('UPDATE users SET is_npc=FALSE WHERE is_npc AND email<>%s',(address,))
        conn.execute("INSERT INTO audit(action,target) VALUES('local-admin:npc-create',%s)",(str(row['id']),))
    set_key(str(root/'.env'),'NPC_USER_ID',str(row['id']))
    print('NPC ready:',args.name,address,row['id'])
    print('Reply engine: .\\.venv\\Scripts\\python.exe npc_worker.py')
elif args.command == 'set-url':
    from urllib.parse import urlparse
    url=args.url.rstrip('/'); parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment:
        raise SystemExit('Use a bare HTTPS website origin.')
    set_key(str(root/'.env'),'PUBLIC_URL',url)
    set_key(str(root/'.env'),'COOKIE_SECURE','true')
    print('Public URL and secure cookies configured. Restart the web process.')
elif args.command == 'allow-email':
    cfg=server.settings();emails={v for v in cfg.get('ALLOWED_EMAILS','').split(',') if v};emails.add(args.email.strip().lower())
    set_key(str(root/'.env'),'ALLOWED_EMAILS',','.join(sorted(emails)))
    print('Email added to internal allowlist.')
elif args.command == 'disable':
    with server.connect() as conn:
        user=conn.execute('UPDATE users SET active=FALSE WHERE email=%s RETURNING id',(args.email.strip().lower(),)).fetchone()
        if user:
            conn.execute('DELETE FROM sessions WHERE user_id=%s',(user['id'],))
            conn.execute("INSERT INTO audit(action,target) VALUES('local-admin:disable',%s)",(str(user['id']),))
    print('Account disabled.' if user else 'Account not found.')
elif args.command == 'create-test-accounts':
    path=root/'TEST-ACCESS.md'
    existing=path.read_text(encoding='utf-8') if path.exists() else ''
    if '## Synthetic test accounts' in existing:
        print('Test account notes already exist; preserving them.')
        raise SystemExit(0)
    notes=['\n## Synthetic test accounts\n','These are local-admin-approved test identities. They did not receive verification emails.','Do not treat these as evidence that Resend delivery works. Share credentials only with intended testers.\n']
    with server.connect() as conn:
        for label,address in [('測試成員小安','tester-a@connect.invalid'),('測試成員小晴','tester-b@connect.invalid')]:
            pwd=secrets.token_urlsafe(20)
            uid=str(uuid.uuid4())
            row=conn.execute('INSERT INTO users(id,email,name,password_hash,verified,bio) VALUES(%s,%s,%s,%s,TRUE,%s) ON CONFLICT(email) DO NOTHING RETURNING id',(uid,address,label,generate_password_hash(pwd),'這是由測試召集人建立的內部功能測試帳號。')).fetchone()
            if row:
                conn.execute("INSERT INTO audit(action,target) VALUES('local-admin:create-synthetic-test-account',%s)",(uid,))
                notes.append(f'- {label}: `{address}` / `{pwd}`')
    path.write_text(existing+'\n'.join(notes)+'\n',encoding='utf-8')
    print('Synthetic test accounts created. Credentials are only in TEST-ACCESS.md.')
