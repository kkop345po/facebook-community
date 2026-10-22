import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
# Find the exact block to replace
i = s.index('const [user,setUser]=useState(null)')
j = s.index('const [draftId,setDraftId]=useState(()=>crypto.randomUUID());') + len('const [draftId,setDraftId]=useState(()=>crypto.randomUUID());')
block = s[i:j]

new_block = """const [user,setUser]=useState(null),[ready,setReady]=useState(false),[mailReady,setMailReady]=useState(true),[mailMode,setMailMode]=useState('unconfigured'),[error,setError]=useState('');
  const [page,setPage]=useState('feed'),[selected,setSelected]=useState(null),[posts,setPosts]=useState([]),[next,setNext]=useState(null),[members,setMembers]=useState([]),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[search,setSearch]=useState(''),[query,setQuery]=useState(''),[modal,setModal]=useState(null),[body,setBody]=useState('');
  const [convs,setConvs]=useState([]),[convsUnread,setConvsUnread]=useState(0),[activeConv,setActiveConv]=useState(null),[msgs,setMsgs]=useState([]),[msgsNext,setMsgsNext]=useState(null),[msgBusy,setMsgBusy]=useState(false);
  const [draftId,setDraftId]=useState(()=>crypto.randomUUID());"""

if block == new_block:
    print('Already patched')
else:
    s = s[:i] + new_block + s[j:]
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Patched')