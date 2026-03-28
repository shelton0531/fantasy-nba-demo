---
name: Complete Project Plan
description: Full project roadmap with all phases, major tasks, and subtasks
type: project
---

# 🎯 Fantasy NBA Demo — 完整專案計畫

**項目目標：** 建立 Fantasy NBA 聯盟管理應用，最終部署到 Telegram 和 LINE 平台

---

## 📐 項目結構

```
Fantasy NBA Demo
├─ Phase 1: Web App 開發 [✅ 100% 完成]
├─ Phase 2: 真實數據集成 [✅ 100% 完成]
└─ Phase 3: 多平台部署 [⏳ 85% 進行中]
   ├─ Task 7: Railway 部署 ⏳
   ├─ Task 8: 周次切換 🔜
   ├─ Task 10: 響應式設計 🔜
   ├─ Task 11: Telegram Web App 🔜
   └─ Task 12: LINE MINI App 🔜
```

---

## 🚀 Phase 1: Web App 開發 ✅ 100% 完成

### 大任務：後端 API 框架 ✅
- ✅ Flask 基礎設置
- ✅ 靜態資源配置
- ✅ CORS 支持
- ✅ 路由結構規劃

### 大任務：數據模型 ✅
- ✅ players_data.json 加載
- ✅ my_roster.json 定義（16 球員）
- ✅ 統計欄位映射（PTS/REB/AST/STL/BLK/FG%/FT%/3PM）

### 大任務：前端 UI ✅

#### 小任務 1-1: 基礎頁面佈局
- ✅ 響應式導航欄
- ✅ Tab 切換系統
- ✅ 底部工具欄

#### 小任務 1-2: 我的陣容 (My Roster) Tab
- ✅ 球員卡片展示
- ✅ 排序功能（名稱/位置/評分）
- ✅ 搜尋功能
- ✅ 詳細數據顯示

#### 小任務 1-3: 本週對戰 (Matchup) Tab
- ✅ H2H 類別制對比
- ✅ 統計數據展示
- ✅ lower_is_better 標記
- ✅ 贏/輸/平估算

#### 小任務 1-4: 自由球員 (Free Agents) Tab
- ✅ 推薦球員列表
- ✅ 排序和篩選
- ✅ 評分系統

#### 小任務 1-5: 新聞 (News) Tab
- ✅ 球員新聞 ticker
- ✅ 更新通知

#### 小任務 1-6: 聯盟 (League) Tab
- ✅ 全部 10 隊顯示
- ✅ 150+ 球員數據對照
- ✅ 我的隊伍橘框標記

### 大任務：API 端點 ✅

#### 小任務 1-7: 基礎端點
- ✅ `GET /api/roster` — 我的陣容 (16 球員)
- ✅ `GET /api/matchup` — 本週對戰
- ✅ `GET /api/free-agents` — 自由球員
- ✅ `GET /api/league` — 聯盟全隊

#### 小任務 1-8: 補助端點
- ✅ `GET /api/news` — 球員新聞
- ✅ `GET /api/ai-recommendations` — AI 建議

---

## 🔄 Phase 2: 真實數據集成 ✅ 100% 完成

### 大任務：Yahoo Fantasy API 認證

#### 小任務 2-1: OAuth 2.0 實現
- ✅ 簡化版 OAuth 流程（oauth2_login.py）
- ✅ Token 獲取和儲存
- ✅ Token 刷新機制

#### 小任務 2-2: Token 管理
- ✅ `yahoo_config.py` 優先順序加載
  1. 記憶體暫存 (_token_override)
  2. 個別環境變數 (YAHOO_ACCESS_TOKEN + YAHOO_REFRESH_TOKEN)
  3. JSON 環境變數 (YAHOO_TOKEN_JSON)
  4. 本地檔案 (yahoo_token.json)
- ✅ Token 過期檢測
- ✅ 自動刷新機制

### 大任務：Yahoo 數據獲取

#### 小任務 2-3: 聯盟信息
- ✅ Game key 修正 (466 = 2025-26 賽季)
- ✅ League key 獲取 (466.l.46147)
- ✅ 聯盟隊伍列表

