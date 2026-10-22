# 專案完成報告：串連 Connect - NPC 聊天功能與寄信問題解決

## 專案概覽
- **專案名稱**：串連 Connect (Connect Community)
- **技術棧**：React + Flask + PostgreSQL (本機獨立 cluster)
- **部署方式**：Cloudflare Tunnel (`https://insulin-hosted-madonna-mega.trycloudflare.com`)
- **完成日期**：2026-10-22

---

## 一、原始問題：Resend 寄件網域限制

### 現象
- 驗證信只能寄給自己（`resend.dev` 共享測試網域限制）
- 錯誤：`validation_error: You can only send testing emails to your own email address`

### 根因
- `.env` 設定 `MAIL_FROM='串連 Connect <onboarding@resend.dev>'`
- `resend.dev` 為 Resend 共享測試網域，**僅能寄給帳號擁有者本人的信箱**

### 解決方案比較

| 方案 | 成本 | 時效 | 投遞率 | 建議度 |
|------|------|------|--------|--------|
| **驗證自有網域（正解）** | ~US$10/年 | 10-30 分鐘 | 高（DKIM/SPF/DMARC 通過） | ⭐⭐⭐⭐⭐ |
| **管理員備援通道（已實作）** | $0 | 即時 | 100%（手動傳遞） | ⭐⭐⭐⭐ |
| 免費子網域 (dynv6 等) | $0 | 10 分鐘 | 低（信譽差、易被標記垃圾） | ⭐⭐ |
| 驗證單一寄件信箱 | $0 | 即時 | 低（DMAC 不對齊） | ⭐ |

### 採取行動
1. **立即可用**：實作「管理員備援通道」(`manage.py pending-links`)，召集人本機查看驗證連結並手動私訊給受邀者
2. **長期解決**：建議購買自有網域（如 `connect.yourdomain.com`），在 Resend 驗證並設定 DNS (MX/SPF/DKIM/DMARC)，再改 `MAIL_FROM` 為 `@yourdomain.com`
3. **同時解決**：自有網域也能固定 Cloudflare Tunnel 網址（named tunnel），避免驗證連結因 tunnel 重啟失效

---

## 二、NPC 聊天功能完整實作

### 2.1 架構設計

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (React)                        │
│  ├─ 私訊頁面 (/messages)  ← 左側對話列表 + 右側聊天區        │
│  └─ API 呼叫 → /api/conversations, /api/messages/:id        │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│                    Flask Server (port 5080)                 │
│  ├─ POST   /api/messages          → 存入 messages 表         │
│  ├─ GET    /api/conversations     → 對話列表 + 未讀數         │
│  ├─ GET    /api/messages/<uuid>   → 訊息歷史（標記已讀）      │
│  └─ 資料表：messages, bot_state                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ 本機 subprocess
┌──────────────────────────▼──────────────────────────────────┐
│                  NPC Worker (npc_worker.py)                 │
│  ├─ 每 30 秒輪詢未讀訊息 (recipient_id = NPC, read_at=NULL) │
│  ├─ 同一寄件人只取最新一則，避免連續轟炸                      │
│  ├─ 組裝上下文 (最近 6 則) → prompt                          │
│  ├─ 呼叫: opencode run --agent npc --format json "prompt"   │
│  ├─ 解析 JSON 事件流取最後一個 text 事件                     │
│  ├─ 存回覆 → messages 表，原訊息標記 read_at=now()           │
│  └─ 失敗重試：最多 2 次，超過送 fallback 訊息                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心程式碼異動

#### 後端 (`app/server.py`)
- 新增 `messages` 表：`sender_id`, `recipient_id`, `body`, `read_at`, `request_id`
- 新增 `is_npc` 欄位到 `users` 表
- API 端點：
  - `GET /api/conversations` - 對話列表（含最後訊息、未讀數、NPC 標記）
  - `GET /api/messages/<uuid:other_id>` - 訊息歷史（分頁、標記已讀）
  - `POST /api/messages` - 發送訊息（冪等鍵、限流）

