#!/usr/bin/env python3
"""NPC 回覆工作程式：每 30 秒輪詢未讀訊息，用 opencode run --agent npc 回覆。
完全隔離：不使用任何工具權限，只在本機叫用 opencode CLI。
"""
import os
import sys
import time
import uuid
import json
import subprocess
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import server

log = logging.getLogger('npc')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

# 找 opencode 執行檔：優先用 npm 全域安裝的完整路徑
def find_opencode():
    candidates = [
        Path(os.environ.get('APPDATA', '')) / 'npm' / 'node_modules' / '@opencode' / 'cli' / 'bin' / 'opencode.exe',
        Path.home() / '.local' / 'share' / 'opencode' / 'bin' / 'opencode',
        Path('/usr/local/bin/opencode'),
        Path('/opt/homebrew/bin/opencode'),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return 'opencode'

OPENAI_CMD_BASE = [find_opencode(), 'run', '--agent', 'npc', '--format', 'json']
# 專案設定檔目錄（從這裡執行才會自動讀到 opencode.jsonc）
NPC_CONFIG_DIR = ROOT.parent / 'npc'

MAX_REPLY_CHARS = 400
POLL_INTERVAL = 30
MAX_FAILURES = 2

def get_npc_id():
    cfg = server.settings()
    env_id = cfg.get('NPC_USER_ID')
    if env_id:
        try:
            return uuid.UUID(env_id)
        except ValueError:
            pass
    with server.connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE is_npc AND active AND verified LIMIT 1").fetchone()
    if row:
        return row['id']
    raise RuntimeError('找不到 NPC 帳號，請先執行 manage.py npc-create')

def fetch_pending(npc_id):
    with server.connect() as conn:
        rows = conn.execute(
            '''SELECT m.id, m.sender_id, u.name, m.body, m.created_at
               FROM messages m
               JOIN users u ON u.id = m.sender_id
               WHERE m.recipient_id = %s AND m.read_at IS NULL AND u.active
               ORDER BY m.id''',
            (npc_id,)
        ).fetchall()
    by_sender = {}
    for r in rows:
        by_sender[r['sender_id']] = r
    return list(by_sender.values())

def build_prompt(messages):
    lines = []
    for m in messages:
        who = m['name'] if not m['mine'] else '你'
        lines.append(f"{who}: {m['body']}")
    history = '\n'.join(lines)
    return f"對方剛說：\n{history}\n\n請用小連的語氣回一句（1-3 句，≤60 字，繁體中文口語）："

def run_opencode(prompt):
    try:
        res = subprocess.run(OPENAI_CMD_BASE + [prompt], capture_output=True, text=True, timeout=120, encoding='utf-8', cwd=str(NPC_CONFIG_DIR))
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    except FileNotFoundError:
        return None, 'notfound'
    if res.returncode != 0:
        return None, f'rc={res.returncode} stderr={res.stderr[:200]}'
    text_out = ''
    for line in res.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            if ev.get('type') == 'text' and ev.get('part', {}).get('text'):
                text_out = ev['part']['text']
        except json.JSONDecodeError:
            pass
    return text_out.strip() if text_out else None, None

def get_recent_thread(npc_id, other_id, limit=6, through_id=None):
    with server.connect() as conn:
        rows = conn.execute(
            '''SELECT m.body, m.created_at, m.sender_id
               FROM messages m
               WHERE ((m.sender_id=%s AND m.recipient_id=%s) OR (m.sender_id=%s AND m.recipient_id=%s))
               AND (%s::bigint IS NULL OR m.id<=%s::bigint)
               ORDER BY m.id DESC LIMIT %s''',
            (npc_id, other_id, other_id, npc_id, through_id, through_id, limit)
        ).fetchall()
    out = []
    for r in reversed(rows):
        out.append({'name': '小連' if r['sender_id'] == npc_id else '對方', 'mine': r['sender_id'] == npc_id,
                    'body': r['body'], 'at': r['created_at'].isoformat()})
    return out

def store_reply(npc_id, to_id, body, msg_id):
    with server.connect() as conn:
        rid = uuid.uuid5(uuid.NAMESPACE_URL, f'facebook:npc:{npc_id}:{msg_id}')
        conn.execute('''INSERT INTO messages(sender_id,recipient_id,body,request_id)
            VALUES(%s,%s,%s,%s) ON CONFLICT(sender_id,request_id) DO NOTHING''', (npc_id, to_id, body, rid))
        conn.execute('UPDATE messages SET read_at=now() WHERE sender_id=%s AND recipient_id=%s AND id<=%s AND read_at IS NULL', (to_id, npc_id, msg_id))
        conn.commit()

def main():
    leadership = server.connect()
    if not leadership.execute("SELECT pg_try_advisory_lock(hashtext('facebook:npc-worker')) AS acquired").fetchone()['acquired']:
        leadership.close()
        log.info('Another NPC worker is already running.')
        return
    leadership.commit()
    npc_id = get_npc_id()
    log.info('NPC worker started, npc_id=%s', npc_id)
    failures = {}

    while True:
        try:
            pending = fetch_pending(npc_id)
            for msg in pending:
                sender = msg['sender_id']
                key = str(msg['id'])
                if failures.get(key, 0) >= MAX_FAILURES:
                    fallback = '我現在有點忙，等一下再回你。'
                    try:
                        store_reply(npc_id, sender, fallback, msg['id'])
                        log.warning('Sent fallback for msg=%s', key)
                    except Exception as e:
                        log.error('Fallback store failed: %s', e)
                    failures.pop(key, None)
                    continue

                thread = get_recent_thread(npc_id, sender, through_id=msg['id'])
                prompt = build_prompt(thread)

                reply, err = run_opencode(prompt)
                if err or not reply:
                    failures[key] = failures.get(key, 0) + 1
                    log.warning('Reply failed msg=%s err=%s (fail #%d)', key, err, failures[key])
                    continue

                reply = reply[:MAX_REPLY_CHARS]
                try:
                    store_reply(npc_id, sender, reply, msg['id'])
                    log.info('Replied to %s (%s): %s', msg['name'], key, reply[:50])
                    failures.pop(key, None)
                except Exception as e:
                    log.error('Store reply failed: %s', e)
                    failures[key] = failures.get(key, 0) + 1

        except Exception as e:
            log.exception('Loop error: %s', e)

        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
