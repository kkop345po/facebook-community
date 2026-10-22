import React, {useEffect, useState, useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {Home, Users, UserRound, Search, ArrowRight, ArrowUpRight, Link2, ShieldCheck, MessageCircle, ThumbsUp, LogOut, Pencil, Trash2, X, Send, Globe2, Mail, ChevronDown, RefreshCw, Heart, Sparkles, LockKeyhole, Check, Menu, BookOpen, LoaderCircle} from 'lucide-react';
import './style.css';
import './social.css';

let csrf='';
async function api(path,method='GET',data){
 const control=new AbortController();const timer=setTimeout(()=>control.abort(),15000);
 try {
  const r=await fetch('/api/'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data?JSON.stringify(data):undefined,signal:control.signal});
  if(!r.headers.get('content-type')?.includes('application/json'))throw new Error('網站連線暫時中斷，請稍後重新整理。');
  const result=await r.json();if(!r.ok){const e=new Error(result.error||'暫時無法完成操作');e.status=r.status;throw e;}if(result.csrf)csrf=result.csrf;return result;
 } catch(e){if(e.name==='AbortError')throw new Error('等待逾時，結果可能仍在處理，請重新整理確認後再試。');throw e;}
 finally{clearTimeout(timer);}
}

const date=s=>new Date(s).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});function Avatar({name='',size='',onClick}){const color=['blue','peach','mint','purple'][[...name].reduce((a,c)=>a+c.codePointAt(0),0)%4];return <span onClick={onClick} className={'avatar '+color+' '+size}>{[...name][0]||'C'}</span>}
function Brand(){return <a className="brand" href="/" aria-label="Facebook 首頁"><span className="brand-icon"><Link2 size={26}/></span><span>Facebook</span></a>}
function Button({busy,children,...props}){return <button {...props} disabled={busy||props.disabled}>{busy?<LoaderCircle className="spin" size={18}/>:children}</button>}

