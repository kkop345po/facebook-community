# 小型社群網站 PRD：官方來源研究摘要

查證日：2026-10-22。用途是協助界定需求與驗證風險，不代表已完成部署、效能測試或使用者研究。僅採官方 Meta、Cloudflare、Resend 來源；搜尋曾出現第三方資料，未用於結論。以下「事實」與「建議」分列，建議不等於使用者已核准範圍。

## 1. Facebook 基本流程對照

| 主題 | 官方可確認事實 | 本案 PRD 建議與界線 |
| --- | --- | --- |
| 發文 | 使用者從動態消息發起文字或照片／影片貼文，送出前選擇受眾。[Meta 發文說明](https://www.facebook.com/help/170116376402147) | MVP 採文字與圖片，明確顯示可見範圍；由伺服器對列表、單篇、互動及附件一致授權。影片、標記與直播另議。 |
| 朋友與動態 | Meta 於 2025 年公告 Friends 分頁納入朋友內容與交友邀請；該公告的初始適用地區是美國、加拿大。[Meta 公告](https://about.fb.com/news/2025/03/bringing-magic-of-friends-back-to-facebook/) | 可採搜尋人員→邀請→接受→朋友動態的簡單流程。邀請狀態機及時間排序是本案設計建議；不宣稱與所有地區現行 Facebook UI 完全相同。 |
| 留言與通知 | 官方通知設定列有貼文留言與交友邀請通知。[Facebook 通知設定](https://www.facebook.com/help/111970308891187/) | MVP 站內通知涵蓋邀請與留言；應定義已讀、重複事件、刪除內容與點擊後無權限的處理。無需由此推導必做 SMS 或瀏覽器推播。 |
| 社群安全 | Meta 提供留言控制、檢舉及檢舉狀態工具。[Meta 安全工具](https://www.meta.com/safety/topics/safety-basics/tools/stay-safe/) | 小型試營運仍需檢舉入口、管理員隱藏／刪除與停權，以及處理紀錄；管理人力和回應時間須由專案確認。 |

研究限制：本次部分 Facebook Help Center 網址回傳登入／暫時封鎖頁，因此未將該頁視為已驗證的朋友接受或按讚細節。按讚切換、取消邀請、拒絕及解除朋友等應在本案需求中獨立定義，不能假稱逐項抄自目前 Facebook。此處比較互動概念，不建議複製品牌素材或官方文案。

## 2. Cloudflare：Flask／Python Workers 與 PostgreSQL

**已確認事實：**

- 官方已有 Flask Worker 範例，使用 `workers.wsgi.entrypoint(app)`，可配合 Workers Static Assets；因此「Flask 一律不能在 Workers 執行」已不符合目前文件。[Flask 官方指南](https://developers.cloudflare.com/workers/languages/python/packages/flask/)
- Python 套件須屬支援的 pure Python、PyEmscripten 或 Pyodide 套件；一般作業系統的原生套件不能僅因能在本機安裝就推定可用。[Python 套件相容性](https://developers.cloudflare.com/workers/languages/python/packages/)
- Python Workers 可透過 Hyperdrive TCP 連線資料庫，要求 compatibility date 至少 `2026-09-08`；官方列出 PostgreSQL 的 `asyncpg`（推薦）、`pg8000`、`psycopg` 驅動。[Hyperdrive Python 指南](https://developers.cloudflare.com/hyperdrive/examples/python-workers/)
- Workers 有 CPU、記憶體及連線等限制；目前文件列出每 isolate 128 MB，免費方案 HTTP CPU 額度為 10 ms。驗證雜湊及圖片處理不能先假定可符合。方案及限制仍應於實作前重查。[Workers 限制](https://developers.cloudflare.com/workers/platform/limits/)

**PRD 推論與建議：**Flask＋Python Workers＋外部 PostgreSQL 具官方支援路徑，但尚未證明本案完整依賴、同步 WSGI／非同步驅動橋接、驗證套件與 ORM 可直接部署。Hyperdrive 是連線層，不代表已取得 PostgreSQL 主機、備份及復原方案。不要在 PRD 承諾免費、固定費用或未測的容量。

**實作前技術驗證門檻：**

1. 固定 Python、pywrangler、依賴與 compatibility date，部署最小 Flask API 到實際 Worker URL；驗證靜態路由與 API 路由。
2. 使用選定驅動及實際 PostgreSQL 主機完成新增／查詢／交易回滾、併發唯一性、TLS、連線失敗與逾時；對貼文／朋友／權限資料確認讀後寫一致性與 Hyperdrive 快取設定。
3. 驗證登入 cookie、CSRF、登出／撤銷、密碼雜湊所需 CPU，以及依賴打包、冷啟動和記憶體。安全要求不可為符合方案額度而弱化。
4. 圖片另定物件儲存與存取授權；測試實際上傳大小、MIME／內容檢查、重試與清理孤兒檔。不得依賴 Worker 記憶體作永久資料庫。
5. 經上述實測才鎖定部署架構；若依賴不相容，提請架構決策選擇替代套件或 Python 主機，不應靜默更換已確認技術要求。

## 3. Resend：一般使用者驗證信的上線前提

**已確認事實：**`resend.dev` 為測試寄件網域，只可寄至 Resend 帳號所屬信箱；寄給其他使用者需驗證自有網域並改用該網域的 From 地址。[Resend 測試網域限制](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain) 自有網域或子網域可用於正式寄送，官方建議使用子網域區隔寄件聲譽。[Verified Domains](https://resend.com/docs/dashboard/domains/introduction) DNS 驗證狀態可能涉及 SPF、DKIM、MX；應依帳號顯示的記錄設定並確認發信 capability，不能只以「已新增網域」判定完成。[Domain Verification Events](https://www.resend.com/changelog/domain-verification-events)

**PRD 建議：**上線依賴應列明自有寄件網域、DNS 修改權限、Resend 帳號可寄件狀態及伺服器端 API secret。驗證信的 token 簽發／雜湊保存、有效期限、單次使用、重寄節流與帳號狀態由應用負責。寄件 API 接受成功不等同使用者收件匣送達；需定義未收到、垃圾郵件、退信、速率限制與重試的體驗。若帳號顯示需正式寄送審核，亦須完成該帳號要求；本次未驗證特定帳號狀態。

**需實測：**從實際部署環境寄至至少兩種外部信箱服務，點擊驗證連結後確認狀態、過期／重用拒絕、重寄後舊連結規則及失敗可重試；檢查日誌不得含完整 token／API key。驗證信上線前應通過實際收件測試，不得用寄給開發者自身的測試信替代。

## 4. 可直接帶入 PRD 的未決事項

- 明確定義公開、朋友、本人可見範圍，以及解除朋友／封鎖對歷史貼文、留言、通知、圖片的效果。
- 確認試營運人數、同時使用量、圖片大小、容量與保留期限，再量測延遲、失敗率及備份復原；本研究不提供容量保證。
- 確認誰持有網域、資料庫與寄信帳號，誰處理檢舉與資料刪除；列為公開試營運門檻。
- 本摘要為官方文件研究，尚無實際產品使用者訪談、需求優先序驗證或正式環境驗收證據。
