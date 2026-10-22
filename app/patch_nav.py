import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/main.jsx',encoding='utf-8').read()
old = """[['feed',Home,'動態消息'],['members',Users,'社群夥伴'],['profile',UserRound,'我的個人頁'],['guide',BookOpen,'關於這個空間']].map(([id,Icon,label])=>"""
new = """[['feed',Home,'動態消息'],['messages',MessageCircle,'私訊'],['members',Users,'社群夥伴'],['profile',UserRound,'我的個人頁'],['guide',BookOpen,'關於這個空間']].map(([id,Icon,label])=>"""
if old in s:
    s = s.replace(old, new)
    open('src/main.jsx','w',encoding='utf-8').write(s)
    print('Nav patched')
else:
    print('NOT FOUND')
    i=s.index('[[\'feed\'')
    print(repr(s[i:i+120]))