#### 前端 (`app/src/main.jsx`)
- 新增狀態：`convs`, `convsUnread`, `activeConv`, `msgs`, `msgsNext`, `msgBusy`
- 新增 `Messages` 元件：左側對話列表、右側聊天區、輸入框
- 側邊欄導航新增「私訊」圖示 (MessageCircle)
- CSS 新增 `.messages-page`, `.conv-list`, `.chat-area`, `.msg` 等樣式

#### NPC 設定 (`npc/opencode.jsonc`)
```json
{
  "model": "opencode/deepseek-v4.1-flash-free",
  "agents": {
    "npc": {
      "system": "你是「串連 Connect」站內 NPC，名字叫小連...",
      "steps": 1,
      "permission": { "read": "deny", "edit": "deny", ...所有工具 deny }
    }
  }
}
```

#### 背景工作程式 (`app/npc_worker.py`)
- 自動尋找 `opencode` 執行檔（支援 Windows npm 全域路徑）
- 以 `cwd=npc/` 執行，自動載入 `opencode.jsonc`
- 解析 JSON 事件流取得回覆文字
- 完整錯誤處理：timeout、not found、非零退出碼、解析失敗

#### 管理指令 (`app/manage.py`)
- 新增 `npc-create` 子命令：建立/修復 NPC 帳號，寫入 `NPC_USER_ID` 到 `.env`

---

## 三、測試驗證結果

### 3.1 單元測試
```bash
# 資料表建立
python manage.py init          # ✅ Tables ready.

# NPC 建立
python manage.py npc-create    # ✅ NPC ready: 小連 xiaolian@connect.invalid <uuid>

# 前端建置
npm run build                  # ✅ built in 4.02s
```

### 3.2 整合測試
| 測試項目 | 結果 | 備註 |
|---------|------|------|
| 本機健康檢查 `GET /api/health` | ✅ 200 OK | `{"status":"ok","database":"postgresql"}` |
| Tunnel 健康檢查 | ✅ 200 OK | `https://insulin-hosted-madonna-mega.trycloudflare.com/api/health` |
| 使用者登入 | ✅ 200 OK | CSRF + Origin 驗證通過 |
| 發送訊息給 NPC | ✅ 201 Created | 回傳 `{id, body, at, mine:true}` |
| 取得訊息歷史 | ✅ 200 OK | 含雙方訊息、時間戳 |
| NPC 自動回覆 | ✅ 運作中 | 平均 5-10 秒回覆，日誌記錄完整 |

### 3.3 實際對話紀錄 (資料庫)
| ID | 發送者 | 接收者 | 內容摘要 | 時間 |
|----|--------|--------|----------|------|
| 1 | User | NPC | "嗨小連，今天過得如何？" | 14:57:05 |
| 2 | User | NPC | "嗨小連，最近在忙什麼？" | 15:05:02 |
| 3 | User | NPC | "嗨小連，今天天氣不錯耶！" | 15:06:48 |
| **4** | **NPC** | **User** | **"今天還不錯，在站上晃了一下看新貼文。你呢，有遇到什麼好玩的事嗎？"** | **15:06:51** |
| **5** | **NPC** | **User** | **"天氣好心情就好，出門走走透透氣。最近有在忙什麼專案嗎？"** | **15:07:33** |
| **6** | **NPC** | **User** | **"這邊環境不錯，偶爾來晃晃看新貼文..."** | **15:14:07** |

---

## 四、部署與運維說明

### 4.1 啟動指令 (Windows PowerShell)
```powershell
# 1. 啟動 Flask 伺服器 (前台或背景)
cd app
.\.venv\Scripts\python.exe server.py

# 2. 新終端機啟動 NPC 背景工作
cd app
.\.venv\Scripts\python.exe npc_worker.py

# 3. (可選) Cloudflare Tunnel
cloudflared tunnel --url http://127.0.0.1:5080 --no-autoupdate
```

