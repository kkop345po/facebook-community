import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

old = """  let chatContent;
 if(activeConv){
  chatContent = (
   <div>
    <div className="chat-header"><Avatar name={activeConv.name} size="small"/><div><b>{activeConv.name}</b><small>{activeConv.is_npc?'站內 NPC':'社群成員'}</small></div></div>
    <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':'')}> <div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}<div ref={endRef}/>
    <form className="chat-input" onSubmit={handleSend}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="輸入訊息…" maxLength={1000} disabled={msgBusy||!activeConv}/><Button className="primary" busy={msgBusy} disabled={!input.trim()||!activeConv}><Send size={16}/></Button></form>
   </div>
  );
 } else {
  chatContent = <div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>;
 }
 return <div className="messages-page">"""

new = """  const chatContent = activeConv ? (
   <div>
    <div className="chat-header"><Avatar name={activeConv.name} size="small"/><div><b>{activeConv.name}</b><small>{activeConv.is_npc?'站內 NPC':'社群成員'}</small></div></div>
    <div className="chat-msgs">{msgs.length===0?<div className="chat-empty"><p>說聲嗨，開始對話</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')+(activeConv.is_npc&&!m.mine?' npc':'')}> <div className="msg-bubble">{m.body}</div><div className="msg-time">{new Date(m.at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}</div></div>)}<div ref={endRef}/>
    <form className="chat-input" onSubmit={handleSend}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="輸入訊息…" maxLength={1000} disabled={msgBusy||!activeConv}/><Button className="primary" busy={msgBusy} disabled={!input.trim()||!activeConv}><Send size={16}/></Button></form>
   </div>
  ) : (
   <div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>
  );
 return <div className="messages-page">"""

if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Replaced with ternary')
else:
    print('NOT FOUND')
    i=s.index('let chatContent')
    print(repr(s[i:i+500]))

open('src/main.jsx','w',encoding='utf-8').write(s)