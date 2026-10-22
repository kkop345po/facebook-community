import server
with server.connect() as conn:
    rows = conn.execute('SELECT id, sender_id, recipient_id, body, created_at FROM messages ORDER BY id').fetchall()
    for r in rows:
        sender = str(r['sender_id'])[:8]
        recip = str(r['recipient_id'])[:8]
        body = r['body'][:60]
        print(f'{r["id"]}: {sender} -> {recip} : {body} at {r["created_at"]}')