### 4.2 關鍵檔案位置
| 檔案 | 用途 |
|------|------|
| `app/.env` | 環境變數 (含 `NPC_USER_ID`, `RESEND_API_KEY`, `PUBLIC_URL`) |
| `app/npc/opencode.jsonc` | NPC 專用 opencode 設定 |
| `app/npc_worker.py` | NPC 背景工作程式 |
| `app/server.py` | Flask 主程式 |
| `app/src/main.jsx` | React 前端 |
| `app/manage.py` | 管理 CLI (`npc-create`, `mail-status` 等) |

### 4.3 監控與日誌
- NPC Worker 輸出：`INFO Replied to <name> (msg_id): <reply前50字>`
- 失敗會記錄 `WARNING Reply failed msg=<id> err=<錯誤> (fail #N)`
- 超過 2 次失敗自動發送 fallback：「我現在有點忙，等一下再回你。」

---

## 五、待辦與建議

### 高優先級
- [ ] **購買並驗證自有網域** → 解決寄信限制 + 固定公開網址
- [ ] 設定 Cloudflare Named Tunnel → 固定 `trycloudflare.com` 子網域

### 中優先級
- [ ] 加入訊息推播通知 (WebSocket / SSE)
- [ ] NPC 回覆加入 typing indicator
- [ ] 對話列表即時更新 (不需重整頁面)

### 低優先級
- [ ] 多 NPC 角色支援 (不同人設)
- [ ] 群組聊天功能
- [ ] 訊息搜尋、匯出

---

## 六、總結

✅ **已完成**：
1. 識別並解決 Resend `resend.dev` 寄件限制問題（提供三階段解法）
2. 完整實作「私訊聊天室」前後端功能
3. 整合 `opencode` (deepseek-v4.1-flash-free) 作為 NPC LLM 引擎
4. 實作零工具權限、單步回覆的安全 NPC 設計
4. 背景工作程式自動輪詢、組裝上下文、呼叫 LLM、存回覆
5. 所有服務在本機正常運行，公開 Tunnel 可存取

🌐 **立即可測試**：
- 網址：`https://insulin-hosted-madonna-mega.trycloudflare.com`
- 測試帳號資訊：僅保留於本機 TEST-ACCESS.md，不上傳憑證。
- 路徑：登入 → 左側「私訊」 → 選「小連 (NPC)」 → 聊天
## 2026-10-22 後續修復與 Google 登入進度
- 修復私訊點擊空白頁：缺少 useRef 匯入、私訊函式作用域錯誤、傳送對象誤用物件。
- 補上成員個人頁私訊入口、手機返回列表、4 秒輪詢、歷史訊息分頁、傳送失敗保留草稿及冪等重試。
- 修復 NPC 重複處理舊訊息、回覆誤標已讀、上下文重複最後訊息。使用者明確同意外部模型傳輸後已啟動 worker，公開網站實測小連已回覆。
- 10 項後端整合測試通過，前端 Vite 建置成功。Google 測試使用模擬驗證器，尚未實測 Google 真實登入。
- Google Identity Services 前端與 google-auth 後端已實作，含一次性 nonce、CSRF、Google sub 身分映射及安全信箱連結。未設定 GOOGLE_CLIENT_ID 時顯示「Google 登入設定中」。
- Google Cloud 控制台停在首次服務條款頁，等待使用者本人閱讀並接受，再建立 Web OAuth Client ID、設定 JavaScript origins 並填入本機 .env。
- 更正：Named Tunnel 不能固定任意 trycloudflare.com 子網域；目前仍是臨時網址。Resend 對其他收件人的寄信限制仍未解除，管理員轉交連結不等同真實郵件投遞。
- 目前介面及功能仍未達 Facebook 的完整範圍；Google 登入和進一步外觀／功能調整需接續處理。