function App(){
 const [user,setUser]=useState(null),[ready,setReady]=useState(false),[mailReady,setMailReady]=useState(true),[mailMode,setMailMode]=useState('unconfigured'),[error,setError]=useState(''),[googleReady,setGoogleReady]=useState(false);
  const [page,setPage]=useState('feed'),[selected,setSelected]=useState(null),[posts,setPosts]=useState([]),[next,setNext]=useState(null),[members,setMembers]=useState([]),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[search,setSearch]=useState(''),[query,setQuery]=useState(''),[modal,setModal]=useState(null),[body,setBody]=useState('');
  const [convs,setConvs]=useState([]),[convsUnread,setConvsUnread]=useState(0),[activeConv,setActiveConv]=useState(null),[msgs,setMsgs]=useState([]),[msgsNext,setMsgsNext]=useState(null),[msgBusy,setMsgBusy]=useState(false);
  const [draftId,setDraftId]=useState(()=>crypto.randomUUID());
 const [searchOpen,setSearchOpen]=useState(false);
 const activeId=useRef(null), messageRequest=useRef(null), feedRequest=useRef(0), authEpoch=useRef(0), threadEpoch=useRef(0), msgsRef=useRef([]);
 function clearPrivateState(){authEpoch.current++;threadEpoch.current++;feedRequest.current++;activeId.current=null;messageRequest.current=null;msgsRef.current=[];setConvs([]);setConvsUnread(0);setMsgs([]);setMsgsNext(null);setActiveConv(null);setMembers([]);setPosts([]);setSelected(null);setNext(null);setBody('');setModal(null);setNotice('');setMsgBusy(false)}
 function enterUser(u){clearPrivateState();setUser(u)}
 async function loadConvs(){const epoch=authEpoch.current;try{let before=null,threads=[],r;do{r=await api('conversations'+(before?'?before='+before:''));if(epoch!==authEpoch.current)return;threads.push(...r.threads);before=r.next}while(before);setConvs(threads);setConvsUnread(r.unread)}catch(e){if(epoch===authEpoch.current)setError(e.message)}}
 async function loadMembers(){const epoch=authEpoch.current;try{let after=null,items=[],r;do{r=await api('members'+(after?'?after='+after:''));if(epoch!==authEpoch.current)return;items.push(...r.members);after=r.next}while(after);setMembers(items)}catch(e){if(epoch===authEpoch.current)setError(e.message)}}
 useEffect(()=>{msgsRef.current=msgs},[msgs]);
 async function loadMsgs(other,more=false,quiet=false){
  const epoch=authEpoch.current,thread=threadEpoch.current;
  if(!quiet)setMsgBusy(true);
  try{let r,items=[],after=quiet?(msgsRef.current.at(-1)?.id||0):null;
   do{r=await api('messages/'+other.id+(quiet?'?after='+after:more&&msgsNext?'?before='+msgsNext:''));if(epoch!==authEpoch.current||thread!==threadEpoch.current||activeId.current!==other.id)return;items.push(...r.messages);after=r.next_after}while(quiet&&after);
   setMsgs(v=>[...new Map([...v,...items].map(m=>[m.id,m])).values()].sort((a,b)=>a.id-b.id));
   if(!quiet)setMsgsNext(r.next);
  }catch(e){if(epoch===authEpoch.current&&thread===threadEpoch.current)setError(e.message)}finally{if(epoch===authEpoch.current&&thread===threadEpoch.current&&!quiet)setMsgBusy(false)}
 }
 async function openConv(other){threadEpoch.current++;if(!other){activeId.current=null;setActiveConv(null);setMsgBusy(false);return}activeId.current=other.id;msgsRef.current=[];setActiveConv(other);setMsgs([]);setMsgsNext(null);await loadMsgs(other);await loadConvs()}
 async function sendMsg(other,body){
  const epoch=authEpoch.current,thread=threadEpoch.current;setMsgBusy(true);
  if(!messageRequest.current||messageRequest.current.to!==other.id||messageRequest.current.body!==body)messageRequest.current={to:other.id,body,request_id:crypto.randomUUID()};
  try{const r=await api('messages','POST',messageRequest.current);if(epoch!==authEpoch.current)return false;messageRequest.current=null;
   if(thread===threadEpoch.current&&activeId.current===other.id)setMsgs(v=>v.some(m=>m.id===r.message.id)?v:[...v,r.message]);
   await loadConvs();return true;
  }catch(e){if(epoch===authEpoch.current)setError(e.message);return false}finally{if(epoch===authEpoch.current)setMsgBusy(false)}
 }
 useEffect(()=>{api('session').then(r=>{setUser(r.user);setMailReady(r.mail_ready);setMailMode(r.mail_mode);setGoogleReady(r.google_ready)}).catch(e=>setError(e.message)).finally(()=>setReady(true))},[]);
 async function load(more=false){const requestId=++feedRequest.current;setBusy(true);setError('');try{const params=new URLSearchParams();if(selected)params.set('author',selected.id);if(query)params.set('q',query);if(more&&next)params.set('before',next);const r=await api('posts?'+params);if(requestId!==feedRequest.current)return;setPosts(v=>more?[...v,...r.posts]:r.posts);setNext(r.next)}catch(e){if(requestId!==feedRequest.current)return;setError(e.message);if(e.status===401){clearPrivateState();setUser(null);api('session').catch(()=>{});}}finally{if(requestId===feedRequest.current)setBusy(false)}}
 useEffect(()=>{if(user){load();loadMembers();loadConvs()}},[user?.id,selected?.id,query]);
 useEffect(()=>{if(!user)return;let stopped=false;let timer;const delay=page==='messages'?4000:30000;async function tick(){if(!document.hidden){await loadConvs();if(page==='messages'&&activeConv&&!msgBusy)await loadMsgs(activeConv,false,true)}if(!stopped)timer=setTimeout(tick,delay)}timer=setTimeout(tick,delay);return()=>{stopped=true;clearTimeout(timer)}},[user?.id,page,activeConv?.id,msgBusy]);
 useEffect(()=>{if(notice){const t=setTimeout(()=>setNotice(''),6000);return()=>clearTimeout(t)}},[notice]);
 function navigate(p){setPage(p);setSelected(p==='profile'?user:null);activeId.current=null;threadEpoch.current++;setActiveConv(null);setQuery('');setSearch('');setError('')}
 async function logout(){window.google?.accounts?.id?.disableAutoSelect();try{await api('logout','POST',{});clearPrivateState();setUser(null);setPage('feed');await api('session')}catch(e){setError(e.message)}}
 async function publish(e){e.preventDefault();setBusy(true);try{await api('posts','POST',{body,request_id:draftId});setBody('');setDraftId(crypto.randomUUID());setNotice('已分享你的日常');await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 const updatePost=p=>setPosts(list=>list.map(x=>x.id===p.id?p:x));
 if(!ready)return <div className="loading"><Brand/><LoaderCircle className="spin"/><p>正在準備你的Facebook…</p></div>;
 if(!user)return <Auth onLogin={enterUser} mailReady={mailReady} mailMode={mailMode} googleReady={googleReady} initialError={error}/>;
 return <div className={'app-shell page-'+page}>
  <header className={'topbar '+(searchOpen?'search-open':'')}><Brand/><form className="search" onSubmit={e=>{e.preventDefault();setQuery(search);setPage('feed');setSelected(null);setSearchOpen(false)}}><Search size={19}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="搜尋Facebook" aria-label="搜尋貼文"/><button aria-label="執行搜尋"><ArrowRight size={18}/></button></form><nav className="top-tabs" aria-label="主要導覽">{[['feed',Home,'首頁'],['members',Users,'社群成員'],['messages',MessageCircle,'Messenger'],['profile',UserRound,'個人檔案']].map(([id,Icon,label])=><button key={id} className={page===id?'active':''} aria-label={label} aria-current={page===id?'page':undefined} onClick={()=>navigate(id)}><Icon size={25}/>{id==='messages'&&convsUnread>0&&<span className="header-badge">{convsUnread}</span>}</button>)}</nav><div className="header-user"><button className="icon-btn mobile-search-toggle" aria-label={searchOpen?'關閉搜尋':'開啟搜尋'} aria-expanded={searchOpen} onClick={()=>setSearchOpen(v=>!v)}><Search size={21}/></button><span className="test-pill"><span/>內部測試</span><button onClick={()=>navigate('profile')} className="avatar-button" aria-label="我的個人頁"><Avatar name={user.name}/></button><button className="icon-btn" onClick={logout} aria-label="登出"><LogOut size={20}/></button></div></header>
  <div className="layout">
   <aside className="sidebar"><div className="sidebar-top"><span className="eyebrow">你的捷徑</span><button className="self-card" onClick={()=>navigate('profile')}><Avatar name={user.name}/><span><b>{user.name}</b><small>查看個人檔案 <ArrowUpRight size={12}/></small></span></button><nav>{[['feed',Home,'動態消息'],['messages',MessageCircle,'私訊'],['members',Users,'社群成員'],['profile',UserRound,'個人檔案'],['guide',BookOpen,'關於']].map(([id,Icon,label])=><button key={id} className={page===id?'active':''} onClick={()=>navigate(id)}><Icon size={21}/><span>{label}</span>{id==='messages'&&convsUnread>0&&<span className="nav-unread">{convsUnread}</span>}{page===id&&<span className="nav-dot"/>}</button>)}</nav></div><div className="sidebar-bottom"><div className="small-brand"><Link2 size={17}/> 真實的分享，剛好的連結。</div><p>Facebook · 2026<br/>為我們的小社群而生</p><span className="version">INTERNAL BETA · 0.1</span></div></aside>
   <main className="main">
    {error&&<div className="alert error" role="alert">{error}<button onClick={()=>setError('')} aria-label="關閉錯誤"><X size={16}/></button></div>}
    {page==='members'?<><div className="section-heading"><div><span className="eyebrow">一起連結</span><h1>社群成員</h1><p>熟悉一個名字，開始一段對話。</p></div><Users size={32}/></div><div className="member-grid">{members.map(m=><button className="member-card" key={m.id} onClick={()=>{setSelected(m);setPage('profile')}}><Avatar name={m.name} size="large"/><h2>{m.name}</h2><p>{m.bio||'日常裡，總有值得分享的小事。'}</p><span>查看個人檔案 <ArrowUpRight size={14}/></span></button>)}</div></>:
     page==='messages'?<Messages convs={convs} unread={convsUnread} activeConv={activeConv} msgs={msgs} msgsNext={msgsNext} msgBusy={msgBusy} user={user} onOpen={openConv} onLoadMore={loadMsgs} onSend={sendMsg} />:
     page==='guide'?<Guide/>:<>
     {selected?<section className="profile-card"><div className="profile-cover"><span>每個人，都有自己的故事。</span><Link2 size={70}/></div><div className="profile-info"><Avatar name={selected.name} size="large"/><div><h1>{selected.name}</h1><p>{selected.bio||'還沒有寫下自我介紹。'}</p><small>加入於 {new Date(selected.joined_at).toLocaleDateString('zh-TW')}</small></div>{selected.id!==user.id&&<button className="primary" onClick={()=>{setPage('messages');openConv(selected)}}><MessageCircle size={16}/>傳送私訊</button>}{selected.id===user.id&&<button className="secondary" onClick={()=>setModal({type:'profile'})}><Pencil size={15}/>編輯個人資料</button>}</div></section>:
     <section className="feed-intro"><div><span className="feed-label">你的社群動態</span><h1>{query?`「${query}」的搜尋結果`:'動態消息'}</h1></div><span className="feed-scope"><Users size={15}/>{members.length} 位成員</span></section>}

     {(!selected||selected.id===user.id)&&!query&&<form className="composer card" onSubmit={publish}><div className="composer-label"><Pencil size={16}/>建立貼文</div><div className="composer-row"><Avatar name={user.name}/><label className="sr-only" htmlFor="post-body">分享你的日常</label><textarea id="post-body" placeholder={`${user.name}，在想些什麼？`} maxLength={3000} value={body} onChange={e=>{setBody(e.target.value);setDraftId(crypto.randomUUID())}} rows={body?3:2} required/></div><div className="composer-footer"><span><ShieldCheck size={15}/>僅限已驗證的社群成員 <small>{body.length}/3000</small></span><Button className="primary" busy={busy} disabled={!body.trim()}><Send size={15}/>發佈</Button></div></form>}
     <div className="feed-heading"><h2>{selected?'貼文':query?'搜尋結果':'最新貼文'} <span>{posts.length?`${posts.length}${next?'+':''}`:''}</span></h2><button onClick={()=>load()} className="text-btn"><RefreshCw size={14}/>重新整理</button></div>
     {!posts.length&&!busy?<div className="empty card"><div className="empty-icon"><MessageCircle size={32}/></div><h2>{query?'還沒有找到相符的分享':'從一句「嗨」開始'}</h2><p>{query?'試試其他關鍵字，或回到動態消息。':'這裡的故事，等你寫下第一頁。\n分享今天的小事，讓彼此靠近一點。'}</p><button className="secondary" onClick={()=>query?navigate('feed'):document.querySelector('#post-body')?.focus()}>{query?'回到動態消息':'寫下第一則分享'}<ArrowRight size={16}/></button></div>:posts.map(p=><Post key={p.id} post={p} user={user} update={updatePost} refresh={()=>load()} onPerson={id=>{const m=members.find(x=>x.id===id);if(m){setSelected(m);setPage('profile')}}} onEdit={()=>setModal({type:'post',post:p})} onError={setError} onNotice={setNotice}/>)}
     {busy&&<div className="inline-loading"><LoaderCircle size={20} className="spin"/>正在載入…</div>}{next&&<button className="load-more secondary" disabled={busy} onClick={()=>load(true)}>載入更多日常<ChevronDown size={16}/></button>}
     </>}
   </main>
   <aside className="rightbar"><section className="contacts-panel"><div className="panel-heading"><h3>聯絡人</h3><button aria-label="查看所有社群成員" onClick={()=>navigate('members')}><Users size={19}/></button></div><p className="contacts-note">選擇成員，開始一段對話</p>{members.filter(m=>m.id!==user.id).map(m=><button className="contact-person" key={m.id} onClick={()=>{setPage('messages');openConv(m)}}><Avatar name={m.name}/><span><b>{m.name}</b><small>{m.is_npc?'AI 聊天助手':'社群成員'}</small></span><MessageCircle size={16}/></button>)}{members.length<2&&<p className="muted">還沒有其他成員加入。</p>}</section><section className="side-summary"><span className="summary-icon"><Users size={21}/></span><div><b>Facebook社群</b><p>{members.length} 位成員 · 成員可見</p></div></section><div className="right-footer">Facebook © 2026<br/>分享生活，也尊重彼此的隱私。</div></aside>
  </div>
  {notice&&<div className="toast" role="status"><Check size={18}/>{notice}</div>}
  {modal&&<EditModal modal={modal} user={user} onClose={()=>setModal(null)} onSaved={async u=>{if(u){setUser(u);setSelected(u);setMembers(v=>v.map(m=>m.id===u.id?u:m))}setModal(null);setNotice('已儲存變更');await load()}}/>}
 </div>;
}

let googleScriptPromise;
function loadGoogleScript(){
 if(window.google?.accounts?.id)return Promise.resolve();
 if(!googleScriptPromise)googleScriptPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.onload=resolve;script.onerror=()=>{googleScriptPromise=null;script.remove();reject(new Error('無法載入 Google 登入，請確認網路後重試。'))};document.head.appendChild(script)});
 return googleScriptPromise;
}
function GoogleSignIn({ready,onLogin,onError}){
 const mount=useRef(null),[failed,setFailed]=useState(false),[attempt,setAttempt]=useState(0);
 useEffect(()=>{if(!ready)return;let cancelled=false;const renewal=setTimeout(()=>setAttempt(n=>n+1),9*60*1000);setFailed(false);
 (async()=>{try{const [,config]=await Promise.all([loadGoogleScript(),api('auth/google/challenge','POST',{})]);if(cancelled)return;
 window.google.accounts.id.initialize({client_id:config.client_id,nonce:config.nonce,auto_select:false,ux_mode:'popup',callback:async response=>{if(cancelled)return;try{const r=await api('auth/google','POST',{credential:response.credential});history.replaceState({},'','/');onLogin(r.user)}catch(e){onError(e.message);setAttempt(n=>n+1)}}});
 window.google.accounts.id.renderButton(mount.current,{theme:'outline',size:'large',text:'continue_with',locale:'zh_TW',width:Math.min(320,mount.current.clientWidth||280)});
 }catch(e){if(!cancelled){setFailed(true);onError(e.message)}}})();return()=>{cancelled=true;clearTimeout(renewal)};},[ready,attempt]);
 return <div className="google-signin"><div className="auth-divider"><span>或使用 Google 帳號</span></div>{ready?<><div ref={mount}/>{failed&&<button className="secondary full" onClick={()=>setAttempt(n=>n+1)}>重新載入 Google 登入</button>}</>:<button className="secondary full" disabled>Google 登入設定中</button>}</div>
}

