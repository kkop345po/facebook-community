# Code Review — 2026-10-22

四個獨立審查角度已完成。範圍為 server.py、main.jsx、npc_worker.py、啟動腳本與原有測試。無 Git baseline，因此以完整檔案檢查，不能視為歷史差異比較。

使用者要求先停止開發並上傳此快照。已套用本輪修正，26 項 pytest 通過；瀏覽器延遲對話切換已重現兩次且通過，跨帳號私訊清除已實測。完整瀏覽器測試重播與所有並行情境驗證仍需接續，不代表全站正式驗收。

## 分類結果

- F1 [high] [patch] Email 預先註冊保留舊密碼：高：Email 驗證僅切 verified，原密碼保留，需在驗證時由信箱擁有者設定密碼。（來源：blind-hunter；原項目：R1）
- F2 [high] [patch] 登出保留私訊狀態：高：logout 未清 convs/msgs/activeConv，新帳號可短暫看到上個帳號資料。 / 高：loadConvs 無 auth epoch，登出前 GET 可覆蓋新登入狀態。（來源：blind-hunter；原項目：R2, R3）
- F3 [medium] [patch] 成員清單截斷30人：中：members 無游標，舊作者個人頁不可達。 / 中：members 無游標，舊作者個人頁不可達。（來源：blind-hunter+edge-case-hunter；原項目：R4, R15）
- F4 [medium] [patch] 對話清單截斷50則：中：conversations 無游標且未讀只算前50組。 / 中：conversations 無游標且未讀只算前50組。（來源：blind-hunter+edge-case-hunter；原項目：R5, R16）
- F5 [high] [patch] 讀取私訊標記未傳回訊息已讀：高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。 / 高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。（來源：blind-hunter+edge-case-hunter；原項目：R6, R11）
- F6 [high] [patch] 留言修改後沿用冪等鍵：高：成功但遺失回應再修改重送會清空未儲存文字。 / 高：成功但遺失回應再修改重送會清空未儲存文字。（來源：blind-hunter+edge-case-hunter；原項目：R7, R13）
- F7 [high] [patch] 輪詢超50則漏訊息：高：quiet 刷新最新50且保留舊cursor，缺口不可讀。 / 高：quiet 刷新最新50且保留舊cursor，缺口不可讀。（來源：blind-hunter+edge-case-hunter；原項目：R8, R12）
- F8 [medium] [patch] NPC 並行重覆回覆：中：無單工鎖且每次新reply UUID。 / 中：無單工鎖且每次新reply UUID。（來源：blind-hunter+edge-case-hunter；原項目：R9, R18）
- F9 [medium] [patch] NPC 上下文越過處理範圍：中：history 未限制觸發msg_id，未讀批次可能重覆回答。 / 中：history 未限制觸發msg_id，未讀批次可能重覆回答。（來源：blind-hunter+edge-case-hunter；原項目：R10, R19）
- F10 [medium] [patch] Google挑戰10分鐘過期：中：頁面久置後登入先失敗再重試；需定時更新challenge。（來源：edge-case-hunter；原項目：R14）
- F11 [medium] [patch] 停用作者貼文互動503：中：post_json 對 inactive作者返回None後解參照。（來源：edge-case-hunter；原項目：R17）
- F12 [medium] [patch] NPC首次啟動缺runtime：中：Start-Npc 未建日誌目錄。（來源：edge-case-hunter；原項目：R20）
- F13 [medium] [patch] 成功寄信未驗證：中：缺 accepted response / sent+provider_id / no resend 回歸測試。（來源：verification-gap；原項目：R21）
- F14 [medium] [patch] NPC持久化缺回歸：中：缺確認僅ack cutoff及recipient可見測試。（來源：verification-gap；原項目：R22）
- F15 [medium] [patch] 對話切換競態缺UI驗證：中：缺延遲A回應不覆蓋B的渲染測試。（來源：verification-gap；原項目：R23）
- F16 [medium] [defer] Resend寄送受限：確實限制收件者；使用者明確不買網域，保留Google登入，無法宣稱寄信全面完成。（來源：intent-alignment；原項目：R26）
- F17 [medium] [defer] 第三方信箱Google拒絕：刻意安全限制，首次使用非Gmail/Workspace以Email註冊；Google帳號link功能暫不擴增。（來源：intent-alignment；原項目：R27）

## 原始分類與排除依據

