import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

# Fix: Change self-closing div to explicit open/close
old = '<div ref={endRef}/>'
new = '<div ref={endRef}></div>'
if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Fixed self-closing div')
else:
    print('NOT FOUND')