function Auth({onLogin,mailReady,mailMode,googleReady,initialError}){
 const params=new URLSearchParams(location.search),action=params.get('action'),token=params.get('token');
 const [mode,setMode]=useState(action==='verify'?'verify':action==='reset'?'reset':'login'),[error,setError]=useState(initialError),[message,setMessage]=useState(''),[pending,setPending]=useState(false),[address,setAddress]=useState(''),[verified,setVerified]=useState(false),[verifyPassword,setVerifyPassword]=useState(''),[verifyConfirm,setVerifyConfirm]=useState('');
 const mailFailure=mailMode==='resend_test'?'目前使用 Resend 測試寄件信箱，僅能寄到 Resend 帳號本人的信箱。其他測試者請向召集人索取內部測試帳號。':'寄信服務暫時無法寄出，請聯絡測試召集人。';
 async function submit(e){e.preventDefault();setPending(true);setError('');setMessage('');const data=Object.fromEntries(new FormData(e.currentTarget));setAddress(data.email||address);
  try{if(mode==='login'){const r=await api('login','POST',data);history.replaceState({},'','/');onLogin(r.user)}
   else if(mode==='register'){if(data.password!==data.confirm)throw new Error('兩次密碼不相同。');const r=await api('register','POST',data);setMode('pending');setMessage(r.sent?'驗證信已交由寄信服務處理，請檢查收件匣與垃圾郵件。':'帳號申請已建立。'+mailFailure+' 未完成驗證前無法登入。')}
   else if(mode==='forgot'){const r=await api('email','POST',{email:data.email,purpose:'reset'});setMessage(r.sent?r.message:mailFailure)}
   else if(mode==='reset'){if(data.password!==data.confirm)throw new Error('兩次密碼不相同。');const r=await api('reset','POST',{password:data.password,token});await api('session');history.replaceState({},'','/');setMode('login');setMessage(r.message)}
  }catch(e){setError(e.message)}finally{setPending(false)}}
 async function verify(){setPending(true);setError('');try{if(verifyPassword!==verifyConfirm)throw new Error('兩次密碼不相同。');const r=await api('verify','POST',{token,password:verifyPassword});setVerifyPassword('');setVerifyConfirm('');setVerified(true);setMessage(r.message);history.replaceState({},'','/')}catch(e){setError(e.message)}finally{setPending(false)}}
 async function resend(){setPending(true);setError('');try{const r=await api('email','POST',{email:address,purpose:'verify'});setMessage(r.sent?r.message:mailFailure)}catch(e){setError(e.message)}finally{setPending(false)}}
 function switchMode(value){setMode(value);setError('');setMessage('')}
 return <div className="auth-page"><header className="auth-header"><Brand/><span className="test-pill"><span/>開放註冊測試中</span></header><main className="auth-layout"><section className="auth-story"><div className="hero-kicker"><span/>REAL PEOPLE. LITTLE MOMENTS.</div><h1>讓日常，<br/>連在<span className="underlined">一起<svg viewBox="0 0 200 15"><path d="M3 10 Q90 -2 193 8"/></svg></span>。</h1><p className="hero-description">有些小事，值得有人聽。<br/>在熟悉的圈子裡，分享生活、交換心情，<br/>讓每一個平凡的今天，都多一點連結。</p><div className="hero-illustration" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><span className="hero-tag tag-hi">嗨，最近好嗎？<Heart size={15}/></span><div className="portrait portrait-a"><div className="hair"/><div className="face"/><div className="shirt"/></div><div className="portrait portrait-b"><div className="hair"/><div className="face"/><div className="shirt"/></div><div className="portrait portrait-c"><div className="hair"/><div className="face"/><div className="shirt"/></div><div className="hello-circle"><Link2 size={33}/></div><span className="hero-tag tag-story"><MessageCircle size={17}/>一點日常，一點共鳴。</span><Sparkles className="hero-spark" size={29}/><span className="hero-dot"/></div><div className="hero-bottom"><ShieldCheck size={19}/><span>只與社群成員分享，安心做自己。</span></div></section>
 <section className="auth-card"><div className="card-kicker">YOUR SPACE TO CONNECT</div><h2>{{login:'很高興，又見到你。',register:'新的連結，從這裡開始。',forgot:'找回通往日常的鑰匙。',pending:'只差一步，就連上了。',verify:verified?'歡迎加入Facebook。':'確認這是你的信箱。',reset:'設定一組新的密碼。'}[mode]}</h2><p className="auth-sub">{{login:'登入你的帳號，看看大家的新鮮事。',register:'建立帳號，與熟悉的人分享你的日常。',forgot:'輸入註冊信箱，我們會寄送重設連結。',pending:'驗證信箱後，就能加入社群對話。',verify:'確認信箱後，設定一組只有你知道的登入密碼。',reset:'使用至少 12 字的密碼，讓帳號更安心。'}[mode]}</p>
 {error&&<div className="alert error" role="alert">{error}</div>}{message&&<div className="alert success" role="status">{message}</div>}
 {mode==='verify'?<><div className="mail-symbol"><Mail size={42}/></div>{!verified?<><label className="field">設定登入密碼<input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={verifyPassword} onChange={e=>setVerifyPassword(e.target.value)}/></label><label className="field">確認登入密碼<input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={verifyConfirm} onChange={e=>setVerifyConfirm(e.target.value)}/></label><Button className="primary full" busy={pending} disabled={verifyPassword.length<12||verifyConfirm.length<12} onClick={verify}>確認驗證信箱<ArrowRight size={17}/></Button></>:<button className="primary full" onClick={()=>switchMode('login')}>前往登入<ArrowRight size={17}/></button>}<button className="text-btn center" onClick={()=>switchMode('pending')}>重新申請驗證信</button></>:
 mode==='pending'?<><div className="mail-symbol"><Mail size={42}/></div><label className="field">驗證信箱<input type="email" autoComplete="email" value={address} onChange={e=>setAddress(e.target.value)} placeholder="you@example.com"/></label><Button className="primary full" busy={pending} onClick={resend}>重新寄送驗證信</Button><p className="field-help">重寄後舊連結失效。兩次申請請間隔 60 秒。</p><button className="text-btn center" onClick={()=>switchMode('login')}>返回登入</button></>:
 <form onSubmit={submit}>
  {mode==='register'&&<label className="field">你的名字<input name="name" maxLength={40} autoComplete="nickname" placeholder="希望大家怎麼稱呼你？" required/></label>}
  {mode!=='reset'&&<label className="field">Email 信箱<input name="email" type="email" autoComplete="email" placeholder="you@example.com" required/></label>}
  {mode!=='forgot'&&<label className="field">密碼<input name="password" type="password" autoComplete={mode==='login'?'current-password':'new-password'} minLength={12} maxLength={128} placeholder={mode==='login'?'輸入你的密碼':'至少 12 字，支援貼上密碼'} required/></label>}
  {(mode==='register'||mode==='reset')&&<label className="field">再次確認密碼<input name="confirm" type="password" autoComplete="new-password" minLength={12} maxLength={128} placeholder="再輸入一次密碼" required/></label>}
  {mode==='login'&&<div className="forgot-row"><span><LockKeyhole size={13}/>安全登入</span><button type="button" className="text-btn" onClick={()=>switchMode('forgot')}>忘記密碼？</button></div>}
  <Button className="primary full" busy={pending}>{{login:'登入，回到你的日常',register:'建立帳號',forgot:'寄送重設密碼信',reset:'更新密碼'}[mode]}<ArrowRight size={17}/></Button>
 </form>}
 {['login','register'].includes(mode)&&<GoogleSignIn ready={googleReady} onLogin={onLogin} onError={setError}/>}
 {mode==='login'?<><div className="auth-divider"><span>第一次來到這裡？</span></div><button className="secondary full" onClick={()=>switchMode('register')}>加入Facebook，建立帳號</button><button className="text-btn center verify-link" onClick={()=>switchMode('pending')}>已有帳號，但還沒收到驗證信？</button></>:!['verify','pending'].includes(mode)&&<button className="text-btn center" onClick={()=>switchMode('login')}>已經有帳號？返回登入</button>}
 {!mailReady&&<p className="mail-status"><span/>Email 驗證服務設定中。內部測試帳號請向召集人索取。</p>}
 {mailMode==='resend_test'&&<p className="mail-status"><span/>目前使用臨時測試寄件信箱，僅可寄至 Resend 帳號本人的信箱。其他測試者請使用召集人提供的內部測試帳號。</p>}
 <div className="auth-footnote"><ShieldCheck size={14}/><span>這是測試空間，請勿分享敏感資料。</span></div></section></main><footer className="auth-footer"><span>© 2026 Facebook</span><span>小小的圈子，真實的連結。</span><span>繁體中文 · INTERNAL BETA</span></footer></div>;
}

