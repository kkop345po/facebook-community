# Facebook Community

內部測試社群網站，使用 React、Flask 與 PostgreSQL，包含 Google 登入、Email 驗證、動態牆、留言、按讚、個人檔案、私訊及選用 NPC 聊天。

這是自行開發的測試專案，與 Meta／Facebook 官方無關。

## 專案內容

- `app/`：前端、後端、測試與 Windows 啟動腳本。
- `npc/`：NPC 模型設定，不含帳號金鑰。
- `.agents/skills/`：專案使用的 Skill 與其原始授權資料。
- `_bmad/`、`_bmad-output/`：BMAD 工具、需求及設計文件。
- `PROJECT_REPORT.md`、`QUALITY-REPORT.md`：進度與驗證紀錄；較舊段落可能已被後續紀錄取代。

## 本機執行

1. 安裝 Python 3.11 以上、Node.js 與 PostgreSQL。
2. 依 `app/README.md` 建立 Python 環境與資料庫，安裝 `app/requirements-lock.txt` 與 npm 依賴。
3. 複製 `app/.env.example` 為 `app/.env`，自行設定資料庫、工作階段密鑰、Google Client ID 與選用的 Resend 金鑰。實際金鑰不包含在儲存庫中。
4. 在 `app` 執行 `npm ci`、`npm run build`、`python manage.py init`，再執行 `python server.py`。
5. 需要公開測試時，另行啟動 Cloudflare Tunnel。舊文件中的臨時網址不是永久部署位址。

## 測試

在已設定測試用 PostgreSQL 的 `app` 資料夾執行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

測試會建立獨立 schema，不會寄送真實 Email。`app/tests/ui_harness.py` 為僅限本機的瀏覽器回歸測試環境，請勿用於公開部署。

## 尚有限制

- Resend 共享測試寄件網域無法向任意收件者寄信，Google 登入可獨立使用。
- Turnstile 尚未設定正式金鑰，防機器人驗證未啟用。
- NPC 使用外部模型服務，啟動前需取得使用者對訊息傳輸的同意。
- 完整 Facebook 功能集、永久雲端部署及全部瀏覽器自動化仍不是本專案已完成範圍。

本機 `.env`、測試帳密、PostgreSQL 資料、依賴套件與執行紀錄均排除上傳。
