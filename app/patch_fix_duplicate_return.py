import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

old = """  );
 return <div className="messages-page">return <div className="messages-page">
  <aside className="conv-list">"""

new = """  );
 return <div className="messages-page">
  <aside className="conv-list">"""

if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Fixed duplicate return')
else:
    print('NOT FOUND')
    i=s.index('return <div className="messages-page">return')
    print(repr(s[i:i+100]))