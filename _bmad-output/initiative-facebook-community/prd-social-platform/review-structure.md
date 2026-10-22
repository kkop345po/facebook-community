# Structure review

本文件組合供測試召集人、設計與開發人員確認內部測試版的範圍、可觀察行為、驗收出口及實作前提。

- Lens：structure；讀者：humans；基準：Microsoft Writing Style Guide。
- 結構模型：Strategic/Context (Pyramid)。
- 範圍：只評估影響理解的組織方式；不修改需求、驗收條件或原文。
- 計量：分別執行指定的 `uv run --no-cache .../word_metrics.py <path>`，PRD 為 4,909 words，addendum 為 1,008 words，合計 5,917。數值沿用工具的計量定義。

| Pass | Original Text | Revised Text | Changes |
| --- | --- | --- | --- |
| structure | PRD §6「第一版取捨與體驗方向」（243 words），位於詳細 FR 與 NFR 之後。 | MOVE：將整節移至 §1 之後、對象與關鍵流程之前；保留 A7、A8、FR 編號與全部內容，必要時同步章節引用。 | 先交代第一版納入、延後與排除的功能，以及全站內容可見性，再讓讀者閱讀流程和逐項驗收，符合 Pyramid 的概覽先於細節。移動 243 words，刪減 0 words。 |

addendum 未發現需要調整的結構問題：開頭先界定補充文件與未部署狀態，再列指定技術、候選方案及驗證、網址與寄件前提、安全注意，最後附來源，足以支持實作決策。

總計 1 項建議；若採納，預估刪減 0 words（PRD 0%；兩份合計 0%）。未提供長度目標。此建議不刪除任何驗收、假設、例子或證據界線，沒有以縮短篇幅犧牲理解的取捨。
