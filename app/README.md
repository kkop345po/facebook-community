# Facebook

React + Flask + PostgreSQL 的邀請制內部社群。主程式在 `server.py`，介面在 `src/`。

## 開啟

Windows PowerShell，於本資料夾執行：

```powershell
.\.venv\Scripts\python.exe server.py
```

本機網址為 `http://127.0.0.1:5080`。此專案使用獨立 PostgreSQL cluster，資料在 `.pgdata/`、port 55438；不變更原本 port 5432 的 PostgreSQL 服務。

```powershell
# 若資料庫已停止，先啟動
& 'C:/Program Files/PostgreSQL/18/bin/pg_ctl.exe' -D "$PWD/.pgdata" -l "$PWD/.runtime/postgres.log" start
# 重新建置介面
npm.cmd run build
# 測試（在隨機隔離 schema 內執行，完成會清理該 schema）
.\.venv\Scripts\python.exe -m pytest -q
```

## 邀請與寄信

`.env` 為秘密設定，已被 gitignore 排除。將 Resend 金鑰填 `RESEND_API_KEY`、已驗證網域的寄件信箱填 `MAIL_FROM`；寄給一般成員需自有且已驗證的網域，`resend.dev` 只能寄給 Resend 帳號自己的信箱。

`TEST-ACCESS.md` 保存邀請碼與（若已建立）合成測試帳號，不能上傳或公開到網站。合成帳號由召集人本機核准，不能用來宣稱 Email 真實送達已驗證。新註冊帳號仍須完成信箱驗證，不會因缺少金鑰自動驗證。

```powershell
.\.venv\Scripts\python.exe manage.py --help
.\.venv\Scripts\python.exe manage.py mail-status
.\.venv\Scripts\python.exe manage.py allow-email tester@example.com
.\.venv\Scripts\python.exe manage.py disable tester@example.com
```

寄信工作加密保存在 PostgreSQL，背景工作每30秒檢查一次；失敗延後2分鐘重試，相同工作沿用 Resend 冪等鍵。API 接受不代表收件匣已送達，必須另做真實收信測試。重寄驗證連結後舊連結失效。

## 臨時公開網址

```powershell
cloudflared tunnel --url http://127.0.0.1:5080 --no-autoupdate
```

取得網址後先設定 PUBLIC_URL 與 Secure Cookie，再重啟 server：

```powershell
.\.venv\Scripts\python.exe manage.py set-url https://實際網址.trycloudflare.com
```

此為 Cloudflare Tunnel 展示方式：電腦、PostgreSQL、server 與 tunnel 都必須保持執行；關機或 tunnel 重啟可能使網址失效。這不等同獨立雲端常駐部署。只公開 Flask 網站服務，不公開 PostgreSQL 連接埠。

## 備份與清理

測試資料存在本機 `.pgdata/`，請勿直接刪除此目錄。每日及測試結束時由召集人使用 PostgreSQL pg_dump 備份至受限位置，實際備份／還原演練與保留清理尚需記錄，不能宣稱已自動完成。結束測試後30日內清除帳號與內容，備份最長7日滾動淘汰；恢復備份須重套刪除紀錄。

已實作的功能與尚待驗證的上線條件，以本次測試報告為準。正式常駐部署、真實 Resend 收件及保留期演練不能以本地自動化測試替代。
