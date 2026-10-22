import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

# Fix 1: Remove duplicate const date (the second one which was added by my API patch)
first = s.index('const date=s=>new Date(s).toLocaleString')
second = s.index('const date=s=>new Date(s).toLocaleString', first+1)
# Remove from second to the next semicolon+newline
end = s.index(';', second) + 1
# Also remove any following newline
if s[end:end+1] == '\n':
    end += 1
s = s[:second] + s[end:]
print('Removed duplicate const date')

# Fix 2: Find the missing brace in Messages component
# Look for the pattern around line 160
i = s.index('chatContent = <div className="chat-placeholder"')
# Check what's around it
ctx = s[i-200:i+200]
print('Context around chatContent:')
print(ctx)

open('src/main.jsx','w',encoding='utf-8').write(s)