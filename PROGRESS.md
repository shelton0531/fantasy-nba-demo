# 📊 Fantasy NBA 專案進度快照

**最後更新：2026-03-27**
**狀態：⚠️ 任務 7 部署中 — Railway Volume 掛載待確認**

---

## 🎯 進度概覽

```
第一階段：Web App 開發
├─ ✅ 後端 API（Flask）
├─ ✅ 前端 UI（HTML/CSS/JS）
├─ ✅ 數據展示修復
└─ ✅ H2H 類別制優化

第二階段：真實數據集成
├─ ✅ OAuth Token 取得
├─ ✅ 修正 game_key（466，2025-26 賽季）
├─ ✅ Yahoo API 整合（真實對手統計）
├─ ✅ 前端顯示真實對手名稱（任務 4）
├─ ✅ Token 自動續期（任務 5）
├─ ✅ Token 部署方案（任務 6）
└─ ✅ 全聯盟陣容頁面（任務 9）

第三階段：部署
├─ ⚠️ Railway 部署（任務 7）— 應用程式已啟動，環境變數設定中
├─ ⏳ 週次切換（任務 8，部署後）
├─ ⏳ Telegram Web App（任務 11）
└─ ⏳ LINE MINI App（任務 12）
```

---

## ✅ 已完成項目

### 任務 1-5：前端修復、H2H UI、Yahoo API 整合 ✓

### 任務 6：Token 部署方案 ✓
`yahoo_config.py` load_token() 優先順序：
1. `_token_override`（記憶體暫存）
2. `YAHOO_ACCESS_TOKEN` + `YAHOO_REFRESH_TOKEN` 個別環境變數（最穩定）
3. `YAHOO_TOKEN_JSON` 整體 JSON 環境變數（備用）
4. `yahoo_token.json` 本地檔案

新增 `GET /api/token-status` 端點（含 source、created_at、elapsed_minutes 除錯資訊）

### 任務 9：全聯盟陣容頁面 ✓
- 10 隊全部取得，150+ 球員數據對照成功
- 前端「🏆 聯盟」Tab：排序、展開/收合、我的隊伍橘框

---

## ⚠️ 進行中：任務 7 — Railway 部署（Token 持久化）

**Railway 網址：** https://web-production-d742.up.railway.app
**GitHub Repo：** https://github.com/shelton0531/fantasy-nba-demo

**最新進度（2026-03-27）：**
- ✅ 應用程式成功部署並運行
- ✅ 前端頁面可存取
- ✅ Yahoo API 本地連線驗證通過（token 自動 refresh 成功）
- ✅ `yahoo_config.py` 改動完成：
  - CURRENT_WEEK 環境變數化（無需 push code 改週次）
  - Token 檔案路徑支援 TOKEN_DIR（為 Volume 掛載做準備）
- ✅ Commit `b4f096a` 已 push，Railway 自動 redeploy
- ⏳ Railway Volume 掛載待完成（用戶操作 Dashboard）

**待做（用戶在 Railway Dashboard）：**
1. Volumes → Add Volume → Mount Path: `/data`
2. Environment Variables 新增：`TOKEN_DIR=/data`, `CURRENT_WEEK=22`
3. 上傳 `yahoo_token.json` 到 Volume `/data/`（方式 A: 腳本 / 方式 B: UI 手動）
4. web service 手動 Redeploy

**解法說明：**
使用 Railway Persistent Volume，token auto-refresh 會自動寫回 `/data/yahoo_token.json`，
完全無需手動更新環境變數，永遠保持最新狀態。

---

## 🔑 關鍵設定

| 設定 | 值 |
|------|-----|
| 聯盟名稱 | Drink or Die 2.0 |
| game_key | 466（2025-26 賽季） |
| league_key | 466.l.46147 |
| 您的隊伍 | Hooters 歡迎黃董獨自光臨（team_id: 2） |
| 本週對手 | 葉來葉好玩葉董好好玩（team_id: 10） |
| 當前週次 | Week 22 |
| Railway 網址 | https://web-production-d742.up.railway.app |

---

## ⏳ 接下來的工作

### 🔴 立即：解決 Token 過期問題
目前每次 token 過期都要手動更新 Railway 環境變數。選項：
1. **短期**：接受手動更新（每 1 小時需操作一次）
2. **中期**：加入 `/api/refresh-token` 端點 + Railway Volume 儲存
3. **長期**：使用 Redis 或 PostgreSQL 儲存 token（Railway 有免費方案）

### 🟡 任務 8 — 週次切換（部署後）
修改 `CURRENT_WEEK = 23` 或新增 `/api/matchup?week=N`

---

## 💾 快速命令

```bash
# 本地啟動
cd "D:\Vibe coding\fantasy-nba-demo"
python3 -m flask run --port 5000

# 取得 yahoo_token.json 內容（上傳到 Railway Volume）
python3 -c "import json; print(json.dumps(json.load(open('yahoo_token.json')), indent=2))"

# 本地測試 Yahoo API 連線
python3 yahoo_api.py

# 驗證 Railway 部署
curl https://web-production-d742.up.railway.app/api/token-status
curl https://web-production-d742.up.railway.app/api/matchup

# 部署 token 到 Railway（需先 npm install -g @railway/cli && railway login）
python3 deploy_token.py
```

---

**最後測試：** 2026-03-27
- 本地：✅ Token 自動 refresh 成功，Yahoo API 真實數據運作完美
  - 本週對手：葉來葉好玩葉董好好玩
  - 我的統計：FG% 50.0%, FT% 77.1%, 3PM 24, PTS 405, REB 136, AST 106, STL 30, BLK 14, TOV 36
  - 對手統計：FG% 49.2%, FT% 78.9%, 3PM 43, PTS 363, REB 137, AST 117, STL 25, BLK 16, TOV 52
- Railway：⏳ 程式碼已部署，Volume 掛載待完成