function Post({post:p,user,update,refresh,onPerson,onEdit,onError,onNotice}){
 const [open,setOpen]=useState(false),[comments,setComments]=useState([]),[next,setNext]=useState(null),[content,setContent]=useState(''),[busy,setBusy]=useState(false),[deleting,setDeleting]=useState(false);const [requestId,setRequestId]=useState(()=>crypto.randomUUID());
 async function getComments(more=false){try{const r=await api(`posts/${p.id}/comments${more&&next?'?after='+next:''}`);setComments(v=>more?[...v,...r.comments]:r.comments);setNext(r.next)}catch(e){onError(e.message)}}
 async function like(){if(busy)return;setBusy(true);try{const r=await api(`posts/${p.id}/like`,'PUT',{liked:!p.liked});update(r.post)}catch(e){onError(e.message)}finally{setBusy(false)}}
 async function comment(e){e.preventDefault();setBusy(true);try{await api(`posts/${p.id}/comments`,'POST',{body:content,request_id:requestId});setContent('');setRequestId(crypto.randomUUID());await getComments();update({...p,comment_count:p.comment_count+1})}catch(e){onError(e.message)}finally{setBusy(false)}}
 async function remove(){setBusy(true);try{await api(`posts/${p.id}`,'DELETE',{});onNotice('已刪除貼文');refresh()}catch(e){onError(e.message)}finally{setBusy(false)}}
 async function removeComment(id){try{await api(`comments/${id}`,'DELETE',{});setComments(v=>v.filter(c=>c.id!==id));update({...p,comment_count:Math.max(0,p.comment_count-1)})}catch(e){onError(e.message)}}
 return <article className="post card"><div className="post-header"><button className="post-author" onClick={()=>onPerson(p.user_id)}><Avatar name={p.name}/><span><b>{p.name}</b><small>{date(p.created_at)}<span>·</span><Users size={12}/>{p.edited&&' · 已編輯'}</small></span></button>{p.user_id===user.id&&<div className="post-tools"><button onClick={onEdit} aria-label="編輯貼文"><Pencil size={16}/></button><button onClick={()=>setDeleting(!deleting)} aria-label="刪除貼文"><Trash2 size={16}/></button></div>}</div><div className="post-body">{p.body}</div>{deleting&&<div className="delete-confirm">確定刪除這則貼文與所有回應？<div><button className="text-btn" onClick={()=>setDeleting(false)}>取消</button><Button className="danger" busy={busy} onClick={remove}>確定刪除</Button></div></div>}<div className="post-stats"><span>{p.likes>0?<><span className="like-mini"><ThumbsUp size={10} fill="currentColor"/></span>{p.likes} 個喜歡</>:<span className="no-likes">每一個回應，都是連結。</span>}</span><button onClick={()=>{setOpen(!open);if(!open)getComments()}}>{p.comment_count} 則留言</button></div><div className="post-actions"><button className={p.liked?'liked':''} disabled={busy} onClick={like}><ThumbsUp size={18} fill={p.liked?'currentColor':'none'}/>{p.liked?'已喜歡':'喜歡'}</button><button onClick={()=>{setOpen(!open);if(!open)getComments()}}><MessageCircle size={18}/>留言</button></div>{open&&<div className="comments">{comments.map(c=><div className="comment" key={c.id}><Avatar name={c.name} size="small"/><div><div className="comment-bubble"><b>{c.name}</b><p>{c.body}</p></div><span className="comment-date">{date(c.created_at)}{c.user_id===user.id&&<button onClick={()=>removeComment(c.id)}>刪除</button>}</span></div></div>)}{next&&<button className="text-btn" onClick={()=>getComments(true)}>載入更多留言</button>}<form className="comment-form" onSubmit={comment}><Avatar name={user.name} size="small"/><input aria-label="寫下留言" placeholder="留下一點回應…" maxLength={1000} value={content} onChange={e=>{setContent(e.target.value);setRequestId(crypto.randomUUID())}} required/><Button busy={busy} aria-label="送出留言" disabled={!content.trim()}><Send size={18}/></Button></form></div>}</article>
}

