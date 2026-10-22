import sys
sys.stdout.reconfigure(encoding='utf-8')
s=open('src/style.css',encoding='utf-8').read()

# Find a good place to insert - before the @media queries
insert_at = s.index('@media(min-width:1500px)')

chat_css = """
/* Messages / Chat */
.messages-page{display:grid;grid-template-columns:280px 1fr;gap:0;height:calc(100vh - 180px);min-height:500px;background:white;border:1px solid #e6ebf2;border-radius:12px;overflow:hidden}
.conv-list{display:flex;flex-direction:column;border-right:1px solid #eef1f6;background:#fafbfd;overflow:hidden}
.conv-header{padding:16px 18px;border-bottom:1px solid #eef1f6}
.conv-header h2{margin:0;font-size:14px;font-weight:700;color:#24334b;display:flex;align-items:center;gap:8px}
.unread-badge{background:var(--blue);color:white;font-size:10px;padding:2px 6px;border-radius:10px;font-weight:700}
.conv-items{flex:1;overflow-y:auto;padding:8px}
.conv-item{display:flex;gap:10px;padding:10px 12px;border-radius:10px;text-align:left;background:none;border:0;color:inherit;width:100%;cursor:pointer;transition:background .12s}
.conv-item:hover{background:#eef3fa}
.conv-item.active{background:#e8f1ff}
.conv-item.unread .conv-name-row b{color:var(--blue)}
.conv-item .avatar{flex-shrink:0}
.conv-meta{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
.conv-name-row{display:flex;align-items:center;gap:6px}
.conv-name-row b{font-size:13px;font-weight:650;color:#24334b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.npc-tag{font-size:8px;background:#f0e6ff;color:#7b5ac8;padding:1px 5px;border-radius:4px;font-weight:600;letter-spacing:.5px}
.conv-preview{font-size:11px;color:#8b9ab7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.conv-time{font-size:9px;color:#a5b0bf;white-space:nowrap;display:flex;flex-direction:column;align-items:flex-end;gap:2px}
.unread-dot{background:var(--blue);color:white;font-size:8px;padding:1px 5px;border-radius:8px;font-weight:700}
.conv-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding:20px;color:#9aa5b8;text-align:center}
.conv-empty svg{color:#c4d9fa;margin-bottom:10px}
.conv-empty p{font-size:13px;font-weight:600;margin:0 0 4px}
.conv-empty small{font-size:10px}
.chat-area{display:flex;flex-direction:column;background:white;overflow:hidden}
.chat-header{padding:14px 18px;border-bottom:1px solid #eef1f6;display:flex;align-items:center;gap:10px;background:#fafbfd}
.chat-header .avatar{flex-shrink:0}
.chat-header div{display:flex;flex-direction:column;min-width:0}
.chat-header b{font-size:14px;color:#24334b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-header small{font-size:10px;color:#9aa5b8}
.chat-msgs{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:12px;background:#fcfdff}
.chat-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#9aa5b8;text-align:center}
.chat-empty svg{color:#c4d9fa;margin-bottom:10px}
.chat-empty p{font-size:13px;font-weight:500}
.msg{display:flex;gap:8px;max-width:85%;animation:fadeIn .15s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.msg.mine{align-self:flex-end;flex-direction:row-reverse}
.msg.theirs{align-self:flex-start}
.msg.npc .msg-bubble{background:#f0e6ff;border-color:#e4d5fa}
.msg-bubble{padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.65;white-space:pre-wrap;word-break:break-word;box-shadow:0 1px 3px #00000008}
.msg.mine .msg-bubble{background:var(--blue);color:white;border-bottom-right-radius:4px}
.msg.theirs .msg-bubble{background:#f0f3f7;color:#24334b;border-color:#e8edf3;border-bottom-left-radius:4px}
.msg-time{font-size:8px;color:#a5b0bf;margin-top:3px;display:flex;align-items:center;gap:4px}
.msg.mine .msg-time{justify-content:flex-end}
.msg.theirs .msg-time{justify-content:flex-start}
.chat-input{display:flex;gap:10px;padding:14px 18px;border-top:1px solid #eef1f6;background:#fafbfd}
.chat-input input{flex:1;border:1px solid #dfe5ed;border-radius:20px;padding:10px 16px;font-size:13px;background:white;color:#24334b;min-width:0}
.chat-input input::placeholder{color:#a4aebc}
.chat-input input:focus{outline:2px solid #a8ccff;border-color:#84b9fe}
.chat-input .primary{padding:8px 16px;min-height:38px;font-size:11px}
.chat-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#9aa5b8;text-align:center}
.chat-placeholder svg{color:#c4d9fa;margin-bottom:12px}
.chat-placeholder p{font-size:14px;font-weight:500}
@media(max-width:1000px){
 .messages-page{grid-template-columns:1fr;height:calc(100vh - 150px)}
 .conv-list{position:absolute;z-index:10;width:280px;max-width:85vw;height:100%;box-shadow:4px 0 20px #00000010}
 .conv-list.closed{display:none}
 .chat-area{width:100%}
}
@media(max-width:760px){
 .messages-page{height:calc(100vh - 120px)}
 .conv-list{width:100%;max-width:none}
 .chat-msgs{padding:14px}
 .chat-input{padding:12px 14px}
}

"""

s = s[:insert_at] + chat_css + s[insert_at:]
open('src/style.css','w',encoding='utf-8').write(s)
print('Chat CSS added')