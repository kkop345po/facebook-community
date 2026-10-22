import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

# Find the members page block end and guide page start
old = """page==='members'?<><div className="section-heading"><div><span className="eyebrow">PEOPLE MAKE THE PLACE</span><h1>一起在這裡的人</h1><p>熟悉一個名字，開始一段對話。</p></div><Users size={32}/></div><div className="member-grid">{members.map(m=><button className="member-card" key={m.id} onClick={()=>{setSelected(m);setPage('profile')}}><Avatar name={m.name} size="large"/><h2>{m.name}</h2><p>{m.bio||'日常裡，總有值得分享的小事。'}</p><span>看看他的日常 <ArrowUpRight size={14}/></span></button>)}</div></>:
     page==='guide'?"""

new = """page==='members'?<><div className="section-heading"><div><span className="eyebrow">PEOPLE MAKE THE PLACE</span><h1>一起在這裡的人</h1><p>熟悉一個名字，開始一段對話。</p></div><Users size={32}/></div><div className="member-grid">{members.map(m=><button className="member-card" key={m.id} onClick={()=>{setSelected(m);setPage('profile')}}><Avatar name={m.name} size="large"/><h2>{m.name}</h2><p>{m.bio||'日常裡，總有值得分享的小事。'}</p><span>看看他的日常 <ArrowUpRight size={14}/></span></button>)}</div></>:
     page==='messages'?<Messages convs={convs} unread={convsUnread} activeConv={activeConv} msgs={msgs} msgsNext={msgsNext} msgBusy={msgBusy} user={user} onOpen={openConv} onLoadMore={loadMsgs} onSend={sendMsg} />:
     page==='guide'?"""

if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Messages page added')
else:
    print('NOT FOUND')
    # Debug
    i=s.index('page===\'members\'')
    print(repr(s[i:i+300]))