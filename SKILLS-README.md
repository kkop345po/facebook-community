# 專案 Skill 安裝說明

安裝位置：`.agents/skills/`，全部位於本 FaceBook 資料夾內。

- Cloudflare：19 個，來源 https://github.com/cloudflare/skills
- Google Cloud：149 個（含 Google Skill 搜尋及文件查詢），來源 https://github.com/google/skills
- Resend：5 個，來源 https://github.com/resend/resend-skills
- BMAD：31 個，來源 https://github.com/bmad-code-org/BMAD-METHOD
- QianProStudio（依使用者指定為 UI UX Pro Max）：1 個，來源 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

全部 205 個頂層 SKILL.md 已檢查 name、description 與前置資料格式。
下載版本與 commit 記錄在 skill-install-manifest.json。
BMAD 版本為官方 main 的 6.13.0-next，已完成 `_bmad/` runtime 與 core-tools、method、toolsmith 初始化。

## 使用

下一輪對話可要求使用指定 Skill；若清單尚未刷新，重新開啟本專案對話。

範例：
- 使用 cloudflare Skill 幫我規劃部署。
- 使用 google-cloud-solution-architecture Skill 規劃 GCP 架構。
- 使用 resend Skill 建立寄信功能。
- 使用 bmad 幫我開始專案規劃。

Skill 是操作指引及支援資源，並不等同已登入雲端服務。
Cloudflare 的 cf 已存在於本機；gcloud 與 resend CLI 未在 PATH 找到。
實際雲端操作仍須對應 CLI 或 SDK 與帳號驗證；Resend 發信須有效金鑰及已驗證網域。本次未部署雲端資源或寄送郵件。

## UI UX Pro Max 驗證

已執行本地 UX 搜尋，成功回傳鍵盤焦點規範。使用時將原始說明中的 `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max` 替換為本專案 `.agents/skills/ui-ux-pro-max` 的絕對路徑。

```powershell
python "C:/Users/GIGABYTE/Desktop/FaceBook/.agents/skills/ui-ux-pro-max/scripts/search.py" "keyboard focus visible" --domain ux -n 1
```