#### 小任務 2-4: 隊伍和陣容數據
- ✅ 我的隊伍信息取得 (team_id: 2)
- ✅ 本週對手信息取得 (team_id: 10)
- ✅ 對手球員統計

#### 小任務 2-5: 即時統計
- ✅ 本週我的隊伍統計
  - PTS: 405, REB: 136, AST: 106
  - STL: 30, BLK: 14, FG%: 50.0%, FT%: 77.1%, 3PM: 24
- ✅ 對手統計
  - PTS: 363, REB: 137, AST: 117
  - STL: 25, BLK: 16, FG%: 49.2%, FT%: 78.9%, 3PM: 43

### 大任務：前端數據整合

#### 小任務 2-6: 真實對手信息
- ✅ 對手隊伍名稱顯示 (葉來葉好玩葉董好好玩)
- ✅ 對手陣容展示

#### 小任務 2-7: 新 API 端點
- ✅ `GET /api/token-status` — Token 狀態（source/created_at/elapsed_minutes）
- ✅ 前端動態調用 Yahoo API

---

## 🚀 Phase 3: 多平台部署 ⏳ 85% 進行中

### 🔴 Task 7: Railway Volume Token 持久化 ⏳ 進行中

**優先級:** 🔴 立即 (阻塞所有後續任務)
**狀態:** ⏳ 最後一步待完成
**預期完成:** 今日

