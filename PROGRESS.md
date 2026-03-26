# 📊 Fantasy NBA 專案進度快照

**最後更新：2026-03-26**
**狀態：⚠️ 任務 7 部署中 — Railway 環境變數設定問題排查**

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

## ⚠️ 進行中：任務 7 — Railway 部署

**Railway 網址：** https://web-production-d742.up.railway.app
**GitHub Repo：** https://github.com/shelton0531/fantasy-nba-demo

**目前狀態：**
- ✅ 應用程式成功部署並運行
- ✅ 前端頁面可存取
- ✅ `source: env_individual` — 確認個別環境變數有被讀取
- ⚠️ Token 過期問題 — `YAHOO_TOKEN_CREATED_AT` 未正確更新

**Railway 需設定的環境變數（4個）：**
```
YAHOO_ACCESS_TOKEN=<access_token 值>
YAHOO_REFRESH_TOKEN=ACrExGl9kKScnLYTydlbO0mvZypb~001~eiHrfW_5NOp21s47C5hzCo_5mJsL648DUQ--
YAHOO_TOKEN_EXPIRES_IN=3600
YAHOO_TOKEN_CREATED_AT=<created_at Unix timestamp>
```

**問題根因：** Token 每小時過期，目前每次都需手動刷新後更新 Railway 環境變數。長遠解法是接資料庫或 Railway Volume。

**排查紀錄：**
- `YAHOO_TOKEN_JSON`（整體 JSON）→ 失敗（Railway 貼入多行 JSON 被截斷）
- 改用 4 個個別環境變數 → 成功讀取，但 `YAHOO_TOKEN_CREATED_AT` 更新有延遲問題

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
cd "C:\Vibe coding\fantasy-nba-demo"
python3 -m flask run --port 5000

# 刷新 token（每小時執行一次）
python3 -c "from yahoo_config import refresh_access_token; refresh_access_token()"

# 取得最新環境變數值
python3 -c "
import json, time
t = json.load(open('yahoo_token.json'))
print(f'YAHOO_ACCESS_TOKEN={t[\"access_token\"]}')
print(f'YAHOO_TOKEN_CREATED_AT={t[\"created_at\"]}')
"

# 驗證部署
curl https://web-production-d742.up.railway.app/api/token-status
curl https://web-production-d742.up.railway.app/api/matchup
```

---

**最後測試：** 2026-03-26
- 本地：✅ Token 正常，Yahoo API 真實數據運作中
- Railway：⚠️ 環境變數 YAHOO_TOKEN_CREATED_AT 更新延遲，token 顯示過期
