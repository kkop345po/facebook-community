# Facebook 網站品質改善 — 2026-10-22

## 已完成與公開站驗證

- 18 項 pytest 整合測試通過，前端 Vite 建置成功。
- npm audit 官方公告查詢：0 個已知漏洞。這不是完整安全保證。
- 登入防暴力破解改為記錄失敗次數；11 次連續成功登入不會誤鎖，10 次失敗後仍會限制，期限過後可恢復。
- 前端動態牆請求加入序號，較舊回應不會覆蓋較新搜尋／個人頁結果。
- 編輯視窗限制 Tab／Shift+Tab 在視窗內循環、鎖定背景捲動；Escape 關閉後回到原按鈕。瀏覽器實際驗證通過，未儲存或變更使用者個人資料。
- 非私訊頁的背景輪詢間隔由 4 秒調整為 30 秒；私訊仍為 4 秒，隱藏頁面仍略過請求。
- 雜湊 JS／CSS 設定 public, max-age=31536000, immutable；HTML 維持 no-cache，所有私密 API 維持 no-store。已檢查實際公開站及條件式 304 回應。
- 郵件 4xx 永久錯誤（408／429 除外）標記 failed，不會無限重試；暫時失敗使用指數退避與隨機延遲，最多 6 次。冪等鍵沿用相同工作 ID；已使用及過期驗證連結不寄送。
- 郵件測試全部使用模擬提供者，未透過測試寄送真實郵件。

## 效能數據與限制

匿名 HTTP 檢查的 JS gzip 傳輸約 82.6 KB，CSS 約 9.4 KB。原本兩者 Cache-Control 均為 no-cache；更新後均為一年 immutable。這是資源與快取檢查，未量測 LCP／INP／CLS，也未取得 Lighthouse 分數。單次網路回應時間不能證明速度改善；本次只主張避免重複下載未變更的版本資源。

參考：https://web.dev/articles/vitals ，https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control

## Skill 執行狀態

- web-perf、email-best-practices、ui-ux-pro-max：已實際用於本次修正及驗證。
- bmad-code-review、bmad-qa-generate-e2e-tests：各依指示執行一次 render_skill.py；uv 無法連線 PyPI 下載 jinja2（socket error 10013），依 Skill 要求停止。未宣稱完成 BMAD 審查或產生 BMAD E2E 自動化。
- 額外執行的是獨立人工程式碼檢查、既有 pytest 擴充、CUA 瀏覽器操作回歸；沒有改為直接讀取或繞過 BMAD workflow。
- turnstile-spin：使用者已確認正式／本機網域與 Email 註冊、密碼登入、驗證／重設信入口。現有授權缺少 Turnstile Edit Token；auth-probe 還顯示 Git Bash 缺少 python3。尚未建立元件，未改動驗證流程，未使用測試金鑰冒充正式防護。
- Cloud Run：僅適用性評估。當前 PostgreSQL 在本機、NPC 依賴本機 CLI，無法將服務直接搬至 Cloud Run 後繼續連 localhost。保留目前免費臨時 Tunnel，未啟用 Cloud Run、Cloud Build、帳單或付費試用。
- 其他平台／架構限定 Skill（例如 GKE、BigQuery、Workers Durable Objects）與現有 Flask／PostgreSQL 網站無直接關係，不為使用而增加服務。

## 尚未解決

- Resend 共享測試網域仍限制收件者；沒有宣稱已解除網域限制。
- Turnstile 仍等待正確授權與元件設定；正式驗證尚未啟用。
- BMAD 兩個啟動器仍受當次依賴下載阻礙；完整獨立審查／自動瀏覽器 E2E 尚未完成。
- 臨時網址與本機開機依賴仍存在。


## 最新 GitHub 快照補充
BMAD 啟動器下載問題已透過允許網路的執行環境排除；四個審查者已完成檢查，詳細分類見 CODE-REVIEW.md。新增及修正後 pytest 為 26 項通過。瀏覽器延遲對話切換兩次與跨帳號資料隔離已通過。依使用者要求先停止進一步開發，完整瀏覽器重播測試及 Turnstile 授權留待接續；舊段落中的啟動器阻礙已不再是目前狀態。