#### 小任務 7-1: Railway 基礎設置 ✅
- ✅ 應用部署到 Railway (https://web-production-d742.up.railway.app)
- ✅ 環境變數配置 (TOKEN_DIR=/data, CURRENT_WEEK=22)
- ✅ Volume 掛載 (Mount Path: /data)

#### 小任務 7-2: Token 初始化方案 ✅
- ✅ `app.py` 新增 `initialize_token_file()` 函數
- ✅ 應用啟動時從環境變數初始化 token
- ✅ Commit f0e230d 已推送

#### 小任務 7-3: 本地 Token 刷新 ✅
- ✅ 本地執行 `flask run` 觸發自動刷新
- ✅ Token created_at: 1774601972 (2026-03-27 16:59:32)
- ✅ 存儲於 `yahoo_token.json`

#### 小任務 7-4: Railway 部署確認 ⏳
- ⏳ Railway login 完成 (用戶已完成)
- ⏳ 執行 `python3 deploy_token.py` 上傳 token 到 Volume
- ⏳ 驗證 `/api/token-status` 返回 "status": "ok"
- ⏳ 確認自動刷新機制工作正常

**完成標準：**
```bash
curl https://web-production-d742.up.railway.app/api/token-status
# 預期: {"status": "ok", "source": "file", "created_at": 1774601972, ...}
```

---

### 🟡 Task 8: 周次切換功能 🔜 待啟動

**優先級:** 🟡 高 (Phase 3 第二優先)
**依賴:** Task 7 完成
**預期完成:** Task 7 完成後 1-2 天

#### 小任務 8-1: 後端支持
- [ ] 修改 API 接受 `?week=N` 參數
- [ ] 查詢特定周次對戰數據
- [ ] 從 Yahoo API 獲取周次時間表

#### 小任務 8-2: 環境變數支持
- [ ] 支持 `CURRENT_WEEK` 環境變數
- [ ] Railway Dashboard 可動態修改周次

#### 小任務 8-3: 前端 UI
- [ ] 周次選擇器（下拉或按鈕）
- [ ] 周次信息展示（如 Week 22: March 20-26）
- [ ] 切換周次後刷新數據

---

### 🟢 Task 10: 響應式設計優化 🔜 待啟動

**優先級:** 🟢 中
**依賴:** 無
**預期完成:** Task 8 之後

#### 小任務 10-1: 手機佈局
- [ ] 調整導航欄（手機底部欄）
- [ ] 球員卡片響應式調整
- [ ] 統計表格響應式

#### 小任務 10-2: 觸控交互
- [ ] 手勢滑動支持
- [ ] 按鈕大小優化（最小 44px）
- [ ] 字體大小調整

#### 小任務 10-3: 測試
- [ ] iOS Safari 測試
- [ ] Android Chrome 測試
- [ ] 平板設備測試

---

### 🔵 Task 11: Telegram Web App 集成 🔜 待啟動

**優先級:** 🔵 高（快速上線）
**狀態:** 規劃中
**預期完成:** 2-3 天

#### 小任務 11-1: Telegram Bot 設置
- [ ] 創建 Telegram Bot (@BotFather)
- [ ] 取得 Bot Token
- [ ] 設置 webhook 或 polling

#### 小任務 11-2: Web App 配置
- [ ] 在 Bot 中註冊 Web App 路徑
- [ ] 配置 Mini App 資訊
- [ ] 設定應用圖標和顏色

#### 小任務 11-3: Web App 集成
- [ ] 前端識別 Telegram 環境
- [ ] 集成 Telegram SDK (`TelegramWebApp.js`)
- [ ] 用戶認證（Telegram ID）
- [ ] 傳送數據回 Bot

#### 小任務 11-4: 測試和發佈
- [ ] Telegram 中本地測試
- [ ] 邀請用戶測試
- [ ] 發佈到 Telegram 應用商店

---

### 🟣 Task 12: LINE MINI App 申請 🔜 待啟動

**優先級:** 🟣 中（台灣市場）
**狀態:** 規劃中
**依賴:** Task 11 完成後
**預期完成:** 3-5 天

#### 小任務 12-1: LINE 官方帳號設置
- [ ] 建立 LINE 官方帳號
- [ ] 申請 LINE Bot Developer Account
- [ ] 取得 Channel ID 和 Secret

#### 小任務 12-2: MINI App 申請資料準備
- [ ] 應用截圖
- [ ] 應用描述（繁體中文）
- [ ] 隱私政策
- [ ] 使用條款

#### 小任務 12-3: 應用配置
- [ ] 上傳 MINI App 到 LINE 平台
- [ ] 設定應用權限
- [ ] 配置帳號連結

#### 小任務 12-4: 審核和發佈
- [ ] 提交審核
- [ ] 跟進審核進度
- [ ] 上架 LINE 應用商店

---

## 📊 進度統計

| 階段 | 完成度 | 狀態 |
|-----|--------|------|
| Phase 1: Web App | 100% ✅ | 完成 |
| Phase 2: 真實數據 | 100% ✅ | 完成 |
| Phase 3a: Railway 部署 | 85% ⏳ | 進行中（Task 7） |
| Phase 3b: 周次功能 | 0% 🔜 | 待啟動（Task 8） |
| Phase 3c: 響應式設計 | 0% 🔜 | 待啟動（Task 10） |
| Phase 3d: Telegram Web App | 0% 🔜 | 待啟動（Task 11） |
| Phase 3e: LINE MINI App | 0% 🔜 | 待啟動（Task 12） |

**總體進度:** 61% 完成

---

## 🔑 關鍵里程碑

| 里程碑 | 日期 | 狀態 |
|------|------|------|
| Web App 上線 | ✅ 2026-03-20 | 完成 |
| Yahoo API 集成 | ✅ 2026-03-24 | 完成 |
| Railway 部署 | ⏳ 2026-03-28 | 進行中 |
| 周次切換功能 | 🔜 2026-03-30 | 計劃中 |
| 響應式設計完成 | 🔜 2026-04-05 | 計劃中 |
| Telegram 上線 | 🔜 2026-04-10 | 計劃中 |
| LINE MINI App 上線 | 🔜 2026-04-20 | 計劃中 |

---

## 🔗 相關文件

- `CLAUDE.md` — 專案配置和規則
- `PROGRESS.md` — 詳細進度快照
- `app.py` — Flask 應用主文件
- `templates/index.html` — 前端主頁面
- `yahoo_api.py` — Yahoo API 客戶端
- `yahoo_config.py` — Token 管理
