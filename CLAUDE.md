# Fantasy NBA 專案 — CLAUDE.md

## 語言規則
- 當使用者以中文輸入時，必須以**繁體中文（正體中文）**回覆
- 嚴禁使用簡體中文
- 英文指令和程式碼保持英文不變

---

## 基本設定
- 專案路徑：G:\Vibe coding\fantasy-nba-demo
- 後端：Python / Flask (app.py)
- 啟動指令：python3 -m flask run --port 5000
- 瀏覽器：http://localhost:5000

---

## 聯盟設定
- 平台：Yahoo Fantasy Basketball
- 制度：Head to Head（H2H）類別制
- 不是總分制，不需要計算 Fantasy 總積分
- 顯示格式：PTS / REB / AST / STL / BLK / FG% / FT% / 3PM

---

## 數據來源
- 套件：nba_api（Python）
- 賽季：2025-26 當季真實數據
- 數據檔案：players_data.json（已存在於專案資料夾）
- ⚠️ 不需要重新抓取數據，直接讀取 players_data.json

---

## 我的陣容（16名球員）
1. Kennedy Chandler (UTA)
2. Tre Jones (CHI)
3. Deni Avdija (POR)
4. Gui Santos (GSW)
5. LeBron James (LAL)
6. P.J. Washington (DAL)
7. Deandre Ayton (LAL)
8. Amen Thompson (HOU)
9. Ace Bailey (UTA)
10. Paul George (PHI)
11. Bobby Portis (MIL)
12. Josh Hart (NYK)
13. DeMar DeRozan (SAC)
14. Shaedon Sharpe (POR)
15. Isaiah Collier (UTA)
16. Russell Westbrook (SAC)

---

## 產品形式（分階段）
- 第一階段：Web App 完成 → 部署到 Vercel → 給朋友測試
- 第二階段：包進 Telegram Web App（不需審核，快速）
- 第三階段：申請 LINE MINI App（台灣用戶公開使用）

---

## ⚡ 啟動說明
**重要：每次啟動 Claude Code 時，會自動強制讀取本檔案以獲取最新專案狀態。**
- 配置時間：2026-03-27
- 觸發機制：Claude 環境初始化時自動讀取 CLAUDE.md
- 目的：確保 Claude 隨時掌握最新進度、配置、和工作規則

---

## 目前進度（2026-03-27 最新確認）

### 🚀 專案狀態
**應用已上線：** https://web-production-d742.up.railway.app
**進度階段：** Phase 2 完成 → Phase 3 部署中
**最後更新：** PROGRESS.md (2026-03-27 16:59)

### ✅ 第一階段：Web App 開發 — 100% 完成
- ✅ 後端 API（Flask）— 完整實現
- ✅ 前端 UI（HTML/CSS/JS）— 所有版面完成
- ✅ 任務 1：修正前端數據顯示 — 6 項子任務完成
- ✅ 任務 2：H2H UI 優化 — 5 項子任務完成

### ✅ 第二階段：真實數據集成 — 100% 完成
- ✅ OAuth Token 取得 — Yahoo Fantasy API 認證成功
- ✅ 修正 game_key（466，2025-26 賽季）
- ✅ 任務 3：Yahoo API 整合 — 真實對手統計已連接
- ✅ 任務 4：前端顯示真實對手名稱 — 完成
- ✅ 任務 5：Token 自動續期 — 自動刷新機制已實現
- ✅ 任務 6：Token 部署方案 — 環境變數方案已配置
- ✅ 任務 9：全聯盟陣容頁面 — 150+ 球員數據對照完成

### ⏳ 第三階段：部署 — 進行中（任務 7）
**Railway 部署：** 應用程式已啟動，環境變數設定中
- ✅ 應用程式已上線：https://web-production-d742.up.railway.app
- ✅ 代碼已推送，自動部署完成
- ✅ Volume 初始化方案已實施（`initialize_token_file()`）
- ⏳ **待完成**：Railway Volume 持久化設定（見下方優先順序）

### ⏭️ 未來計畫
- 任務 8：週次切換（部署後）
- 任務 10：手機/响應式設計
- 任務 11：Telegram Web App 集成
- 任務 12：LINE MINI App 申請

---

## 🔴 立即優先順序（任務 7 — Railway Volume 持久化）

**5 分鐘完成，永久解決 Token 過期問題：**

1. 進入 Railway Dashboard
   - 專案：fantasy-nba-demo
   - Service：web
   - Tab：**Volumes**

