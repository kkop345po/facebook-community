import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
old = """useEffect(()=>{if(user){load();api('members').then(r=>setMembers(r.members)).catch(e=>setError(e.message))}},[user?.id,selected?.id,query]);"""
new = """useEffect(()=>{if(user){load();api('members').then(r=>setMembers(r.members)).catch(e=>setError(e.message));loadConvs()}},[user?.id,selected?.id,query]);
 useEffect(()=>{if(page==='messages'){loadConvs()}},[page]);"""
if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('useEffect patched')
else:
    print('NOT FOUND')
    i=s.index('useEffect(()=>{if(user){load()')
    print(repr(s[i:i+120]))