import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

old = """function Messages({convs,unread,activeConv,msgs,msgsNext,msgBusy,user,onOpen,onLoadMore,onSend}){
 const [input,setInput]=useState('');
 const endRef=useRef(null);
 const scrollToEnd=()=>{endRef.current?.scrollIntoView({behavior:'smooth'})};
 useEffect(scrollToEnd,[msgs]);
 const handleSend=e=>{e.preventDefault();if(!input.trim()||!activeConv||msgBusy)return;onSend(activeConv,input);setInput('');};
 if(!user) return <div className="loading"><Brand/><LoaderCircle className="spin"/><p>準備中…</p></div>;
 return <div className="messages-page">
  <aside className="conv-list">
   <div className="conv-header"><h2>私訊 {unread>0&&<span className="unread-badge">{unread}</span>}</h2></div>
   {convs.length===0?<div className="conv-empty"><MessageCircle size={32}/><p>還沒有對話</p><small>在社群夥伴頁面點選某人開始聊天</small></div>:
    <div className="conv-items">{convs.map(c=><button key={c.id} className={'conv-item '+(activeConv&&activeConv.id===c.id?'active':'')+(c.unread>0?'unread':'')} onClick={()=>onOpen(c)}><Avatar name={c.name} size="small"/><div className="conv-meta"><div className="conv-name-row"><b>{c.name}</b>{c.is_npc&&<span className="npc-tag">NPC</span>}</div><div className="conv-preview">{c.last_mine?'你: ':''}{c.last||'無訊息'}</div></div><div className="conv-time">{c.last_at?new Date(c.last_at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):''}{c.unread>0&&<span className="unread-dot">{c.unread}</span>}</div></button>)}</div>}
  </aside>
  <section className="chat-area">
   {activeConv?<>
    <div className="chat-header"><Avatar name={activeConv.name} size="small"/><div><b>{activeConv.name}</b><small>{activeConv.is_npc?'站內 NPC':'社群成員'}</small></div></div>
    <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':''))}><div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}<div ref={endRef}/>
    <form className="chat-input" onSubmit={handleSend}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="輸入訊息…" maxLength={1000} disabled={msgBusy||!activeConv}/><Button className="primary" busy={msgBusy} disabled={!input.trim()||!activeConv}><Send size={16}/></Button></form>
   </>:<div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>}
  </section>
 </div>}"""

new = """function Messages({convs,unread,activeConv,msgs,msgsNext,msgBusy,user,onOpen,onLoadMore,onSend}){
 const [input,setInput]=useState('');
 const endRef=useRef(null);
 const scrollToEnd=()=>{endRef.current?.scrollIntoView({behavior:'smooth'})};
 useEffect(scrollToEnd,[msgs]);
 const handleSend=e=>{e.preventDefault();if(!input.trim()||!activeConv||msgBusy)return;onSend(activeConv,input);setInput('');};
 if(!user) return <div className="loading"><Brand/><LoaderCircle className="spin"/><p>準備中…</p></div>;
 return <div className="messages-page">
  <aside className="conv-list">
   <div className="conv-header"><h2>私訊 {unread>0&&<span className="unread-badge">{unread}</span>}</h2></div>
   {convs.length===0?<div className="conv-empty"><MessageCircle size={32}/><p>還沒有對話</p><small>在社群夥伴頁面點選某人開始聊天</small></div>:
    <div className="conv-items">{convs.map(c=><button key={c.id} className={'conv-item '+(activeConv&&activeConv.id===c.id?'active':'')+(c.unread>0?'unread':'')} onClick={()=>onOpen(c)}><Avatar name={c.name} size="small"/><div className="conv-meta"><div className="conv-name-row"><b>{c.name}</b>{c.is_npc&&<span className="npc-tag">NPC</span>}</div><div className="conv-preview">{c.last_mine?'你: ':''}{c.last||'無訊息'}</div></div><div className="conv-time">{c.last_at?new Date(c.last_at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):''}{c.unread>0&&<span className="unread-dot">{c.unread}</span>}</div></button>)}</div>}
  </aside>
  <section className="chat-area">
   {activeConv ? (
    <>
     <div className="chat-header"><Avatar name={activeConv.name} size="small"/><div><b>{activeConv.name}</b><small>{activeConv.is_npc?'站內 NPC':'社群成員'}</small></div></div>
     <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':'')}> <div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}<div ref={endRef}/>
     <form className="chat-input" onSubmit={handleSend}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="輸入訊息…" maxLength={1000} disabled={msgBusy||!activeConv}/><Button className="primary" busy={msgBusy} disabled={!input.trim()||!activeConv}><Send size={16}/></Button></form>
    </>
   ) : (
    <div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>
   )}
  </section>
 </div>}"""

if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Messages component fixed')
else:
    print('NOT FOUND')
    i=s.index('function Messages')
    print(repr(s[i:i+100]))