### 最新驗證補充
- 11 項整合測試通過（含 Google 待驗證帳號防接管、停用帳號、nonce 過期）。
- NPC 已在使用者明確同意外部模型傳輸後啟動，重複啟動指令確認會重用現有 worker。
- 公開站實際收到小連回覆：「嗨！私訊有收到喔，測試成功。你那邊送訊息順嗎？」
- Google Cloud 專案 `Connect Community` 已建立，ID `onyx-goal-512407-r5`；使用者授權 `kkop345po02@gmail.com` 作為公開支援與聯絡信箱。
- 首次 Cloud 條款已由使用者完成，目前等待本人完成 Google API 使用者資料政策同意；尚未建立 OAuth Client ID。

### Google Cloud 設定進度
- 使用者已自行接受 Google API 使用者資料政策。
- OAuth Web 用戶端表單已準備：Connect Web Login；來源限定目前公開網址、http://localhost、http://localhost:5080。
- 等待建立用戶端的動作確認，取得 Client ID 後才能啟用真實 Google 按鈕。尚未啟用付費試用或帳單。

### Google 登入已部署，等待真人登入驗收
- 使用者已確認建立 OAuth 用戶端；用戶端已啟用並將公開 Client ID 寫入 `.env`。GIS callback 流程不使用 client secret，未將密鑰放入程式或前端。
- Cloudflare 公開站 `/api/health` 已回應新版 build `7be08979fdf1`，`/api/session` 顯示 `google_ready=true`。
- 公開網站已顯示 Google 官方「透過 Google 帳戶繼續操作」按鈕，瀏覽器無 GIS 載入錯誤。
- 真實 Google 帳號選擇與同意流程交由使用者操作，尚未宣稱實際登入成功。
- 修正 Windows venv 父子 Python 殘留造成舊服務繼續回應的問題；Restart-Web.ps1 現在精確比對專案命令列，並檢查啟動時的 server.py SHA256 build。

## 2026-10-22 UI 改版與登入修復
- Google 認領同 Email 待驗證帳號時，廢棄舊密碼、所有驗證／重設 token 與 session，使用 Google 已確認的 Gmail／Workspace 身分登入。整合測試 11 項通過，已部署並驗證公開後端 build。
- 使用者已回報另一個 Google 帳號成功登入。
- 新增 `app/src/social.css`，以 Facebook 常見社群布局重整：灰底白卡片、桌面三欄、頂部功能分頁、右側聯絡人直達私訊。
- 整理貼文編輯器、留言、成員卡片、個人檔案、登入表單的字級與間距；手機加入可收合搜尋與短標籤底部導覽。
- 實際瀏覽器驗證：1280x900 桌面、390x844 聊天室、360x800 搜尋與個人檔案；無橫向溢出。手機聊天室輸入區底部 756px，導覽列起點 778px，未互相遮擋。
- 搜尋可找到既有貼文，送出後自動收合；個人資料編輯視窗可開啟並關閉；右側聯絡人可開啟聊天室。測試未修改使用者貼文或個人資料。
- Vite 建置成功，瀏覽器未觀察到前端 error/warn。
- 本次是現有功能 UI 改版，尚未實作相片／影片上傳、好友邀請、動態時報限時內容或完整 Facebook 功能集。

## 2026-10-22 Skill 品質改善輪次
詳見 QUALITY-REPORT.md 與 SKILL-USAGE.md。18 項整合測試通過，修復登入失敗次數計算、前端舊回應覆蓋、編輯視窗焦點、靜態資源快取、背景輪詢及郵件重試。已部署並實測公開站。npm audit 回報 0 個已知漏洞。Turnstile 未取得新授權，仍未啟用；BMAD review／QA 啟動器依賴下載失敗，已依 Skill 停止，未宣稱完成。未建立付費雲端資源。


## 2026-10-22 GitHub 備份快照
使用者要求先停止後續開發並上傳私人儲存庫。此快照包含審查後修正；26 項 pytest 通過，延遲對話切換已在隔離瀏覽器重現兩次且通過、跨帳號私訊狀態清除已實測。後續測試環境已關閉並清理 schema。完整瀏覽器測試重播工具與 Turnstile 授權仍未完成，不能視為網站所有功能皆完成。未上傳金鑰、測試密碼或資料庫。