function EditModal({modal,user,onClose,onSaved}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');const profile=modal.type==='profile',modalRef=useRef(null);
 useEffect(()=>{
  const previous=document.activeElement,previousOverflow=document.body.style.overflow;
  document.body.style.overflow='hidden';
  const listener=e=>{if(e.key==='Escape'){e.preventDefault();onClose();return}if(e.key==='Tab'){const controls=[...modalRef.current.querySelectorAll('button:not(:disabled),input:not(:disabled),textarea:not(:disabled),a[href]')].filter(node=>node.getClientRects().length);const first=controls[0],last=controls.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}};
  document.addEventListener('keydown',listener);modalRef.current.querySelector('input,textarea')?.focus();
  return()=>{document.removeEventListener('keydown',listener);document.body.style.overflow=previousOverflow;if(previous?.isConnected)previous.focus()};
 },[]);
 async function submit(e){e.preventDefault();setBusy(true);try{const data=Object.fromEntries(new FormData(e.currentTarget));const r=await api(profile?'profile':`posts/${modal.post.id}`,'PATCH',data);await onSaved(r.user)}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)onClose()}}><section ref={modalRef} className="modal card" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="panel-heading"><h2 id="modal-title">{profile?'編輯個人資料':'編輯日常'}</h2><button className="icon-btn" onClick={onClose} aria-label="關閉"><X size={22}/></button></div>{error&&<div className="alert error">{error}</div>}<form onSubmit={submit}>{profile?<><label className="field">你的名字<input name="name" maxLength={40} defaultValue={user.name} required/></label><label className="field">關於你<textarea name="bio" maxLength={300} defaultValue={user.bio} placeholder="分享一點關於自己的事…" rows={4}/></label></>:<label className="field">貼文內容<textarea name="body" maxLength={3000} defaultValue={modal.post.body} required rows={7}/></label>}<Button busy={busy} className="primary full">儲存變更<Check size={17}/></Button></form></section></div>
}
function Guide(){return <section className="guide card"><span className="eyebrow">A SPACE FOR US</span><h1>我們想留一個地方，<br/>給真實的日常。</h1><p>Facebook是一個開放註冊的測試社群。你可以在這裡分享近況、回應夥伴，慢慢累積屬於我們的對話。</p><div className="guide-item"><ShieldCheck/><div><h2>先驗證，再分享</h2><p>只有已驗證且有效的成員，才能讀取動態與互動。測試帳號由召集人在本機建立。</p></div></div><div className="guide-item"><Users/><div><h2>小圈子，也彼此尊重</h2><p>目前所有分享對已驗證成員可見。請勿放入敏感資料，若需要協助，直接聯絡測試召集人。</p></div></div><div className="guide-item"><Heart/><div><h2>自己的內容，自己做主</h2><p>你可以修改或刪除自己的貼文，刪除自己的留言，也能隨時取消按讚。內部測試結束後會清理測試資料。</p></div></div><p className="guide-version">內部測試版 0.1 · React / Flask / PostgreSQL</p></section>}

