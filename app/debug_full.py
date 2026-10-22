import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
i = s.index('function Messages')
j = s.index('function App')
print(s[i:j])