```json
[
  {
    "id": "R1",
    "source": "blind-hunter",
    "title": "Email 預先註冊保留舊密碼",
    "detail": "高：Email 驗證僅切 verified，原密碼保留，需在驗證時由信箱擁有者設定密碼。",
    "verdict": "high",
    "evidence": "高：Email 驗證僅切 verified，原密碼保留，需在驗證時由信箱擁有者設定密碼。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R2",
    "source": "blind-hunter",
    "title": "登出保留私訊狀態",
    "detail": "高：logout 未清 convs/msgs/activeConv，新帳號可短暫看到上個帳號資料。",
    "verdict": "high",
    "evidence": "高：logout 未清 convs/msgs/activeConv，新帳號可短暫看到上個帳號資料。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R3",
    "source": "blind-hunter",
    "title": "遲到對話回應跨帳號覆蓋",
    "detail": "高：loadConvs 無 auth epoch，登出前 GET 可覆蓋新登入狀態。",
    "verdict": "high",
    "evidence": "高：loadConvs 無 auth epoch，登出前 GET 可覆蓋新登入狀態。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R4",
    "source": "blind-hunter",
    "title": "成員清單截斷30人",
    "detail": "中：members 無游標，舊作者個人頁不可達。",
    "verdict": "medium",
    "evidence": "中：members 無游標，舊作者個人頁不可達。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R5",
    "source": "blind-hunter",
    "title": "對話清單截斷50則",
    "detail": "中：conversations 無游標且未讀只算前50組。",
    "verdict": "medium",
    "evidence": "中：conversations 無游標且未讀只算前50組。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R6",
    "source": "blind-hunter",
    "title": "讀取私訊標記未傳回訊息已讀",
    "detail": "高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。",
    "verdict": "high",
    "evidence": "高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R7",
    "source": "blind-hunter",
    "title": "留言修改後沿用冪等鍵",
    "detail": "高：成功但遺失回應再修改重送會清空未儲存文字。",
    "verdict": "high",
    "evidence": "高：成功但遺失回應再修改重送會清空未儲存文字。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R8",
    "source": "blind-hunter",
    "title": "輪詢超50則漏訊息",
    "detail": "高：quiet 刷新最新50且保留舊cursor，缺口不可讀。",
    "verdict": "high",
    "evidence": "高：quiet 刷新最新50且保留舊cursor，缺口不可讀。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R9",
    "source": "blind-hunter",
    "title": "NPC 並行重覆回覆",
    "detail": "中：無單工鎖且每次新reply UUID。",
    "verdict": "medium",
    "evidence": "中：無單工鎖且每次新reply UUID。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R10",
    "source": "blind-hunter",
    "title": "NPC 上下文越過處理範圍",
    "detail": "中：history 未限制觸發msg_id，未讀批次可能重覆回答。",
    "verdict": "medium",
    "evidence": "中：history 未限制觸發msg_id，未讀批次可能重覆回答。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R11",
    "source": "edge-case-hunter",
    "title": "未顯示私訊被標已讀",
    "detail": "高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。",
    "verdict": "high",
    "evidence": "高：UPDATE 覆蓋全部歷史及 SELECT 後新到訊息。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R12",
    "source": "edge-case-hunter",
    "title": "輪詢漏訊息",
    "detail": "高：quiet 刷新最新50且保留舊cursor，缺口不可讀。",
    "verdict": "high",
    "evidence": "高：quiet 刷新最新50且保留舊cursor，缺口不可讀。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R13",
    "source": "edge-case-hunter",
    "title": "留言重送遺失文字",
    "detail": "高：成功但遺失回應再修改重送會清空未儲存文字。",
    "verdict": "high",
    "evidence": "高：成功但遺失回應再修改重送會清空未儲存文字。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R14",
    "source": "edge-case-hunter",
    "title": "Google挑戰10分鐘過期",
    "detail": "中：頁面久置後登入先失敗再重試；需定時更新challenge。",
    "verdict": "medium",
    "evidence": "中：頁面久置後登入先失敗再重試；需定時更新challenge。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R15",
    "source": "edge-case-hunter",
    "title": "成員截斷",
    "detail": "中：members 無游標，舊作者個人頁不可達。",
    "verdict": "medium",
    "evidence": "中：members 無游標，舊作者個人頁不可達。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R16",
    "source": "edge-case-hunter",
    "title": "對話未讀截斷",
    "detail": "中：conversations 無游標且未讀只算前50組。",
    "verdict": "medium",
    "evidence": "中：conversations 無游標且未讀只算前50組。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R17",
    "source": "edge-case-hunter",
    "title": "停用作者貼文互動503",
    "detail": "中：post_json 對 inactive作者返回None後解參照。",
    "verdict": "medium",
    "evidence": "中：post_json 對 inactive作者返回None後解參照。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R18",
    "source": "edge-case-hunter",
    "title": "NPC重覆回覆",
    "detail": "中：無單工鎖且每次新reply UUID。",
    "verdict": "medium",
    "evidence": "中：無單工鎖且每次新reply UUID。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R19",
    "source": "edge-case-hunter",
    "title": "NPC越界上下文",
    "detail": "中：history 未限制觸發msg_id，未讀批次可能重覆回答。",
    "verdict": "medium",
    "evidence": "中：history 未限制觸發msg_id，未讀批次可能重覆回答。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R20",
    "source": "edge-case-hunter",
    "title": "NPC首次啟動缺runtime",
    "detail": "中：Start-Npc 未建日誌目錄。",
    "verdict": "medium",
    "evidence": "中：Start-Npc 未建日誌目錄。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R21",
    "source": "verification-gap",
    "title": "成功寄信未驗證",
    "detail": "中：缺 accepted response / sent+provider_id / no resend 回歸測試。",
    "verdict": "medium",
    "evidence": "中：缺 accepted response / sent+provider_id / no resend 回歸測試。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R22",
    "source": "verification-gap",
    "title": "NPC持久化缺回歸",
    "detail": "中：缺確認僅ack cutoff及recipient可見測試。",
    "verdict": "medium",
    "evidence": "中：缺確認僅ack cutoff及recipient可見測試。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R23",
    "source": "verification-gap",
    "title": "對話切換競態缺UI驗證",
    "detail": "中：缺延遲A回應不覆蓋B的渲染測試。",
    "verdict": "medium",
    "evidence": "中：缺延遲A回應不覆蓋B的渲染測試。",
    "location": "app/server.py or app/src/main.jsx or app/npc_worker.py; see original reviewer findings"
  },
  {
    "id": "R24",
    "source": "intent-alignment",
    "title": "公開站證據不在diff",
    "detail": "現有 PROJECT_REPORT 記錄並已實際驗證公開網址，diff未包含部署檔不代表未部署。",
    "verdict": "false",
    "evidence": "現有 PROJECT_REPORT 記錄並已實際驗證公開網址，diff未包含部署檔不代表未部署。",
    "rejected": true,
    "reason": "依已確認需求與現有部署證據評估"
  },
  {
    "id": "R25",
    "source": "intent-alignment",
    "title": "真實Google登入不在測試",
    "detail": "使用者已回報成功，已有公開站按鈕及Google設定證據；mock測試本來不證明真人OAuth。",
    "verdict": "low",
    "evidence": "使用者已回報成功，已有公開站按鈕及Google設定證據；mock測試本來不證明真人OAuth。",
    "rejected": true,
    "reason": "依已確認需求與現有部署證據評估"
  },
  {
    "id": "R26",
    "source": "intent-alignment",
    "title": "Resend寄送受限",
    "detail": "確實限制收件者；使用者明確不買網域，保留Google登入，無法宣稱寄信全面完成。",
    "verdict": "medium",
    "evidence": "確實限制收件者；使用者明確不買網域，保留Google登入，無法宣稱寄信全面完成。",
    "rejected": false,
    "reason": "依已確認需求與現有部署證據評估"
  },
  {
    "id": "R27",
    "source": "intent-alignment",
    "title": "第三方信箱Google拒絕",
    "detail": "刻意安全限制，首次使用非Gmail/Workspace以Email註冊；Google帳號link功能暫不擴增。",
    "verdict": "medium",
    "evidence": "刻意安全限制，首次使用非Gmail/Workspace以Email註冊；Google帳號link功能暫不擴增。",
    "rejected": false,
    "reason": "依已確認需求與現有部署證據評估"
  },
  {
    "id": "R28",
    "source": "intent-alignment",
    "title": "不是完整Facebook",
    "detail": "完整產品同等功能未承諾在品質改善輪次補齊，已明列功能差距。",
    "verdict": "low",
    "evidence": "完整產品同等功能未承諾在品質改善輪次補齊，已明列功能差距。",
    "rejected": true,
    "reason": "依已確認需求與現有部署證據評估"
  },
  {
    "id": "R29",
    "source": "intent-alignment",
    "title": "不是邀請制",
    "detail": "使用者明確要求取消內部測試邀請碼，開放註冊是已確認需求。",
    "verdict": "false",
    "evidence": "使用者明確要求取消內部測試邀請碼，開放註冊是已確認需求。",
    "rejected": true,
    "reason": "依已確認需求與現有部署證據評估"
  }
]
```

## 保留事項

- Resend 網域與第三方信箱 Google 限制依現有選擇保留。
- Turnstile API Token 尚未提供，未建立元件或宣稱正式防護。
- 上述實測證明不包含寄信投遞至所有第三方信箱或所有 Google 帳號種類。
