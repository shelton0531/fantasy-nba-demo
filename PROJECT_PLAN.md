# BD Lead Finder — 專案計畫書
## 專為時尚美妝精品品牌業務開發設計

---

## 1. 專案背景與目標

### 背景
目前 BD 工作高度依賴人工，陌生開發流程無法系統性地找到符合條件的目標客戶。缺乏一個能夠「由大到小」——先找符合 ICP 的品牌公司，再找該公司 key decision maker，最後取得有效聯絡方式——的整合工具。

### 核心目標
- 每週產出 25 個有效 leads
- 每月累計 100 個 qualified leads
- 每個 lead 包含：公司基本資料 + 聯繫人清單 + 可用 email

---

## 2. 目標客戶輪廓（ICP）

| 條件 | 規格 |
|------|------|
| 行業 | 時尚、美妝、精品、肌膚保養品牌 |
| 地區 | 台灣、新加坡、澳洲、紐西蘭、香港、北歐國家 |
| 公司規模 | 50–300 人 |
| 目標職位 | CEO、CMO、VP Marketing、Brand Director、Head of BD、Marketing Manager |

---

## 3. 技術架構

### 基礎：chaitanyya/sales（修改版）
- Repository: https://github.com/chaitanyya/sales
- Framework: Next.js + SQLite + Drizzle ORM
- AI 引擎: Claude Code CLI（Pro $20/月）
- UI: shadcn/ui + Tailwind CSS

### 新增模組
1. **ICP Prompt 客製化** — 移除產業深度分析，專注品牌篩選
2. **Scorer 評分模組** — 0–100 分 + 評分理由 + pending_review 狀態
3. **Company Grouping** — 同公司聯繫人自動歸群標籤
4. **Email Finder** — MX 記錄驗證 + email 格式推斷 + Hunter.io 整合

---

## 4. 功能規格

### 4.1 公司搜尋（Company Discovery）
- 輸入：行業 + 地區 + 規模條件
- 輸出：符合條件的品牌公司清單
- 每家公司資料：名稱、官網、所在地、主要產品線、員工規模、ICP 符合原因（一句話）
- Token 預算：每家公司 ≤ 15,000 tokens

### 4.2 聯繫人搜尋（People Discovery）
- 輸入：公司名稱 + 目標職位
- 輸出：聯繫人清單（姓名、職位、LinkedIn URL、推斷 email）
- 同公司聯繫人自動標記相同 company_tag
- 顯示方式：以公司為群組展開，不散落呈現

### 4.3 智能評分（AI Scorer）
- 評分維度：ICP 符合度、職位決策權重、地區優先級、公司成長訊號
- 輸出格式：分數（0–100）+ 評分理由（3–5 點）+ 建議行動
- 分數分級：
  - 80–100：High Priority，立即聯繫
  - 60–79：Medium，納入本週 pipeline
  - 40–59：Low，保留觀察（pending_review）
  - 0–39：Disqualified，標記原因後封存

### 4.4 Email 驗證（Email Verifier）
- 四層驗證：格式檢查 → MX 記錄 → Hunter.io API → SMTP 握手
- 信心等級：high / medium / low / invalid
- 輸出：最可能有效的 email + 備選格式

---

## 5. 工作流程

```
Step 1: 設定搜尋條件（行業 + 地區 + 規模）
           ↓
Step 2: Claude 搜尋符合條件的品牌公司
           ↓
Step 3: AI Scorer 對每家公司評分
           ↓
Step 4: 高分公司 → 進入 People Discovery
           ↓
Step 5: 找出 key decision makers + 推斷 email
           ↓
Step 6: Email 驗證，輸出可用聯絡清單
           ↓
Step 7: 匯出 CSV，進入 outreach 流程
```

---

## 6. 預算與資源

| 項目 | 費用 | 說明 |
|------|------|------|
| Claude Pro | $20/月 | 涵蓋所有 Claude Code 用量 |
| Hunter.io | $0 | 免費 25 次/月驗證 |
| 開發時間 | 2–3 天 | 修改現有 chaitanyya/sales |

**每月總成本：$20 USD（NT$640）**

---

## 7. 執行時程

| 週次 | 任務 |
|------|------|
| Week 1 | Clone repo + 環境設定 + ICP Prompt 客製化 |
| Week 1 | 測試搜尋品質，調整 Prompt |
| Week 2 | 加入 Scorer 模組 + 評分邏輯 |
| Week 2 | 加入 Company Grouping 功能 |
| Week 3 | 整合 Email Verifier |
| Week 3 | 端到端測試，跑第一批 25 個 leads |

---

## 8. 成功指標

- 每週 25 個 leads，其中 ≥ 60 分的 qualified leads ≥ 15 個
- Email 命中率 ≥ 40%（無 Apollo 免費版的合理預期）
- 每個 lead 的處理時間 ≤ 5 分鐘人工介入

---

## 9. 已知限制與假設

- 不使用付費 API（Apollo、ZoomInfo 等），email 命中率受限
- chaitanyya/sales 的 web search 能力依賴 Claude Code CLI 內建搜尋
- 北歐地區的品牌資料在 Claude 訓練資料中可能較少，搜尋品質需測試
- Hunter.io 免費版每月 25 次驗證，超量需手動處理
