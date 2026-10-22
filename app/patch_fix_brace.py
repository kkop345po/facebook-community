import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()

# Fix: Add missing closing brace before else
old = """   </div>
  );
 }else{
  chatContent = <div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>;
 }"""
new = """   </div>
  );
 } else {
  chatContent = <div className="chat-placeholder"><MessageCircle size={48}/><p>選擇左側對話開始聊天</p></div>;
 }"""
if old in s:
    s = s.replace(old, new)
    print('Fixed missing brace')
else:
    print('NOT FOUND - trying alternative')
    # Try with different whitespace
    old2 = """  );
 }else{"""
    if old2 in s:
        s = s.replace(old2, """  );
 } else {""")
        print('Fixed with alt')
    else:
        print('Still not found')
        i=s.index('chatContent = <div className="chat-placeholder"')
        print(repr(s[i-100:i+100]))

open('src/main.jsx','w',encoding='utf-8').write(s)