function Messages({convs,unread,activeConv,msgs,msgsNext,msgBusy,user,onOpen,onLoadMore,onSend}){
 const [input,setInput]=useState('');
 const endRef=useRef(null), lastSeen=useRef(null);
 useEffect(()=>{setInput('');lastSeen.current=null},[activeConv?.id]);
 useEffect(()=>{const last=msgs.at(-1)?.id;if(last&&last!==lastSeen.current){endRef.current?.scrollIntoView({behavior:'smooth',block:'nearest'});lastSeen.current=last}},[msgs]);
 async function handleSend(e){e.preventDefault();if(!input.trim()||!activeConv||msgBusy)return;const sent=input;if(await onSend(activeConv,sent))setInput(v=>v===sent?'':v)}
 return <div className={'messages-page '+(activeConv?'has-active':'')}>
  <aside className="conv-list"><div className="conv-header"><h2>私訊 {unread>0&&<span className="unread-badge">{unread}</span>}</h2></div>
   {convs.length===0?<div className="conv-empty"><MessageCircle size={32}/><p>還沒有對話</p><small>到成員個人頁按「傳送私訊」開始聊天。</small></div>:<div className="conv-items">{convs.map(c=><button key={c.id} className={'conv-item '+(activeConv?.id===c.id?'active':'')+(c.unread>0?' unread':'')} onClick={()=>onOpen(c)}><Avatar name={c.name} size="small"/><div className="conv-meta"><div className="conv-name-row"><b>{c.name}</b>{c.is_npc&&<span className="npc-tag">NPC</span>}</div><div className="conv-preview">{c.last_mine?'你：':''}{c.last||'開始對話'}</div></div>{c.unread>0&&<span className="unread-dot">{c.unread}</span>}</button>)}</div>}
  </aside>
  <section className="chat-area">{activeConv?<>
   <div className="chat-header"><button className="chat-back text-btn" onClick={()=>onOpen(null)} aria-label="返回對話列表">返回</button><Avatar name={activeConv.name} size="small"/><div><b>{activeConv.name}</b><small>{activeConv.is_npc?'AI 助手 · 對話由 OpenCode 產生回覆':'社群成員'}</small></div></div>
   <div className="chat-msgs" role="log" aria-label="對話訊息" aria-live="polite">{msgsNext&&<button className="text-btn" disabled={msgBusy} onClick={()=>onLoadMore(activeConv,true)}>載入較早訊息</button>}{msgs.length===0?<div className="chat-empty"><p>{msgBusy?'正在載入…':'說聲嗨，開始對話'}</p></div>:msgs.map(m=><div key={m.id} className={'msg '+(m.mine?'mine':'theirs')}><div className="msg-bubble">{m.body}</div><div className="msg-time">{date(m.at)}</div></div>)}<div ref={endRef}/></div>
   <form className="chat-input" onSubmit={handleSend}><input aria-label="輸入私訊" value={input} onChange={e=>setInput(e.target.value)} placeholder="輸入訊息…" maxLength={1000}/><Button className="primary" aria-label="傳送私訊" busy={msgBusy} disabled={!input.trim()}><Send size={16}/></Button></form>
  </>:<div className="chat-placeholder"><MessageCircle size={48}/><p>選擇對話開始聊天</p></div>}</section>
 </div>
}

createRoot(document.getElementById('root')).render(<App/>);
