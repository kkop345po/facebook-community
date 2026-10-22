import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
i = s.index('async function api(')
j = s.index('const date=s=>')
api_block = s[i:j]

new_api = """async function api(path,method='GET',data){
 const control=new AbortController();const timer=setTimeout(()=>control.abort(),15000);
 try {
  const r=await fetch('/api/'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data?JSON.stringify(data):undefined,signal:control.signal});
  const result=await r.json();if(!r.ok){const e=new Error(result.error||'暫時無法完成操作');e.status=r.status;throw e;}if(result.csrf)csrf=result.csrf;return result;
 } catch(e){if(e.name==='AbortError')throw new Error('等待逾時，結果可能仍在處理，請重新整理確認後再試。');throw e;}
 finally{clearTimeout(timer);}
}

async function loadConvs(){
 const r=await api('conversations');
 setConvs(r.threads); setConvsUnread(r.unread);
}

async function openConv(other){
 setActiveConv(other); setMsgs([]); setMsgsNext(null);
 await loadMsgs(other);
}

async function loadMsgs(other, more=false){
 setMsgBusy(true);
 try{
  const before = more && msgsNext ? msgsNext : '';
  const r=await api('messages/' + other + (before ? '?before=' + before : ''));
  setMsgs(v => more ? [...r.messages, ...v] : r.messages);
  setMsgsNext(r.next);
 }finally{setMsgBusy(false);}
}

async function sendMsg(other, body){
 setMsgBusy(true);
 try{
  const rid = crypto.randomUUID();
  const r=await api('messages','POST',{to: other, body, request_id: rid});
  setMsgs(v => [...v, r.message]);
  setDraftId(crypto.randomUUID());
  // 更新對話列表的最後訊息
  setConvs(v => v.map(c => c.id===other.id ? {...c, last: body, last_at: r.message.at, last_mine: true, unread: 0} : c));
 }finally{setMsgBusy(false);}
}

const date=s=>new Date(s).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});"""

s = s[:i] + new_api + s[j:]
open('src/main.jsx','w',encoding='utf-8').write(s)
print('API functions added')