2. 建立 Volume（如尚未建立）
   - Mount Path：`/data`
   - 點擊 Create

3. 進入 **Variables** Tab
   - 確認 `TOKEN_DIR = /data`
   - 確認 `CURRENT_WEEK = 22`

4. 上傳初始 Token 檔案到 Volume（本地執行）
   ```bash
   cd "G:\Vibe coding\fantasy-nba-demo"
   python3 deploy_token.py
   ```

5. 點擊 **Redeploy** 按鈕

6. 驗證成功
   ```bash
   curl https://web-production-d742.up.railway.app/api/token-status
   # 預期：status = "ok", source = "file"
   ```

完成後：✨ **自動化完成**，Token 每次過期自動刷新，無需再手動更新

---

## 工作規則（每個任務完成後必須執行）
- ✅ 完成內容：說明做了什麼
- ⚠️ 不確定之處：列出潛在問題
- 📊 數據來源：標明每筆數據來源（nba_api / 估算 / 其他）
- 👉 下一步建議：提供可直接複製的指令

如果遇到錯誤：不要只說發生錯誤，直接提供修正方案和對應指令

---

## 系統環境注意事項
- Python 3.14.3 (位於 C:\Users\shelton_yeh\AppData\Local\Python\pythoncore-3.14-64\python.exe)
- pip 需用 python -m pip 執行
- claude 完整路徑：C:\Users\Shelton\.local\bin\claude.exe
- PATH 已設定：C:\Users\Shelton\.local\bin

### 已安裝的 Python 套件
- Flask 3.1.3 — Web 框架
- requests 2.x — HTTP 客戶端
- requests-oauthlib 1.3.x — OAuth 認證
- yahoofantasy 0.x — Yahoo Fantasy API 官方庫（用於簡化 OAuth）

### Flask 啟動指令
```bash
# 在專案目錄執行
python3 -m flask run --port 5000

# 或使用簡化版（需設定 FLASK_APP 環境變數）
flask run --port 5000
```

瀏覽器訪問：http://localhost:5000

---

## API 端點狀態（2026-03-26）

### ✅ 正常運作的端點
| 端點 | 說明 | 數據來源 |
|------|------|--------|
| `GET /api/roster` | 我的 16 人陣容（季度統計） | players_data.json |
| `GET /api/matchup` | 本週對戰數據（含 lower_is_better 標示） | 假對手（模擬）|
| `GET /api/news` | 球員新聞 ticker | 硬編碼 mock 數據 |
| `GET /api/free-agents` | 自由球員推薦 | players_data.json 評分 |
| `GET /api/ai-recommendations` | AI 建議 | 簡單邏輯分析 |

### ⏳ 待優化的端點
| 端點 | 現狀 | 目標 |
|------|------|------|
| `GET /api/matchup` | 對手是隨機生成的假隊伍 | 改為真實 Yahoo 對手 |
| `/api/opponent/roster` | 不存在 | 新增，取得對手陣容 |

### 待新增的端點（Phase 2）
- `GET /api/league/standings` — 聯盟排名
- `GET /api/schedule/week/:week` — 特定周次對戰
- `GET /api/player/:player_id` — 單一球員詳細數據

---

## 測試指令

### 啟動伺服器
```bash
cd "C:\Vibe coding\fantasy-nba-demo"
python3 -m flask run --port 5000
```

### 測試 API
```bash
# 測試對戰端點（驗證 lower_is_better 欄位）
curl http://localhost:5000/api/matchup | python3 -m json.tool | head -40

# 測試陣容端點（驗證 fg_pct 欄位）
curl http://localhost:5000/api/roster | python3 -m json.tool | head -50
```

### 測試 OAuth
```bash
# 簡化版 OAuth 2.0 流程（需在瀏覽器手動授權）
python3 oauth2_login.py
```

---

## 關鍵檔案清單

### 前端
- `templates/index.html` — 主頁面（1011 行，已優化）

### 後端
- `app.py` — Flask 應用（9 個 API 端點）
- `data_loader.py` — 數據處理邏輯
- `yahoo_api.py` — Yahoo Fantasy API 客戶端（已編寫但未使用）
- `yahoo_config.py` — 認證配置

### OAuth 認證
- `oauth2_login.py` — 簡化版 OAuth 2.0（新增）
- `do_login.py` — 使用 yahoofantasy 庫（失敗）
- `oauth_authorize.py` — HTTPS 回調版（複雜）

### 數據
- `players_data.json` — 570 位 NBA 球員季度統計
- `my_roster.json` — 你的 16 人陣容定義
