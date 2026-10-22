import subprocess, pathlib
ROOT=pathlib.Path(__file__).parent
W=ROOT/'_bmad-output/initiative-facebook-community/brainstorm-social-platform'
SCRIPT=ROOT/'_bmad/scripts/memlog.py'
def log(kind,text):
 subprocess.run(['uv','run','--no-cache',str(SCRIPT),'append','--workspace',str(W),'--type',kind,'--by','coach','--text',text],check=True,capture_output=True)
groups=[
('First Principles Thinking — 身分與信任','Email 與密碼註冊|信箱驗證後才能發文|登入與安全登出|忘記密碼寄重設連結|重寄驗證信與冷卻時間|過期驗證連結可恢復流程|同信箱不重複建立帳號|可撤銷的伺服器端登入工作階段|使用者名稱與顯示名稱分離|停權後撤銷所有登入'),
('Analogical Thinking — 社區公告欄','時間排序動態牆|純文字貼文|照片貼文|貼文編輯與刪除|留言串|單一按讚與取消|個人檔案頁|自介與頭像|公開貼文可分享連結|游標分頁載入舊貼文'),
('What If Scenarios — 第一百位朋友','雙向好友邀請|接受或拒絕邀請|撤回尚未接受邀請|取消好友|搜尋公開顯示名稱|好友限定貼文|封鎖後雙向限制存取|不感興趣隱藏貼文|收藏稍後閱讀|共同好友提示但尊重隱私'),
('Reverse Brainstorming — 如何讓信任崩潰再反轉','密碼只存安全雜湊|伺服器檢查每次修改權限|跨站請求偽造防護|顯示貼文時轉義文字|參數化資料庫查詢|驗證權杖只存雜湊|單次使用權杖交易鎖定|註冊與登入限流|避免錯誤訊息洩漏帳號存在性|安全 Cookie 與到期失效'),
('Metaphor Mapping — 大樓門廳與房間','登入頁作為清楚入口|驗證等待頁提供下一步|新用戶三步完成個人資料|動態牆作為交誼廳|個人頁作為自己的房間|通知中心作為信箱|空白動態牆提供發文引導|草稿避免離頁遺失|手機單欄導覽|鍵盤可操作的發文視窗'),
('Cross-Pollination — 郵務與物流','驗證信待寄事件存資料庫|寄信失敗可重試|寄信事件具冪等識別|信件內清楚標示有效期限|信件連結只採用設定的公開網址|使用者能看到待驗證狀態|寄信服務不影響登入頁顯示|記錄送信狀態不記錄完整權杖|測試模式清楚標示未真正寄信|已登入用戶可修正待驗證信箱'),
('Time Shifting — 從十人到萬人','先以十人封閉測試|資料庫遷移追蹤版本|貼文時間與作者建立索引|伺服器限制每頁筆數|圖片限制尺寸與檔案型別|上傳圖片至 R2|資料庫每日備份與還原演練|API 錯誤具追蹤識別|健康檢查區分服務與資料庫|以量測結果決定快取'),
('Forced Relationships — 校園與圖書館','新會員歡迎貼文|每週社群討論題|社團主題書架|活動報名與提醒|社區互助求助貼文|貼文標籤分類|按主題追蹤公開內容|社群守則置頂|檢舉後可查處理進度|版主可隱藏違規內容'),
('Concept Blending — 安靜社群','預設最新排序與可理解規則|關閉通知選項|每日摘要而非轟炸通知|不顯示公開人氣排行榜|使用者可刪除個人內容|帳號資料匯出|停用帳號冷靜期|圖片替代文字|尊重減少動畫偏好|適合繁體中文的時間與排版'),
('What If Scenarios — 部署斷線日','前端由 Cloudflare Workers Static Assets 提供|以 workers.dev 作開發階段公開網址|Flask Python Worker 先做套件相容性驗證|傳統 Flask 可改用 Cloudflare Containers|PostgreSQL 採獨立託管資料庫|開發可用本地 PostgreSQL|同源 /api 代理簡化 Cookie|臨時 Tunnel 僅供短期展示|發信網域與網站網域分開配置|將登入資料與服務金鑰留在後端'),
('Sensory Exploration — 使用完成感','按讚即時回饋且失敗回復|發文成功後新內容出現在頂部|表單錯誤出現在欄位旁|載入骨架避免版面跳動|通知未讀狀態清楚|重新整理仍保留真實貼文|雙帳號看見彼此互動|無權限頁面清楚說明|低速網路可重新嘗試|完成註冊到第一則留言的導覽')]
log('direction','使用者指定 React 前端、Flask 後端、PostgreSQL、Cloudflare 臨時網域與 Resend 驗證信；選擇 Ideate for me，專案主題 facebook-community。')
for technique,ideas in groups:
 log('technique','started '+technique)
 for idea in ideas.split('|'): log('idea',idea)
log('insight','關鍵是建立真實用戶的完整互動循環：註冊、驗證、登入、發文、另一帳號留言按讚、重新整理仍保留，而非只有 Facebook 外觀。')
log('decision','MoSCoW Must：註冊、驗證、重寄、登入登出、忘記密碼、個人資料、文字貼文增改刪、時間動態牆、留言、按讚、分頁、權限與限流；Should：頭像照片、好友與好友隱私、通知、檢舉；Could：社團、活動、收藏；本輪不做直播、廣告、Marketplace、複雜推薦、即時私訊。')
log('decision','規劃部署：React 由 Workers Static Assets 提供，Flask 優先驗證 Python Workers 相容性；傳統 Python 資料庫驅動若不相容採 Cloudflare Containers（需付費方案），PostgreSQL 使用外部託管，容器經 TLS 直連，不預設可使用 Hyperdrive Python 驅動。')
log('insight','Cloudflare 官方已有 Flask Python Workers 文件，但 PostgreSQL 驅動需實證。workers.dev 是平台提供的網址；隨機 trycloudflare.com 僅短期展示。Resend 對一般用戶發信需自有已驗證寄件網域，不能拿 workers.dev 當寄件網域。')
log('direction','視覺建議：繁體中文、桌面三欄與手機單欄，獨立品牌暫稱「串連」，採熟悉的社群互動與清楚的狀態提示；此為提案而非用戶已確認選擇。')
log('decision','驗收：兩個獨立帳號完成實際驗證與互動；測試過期及重複權杖、未驗證不能寫入、非作者不能改刪、登出失效、分頁無重複、重新整理資料保留與手機操作。未部署或發信前不得聲稱已上線。')
log('direction','參考來源 https://developers.cloudflare.com/workers/languages/python/packages/flask/ ; https://developers.cloudflare.com/containers/ ; https://developers.cloudflare.com/hyperdrive/reference/supported-databases-and-features/ ; https://resend.com/docs/knowledge-base/403-error-resend-dev-domain 。本階段是發想規劃，尚未實作或部署網站。')
subprocess.run(['uv','run','--no-cache',str(SCRIPT),'set','--workspace',str(W),'--key','status','--value','complete'],check=True)
print('110 ideas logged:',W/'.memlog.md')
