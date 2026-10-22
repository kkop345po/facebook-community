# 技術條件與實作前提

本文件補充 PRD 的技術輸入，與需求行為分開保存；方案仍須實測，不代表已部署。

## 使用者指定的技術

- React 前端、Flask 後端、PostgreSQL 資料庫。
- Cloudflare 提供可連線的網站網址。
- Resend 寄送驗證信；忘記密碼信為快速草稿補充的第一版功能。

## 候選部署方案與必做驗證

React 靜態資源可由 Cloudflare Workers Static Assets 提供，以同源 `/api` 入口存取後端。Cloudflare 官方提供 Flask Python Workers 使用方式；但這不能證明任意 Python 套件或 PostgreSQL 驅動都可正常運作。

本次官方文件研究確認：Python Workers 已有 Hyperdrive 路徑，compatibility date 至少為 `2026-09-08`，列出的 PostgreSQL 驅動含 asyncpg、pg8000 與 psycopg。這是可採用的候選路徑，不等於本專案整組依賴已驗證。

先以小型實驗驗證：Flask 請求、環境秘密、PostgreSQL TLS 連線、參數查詢、交易與唯一約束、並行請求、資料庫重新連線及 Resend HTTPS 呼叫。記錄版本、設定、成功與失敗證據，再選架構。重點包括同步 WSGI 與驅動的整合、ORM、密碼雜湊 CPU 預算，以及 Hyperdrive 快取對認證與互動資料一致性的影響；不預設 JavaScript 範例可直接套用 Python。

若不相容，可評估 Cloudflare Containers 執行傳統 Flask 與 PostgreSQL 驅動，資料庫由外部服務提供；Containers 需對應付費資格，啟用前確認預算。此路徑是備案，不是已獲批准的付費決策。Flask 的工作階段與限流不能只放容器記憶體，避免重啟或多實例讓限制失效。

PostgreSQL 是獨立資料庫，不是 Cloudflare 自動附送的資源；本地開發也使用 PostgreSQL，不用 SQLite 冒充整合驗證。檔案上傳不在第一版，暫不引入 R2。

## 網址與寄件網域

優先候選為 `workers.dev` 平台網址。隨機 `trycloudflare.com` Tunnel 僅能作短期展示，依賴來源服務持續執行，不宣稱是持續部署。最終採哪個網址須在部署驗證確認。

網站可使用平台網址，寄件端仍需可控制 DNS 的網域。Resend 預設 `resend.dev` 測試寄件網域只能寄到帳號自己的信箱；向兩位內部測試成員寄真實驗證信前，必須完成自有寄件網域驗證。禁止把平台網址當作可自行驗證的寄件網域。

## 安全與寄信行為的實作注意

密碼採適當密碼雜湊；驗證與重設權杖具安全隨機性，只存雜湊並分開用途。一次性消耗與狀態更新應在資料庫交易中原子執行。使用具撤銷能力的安全 Cookie 工作階段、跨站請求防護及參數化查詢；密碼、Resend 金鑰與資料庫憑證不能放 React bundle。

寄信與帳號狀態分開：寄送失敗不撤銷待驗證帳號、不自動驗證。重試必須沿用同一邏輯事件的去重識別，控制寄送併發與連結輪替，避免延遲到達的舊信讓新信失效。驗證網址來自設定好的允許公開來源，不能直接相信請求 Host。重試與到期時間需在端到端測試驗證。

## 來源與證據界線

- [Cloudflare Flask Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/flask/)
- [Python Workers 連接 Hyperdrive](https://developers.cloudflare.com/hyperdrive/examples/python-workers/)
- [Workers 執行限制](https://developers.cloudflare.com/workers/platform/limits/)
- [Cloudflare Containers](https://developers.cloudflare.com/containers/)
- [Hyperdrive 支援的資料庫](https://developers.cloudflare.com/hyperdrive/reference/supported-databases-and-features/)
- [Resend 測試寄件網域限制](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)

上述來源於前階段查證，實作選版時再確認相容性；本次 PRD 尚未執行部署、發信或資料庫整合測試。最新研究摘要另見 research-digest.md。
