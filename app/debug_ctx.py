import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
i = s.index('chatContent = <div className="chat-placeholder"')
print(repr(s[i-200:i+200]))