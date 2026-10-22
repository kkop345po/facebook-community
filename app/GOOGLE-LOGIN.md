# Google 登入設定

本網站使用 Google Identity Services 的官方按鈕，Flask 使用 google-auth 驗證簽章、audience、issuer、到期時間、email_verified，並額外檢查十分鐘有效且只能使用一次的 nonce。Google 身分以 sub 綁定，不以可變動的 email 當識別碼。

## Google Auth Platform

- 專案：Connect Community (`onyx-goal-512407-r5`)
- 用戶端類型：網頁應用程式
- Authorized JavaScript origins：
  - https://insulin-hosted-madonna-mega.trycloudflare.com
  - http://localhost
  - http://localhost:5080
- 使用 GIS popup callback，不需要設定 redirect URI，也不需要將 client secret 放到前端。
- Client ID 寫入本機 `.env`：`GOOGLE_CLIENT_ID=...apps.googleusercontent.com`，然後執行 `Restart-Web.ps1`。
- 臨時網址更換後必須更新 Google 的 origin 清單。Google 控制台對共享臨時網域的接受情況仍須實測，不能保證 production 品牌驗證可用。

Google 登入成功可建立已驗證的 Gmail／Workspace 成員，無需另外透過 Resend 驗證同一個 Google 信箱。Resend 的寄信限制本身仍存在。

Google 非 Gmail／Workspace 的第三方信箱首次登入會拒絕自動建立或連結，避免錯誤信箱擁有權判斷。同 Email 的未驗證帳號，可由 Google 已確認擁有權的 Gmail／Workspace 身分認領：系統會廢棄原密碼、原驗證／重設連結和舊工作階段，使用 Google 名稱重建個人資料，避免預先註冊者保留存取權。此後可用 Google 登入；若要使用 Email 密碼登入，需重新設定密碼。已驗證且有效的同 Gmail／Workspace Email 帳號可連結到 Google sub。

測試：11 項整合測試通過。Google 部分使用模擬驗證器測試 nonce、重放、sub 穩定識別、第三方信箱及無效權杖；2026-10-22 使用者已回報另一個 Google 帳號成功登入；待驗證帳號認領仍以整合測試驗證。
