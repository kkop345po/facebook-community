import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

# Fix: Add closing </div> for chat-msgs before the ref div
old = """    <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':'')}> <div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}<div ref={endRef}></div>"""

new = """    <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':'')}> <div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}</div><div ref={endRef}></div>"""

if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Fixed missing chat-msgs close')
else:
    print('NOT FOUND')
    # Try to find similar
    idx = s.index('chat-msgs')
    print(repr(s[idx:idx+300]))