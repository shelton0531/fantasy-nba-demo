# 任務 8 實現計畫：每日日期切換器 + 球員對手顯示 + 7/14/30 天數據切換

## 📋 Context

**需求背景（用戶提出）：**
1. 變成每日的切換器，在陣容頁面右上方顯示
2. 球員根據日期切換器顯示當日數據、球賽日期與對手
3. 按照當日顯示球員出賽狀況（GTD, Out, INJ, NA）
4. 球員數據按照 7/14/30 天平均值顯示，並提供額外切換器

**當前現狀：**
- 前端完全無日期/周次切換 UI（section-header 只有純文字「本週累計數據」）
- 後端 `/api/roster` 不接受任何時間參數，固定返回季度均值
- `players_data.json` 只有 season 和 recent（L15）兩個數據集，無 7/14/30 天分段
- 球員出賽狀態全部硬編碼為 "Active"，無真實數據
- 無每日賽程 API

---

## 🎯 設計決策

### 數據來源
- **每日賽程**：使用 `nba_api.ScoreboardV2(game_date='YYYY-MM-DD')` 取得 NBA 每日比賽資訊
- **7/14/30 天數據**：使用 `LeagueDashPlayerStats(last_n_games=N, season='2025-26')` 取得分段平均值（複製現有 `_fetch_recent_stats()` 的模式）
- **球員出賽狀態**：從每日賽程判斷「是否有比賽」；傷病狀態暫從 `my_roster.json` 的 status 欄位讀取（目前全 Active，可手動維護）

### 快取策略
- **每日賽程**：按日期為鍵（`daily_schedule_YYYY-MM-DD.json`），過去日期永久快取，今天 30 分鐘 TTL，未來日期 1 小時 TTL
- **7/14/30 天數據**：3 小時 TTL（與現有 season/recent 一致）

---

## 🚀 實現方案（5 個子任務，順序重要）

### 子任務 8-A：後端 period 參數擴展（2-3 小時）
**複雜度：低** | **依賴：無** | **先決條件：無**

**目標**：支援 `GET /api/roster?period=7d|14d|30d|season|recent`

**修改文件：**

1. **`data/nba_live.py`（新增函數）**
   - 複製 `_fetch_recent_stats()` 邏輯，創建 `_fetch_n_game_stats(n)` 函數
   - 參數 `n` = 7/14/30
   - 快取路徑 = `cache/last{n}_stats.json`
   - 調用：`LeagueDashPlayerStats(season='2025-26', per_mode_detailed='PerGame', last_n_games=n)`

2. **`data_loader.py`（修改現有函數）**
   - `get_roster_with_stats(period)` 擴展：
     ```python
     if period in ['7d', '14d', '30d']:
         from data.nba_live import _fetch_n_game_stats
         int_n = int(period[0:2])  # '7d' → 7
         players_list = _fetch_n_game_stats(int_n)
     ```

3. **`app.py`（修改現有端點）**
   - `@app.route("/api/roster")` 改為：
     ```python
     period = request.args.get('period', 'season')
     roster_data = get_roster_with_stats(period)
     # ... 返回格式不變，只是數據不同
     ```

**測試**：
```bash
curl "http://localhost:5000/api/roster?period=7d" | python3 -m json.tool | head -30
```

---

### 子任務 8-B：前端 period 切換器（1-2 小時）
**複雜度：低** | **依賴：8-A** | **先決條件：8-A 完成**

**目標**：在陣容頁面 section-header 新增 4 個 period 按鈕（整季/7天/14天/30天）

**修改文件：**

1. **`templates/index.html`（新增 HTML + CSS + JS）**

   a. **HTML（插入 section-header，行 559-563）**
   ```html
   <div class="section-header">
     <span class="section-title">我的陣容</span>
     <div class="section-line"></div>
     <!-- 新增：period tabs -->
     <div class="period-tabs" id="period-tabs">
       <button class="period-btn active" data-period="season">整季</button>
       <button class="period-btn" data-period="7d">7天</button>
       <button class="period-btn" data-period="14d">14天</button>
       <button class="period-btn" data-period="30d">30天</button>
     </div>
   </div>
   ```

   b. **CSS（新增到 style 區塊）**
   ```css
   .period-tabs {
     display: flex;
     gap: 4px;
   }
   .period-btn {
     padding: 4px 10px;
     border-radius: 20px;
     border: 1px solid var(--border);
     background: transparent;
     color: var(--text-muted);
     font-size: 11px;
     cursor: pointer;
     transition: all 0.15s;
   }
   .period-btn.active {
     background: var(--primary);
     border-color: var(--primary);
     color: #fff;
     font-weight: 600;
   }
   ```

   c. **JS（新增到 script 區塊，window.onload 中或 init() 中）**
   ```javascript
   let currentPeriod = 'season';

   document.querySelectorAll('.period-btn').forEach(btn => {
     btn.onclick = () => {
       currentPeriod = btn.dataset.period;
       document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
       btn.classList.add('active');
       loadRoster();  // 使用新 period 重新載入
     };
   });
   ```

2. **修改 `loadRoster()` 函數（現有函數）**
   ```javascript
   // 原本：fetch(`${API}/api/roster`)
   // 改為：
   fetch(`${API}/api/roster?period=${currentPeriod}`)
   ```

**測試**：
- 點擊「7天」按鈕，驗證陣容數據更新為 7 天平均值
- 切換回「整季」，驗證恢復為季度平均值

---

### 子任務 8-C：後端每日賽程 API（3-4 小時）
**複雜度：中** | **依賴：無** | **先決條件：無**

**目標**：實現 2 個新端點：`/api/schedule/daily` 和 `/api/roster/daily`

**修改文件：**

1. **`data/nba_live.py`（新增函數）**
   ```python
   def get_daily_schedule(date_str):
       """
       date_str: 'YYYY-MM-DD' (e.g., '2026-03-28')
       Returns: {
           'date': '2026-03-28',
           'games': [
               {
                   'game_id': '...',
                   'home_team': 'LAL',
                   'away_team': 'GSW',
                   'game_time': '19:30 ET',
                   'status': 'Scheduled'  # or 'Final', 'In Progress'
               }
           ],
           'my_players_playing': [
               {
                   'player_name': 'LeBron James',
                   'nba_team': 'LAL',
                   'opponent': 'GSW',
                   'home_away': 'home'  # or 'away'
               }
           ]
       }
       """
       cache_file = os.path.join(CACHE_DIR, f'daily_schedule_{date_str}.json')

       # TTL 邏輯
       today = datetime.today().strftime('%Y-%m-%d')
       if date_str < today:
           # 過去日期：永久快取
           ttl = float('inf')
       elif date_str == today:
           # 今天：30 分鐘
           ttl = 30 * 60
       else:
           # 未來日期：1 小時
           ttl = 60 * 60

       if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < ttl:
           with open(cache_file, 'r') as f:
               return json.load(f)

       # 取得每日賽程
       try:
           endpoint = ScoreboardV2(game_date=date_str)  # 需 import
           df = endpoint.get_data_frames()[0]  # GameHeader table
           games = []
           for _, row in df.iterrows():
               games.append({
                   'game_id': row['GAME_ID'],
                   'home_team': row['HOME_TEAM_ABBREVIATION'],  # 確認字段名
                   'away_team': row['VISITOR_TEAM_ABBREVIATION'],
                   'home_team_full': row.get('HOME_TEAM', ''),
                   'away_team_full': row.get('VISITOR_TEAM', ''),
                   'game_time': row.get('GAME_TIME_ET', 'TBD'),
                   'status': row.get('GAME_STATUS', 'Scheduled')
               })
       except Exception as e:
           print(f"[nba_live] 取得賽程失敗: {e}")
           return {'date': date_str, 'games': [], 'error': str(e)}

       # 對照 my_roster.json，找出我的球員有比賽的
       my_players_playing = []
       try:
           from data_loader import load_my_roster
           roster = load_my_roster()
           my_teams_in_games = {g['home_team']: 'home' for g in games}
           my_teams_in_games.update({g['away_team']: 'away' for g in games})

           for roster_player in roster['roster']:
               team = roster_player['team']
               if team in my_teams_in_games:
                   home_away = my_teams_in_games[team]
                   opponent = next(
                       (g['away_team'] if g['home_team'] == team else g['home_team']
                        for g in games if team in (g['home_team'], g['away_team'])),
                       None
                   )
                   my_players_playing.append({
                       'player_name': roster_player['name'],
                       'nba_team': team,
                       'opponent': opponent,
                       'home_away': home_away
                   })
       except Exception as e:
           print(f"[nba_live] 對照陣容失敗: {e}")

       result = {
           'date': date_str,
           'games': games,
           'my_players_playing': my_players_playing
       }

       # 快取
       os.makedirs(CACHE_DIR, exist_ok=True)
       with open(cache_file, 'w') as f:
           json.dump(result, f)

       return result
   ```

2. **`data_loader.py`（新增函數）**
   ```python
   def get_roster_with_daily_context(date_str, period='season'):
       """
       結合每日賽程 + 陣容統計
       返回陣容數據，並添加當日對手、出賽狀態等欄位
       """
       from data.nba_live import get_daily_schedule

       # 獲得陣容 + 統計數據
       roster_data = get_roster_with_stats(period)
       schedule = get_daily_schedule(date_str)

       # 建立 team → 對手對照表
       team_opponent_map = {}
       for game in schedule.get('games', []):
           team_opponent_map[game['home_team']] = {
               'opponent': game['away_team'],
               'home_away': 'home'
           }
           team_opponent_map[game['away_team']] = {
               'opponent': game['home_team'],
               'home_away': 'away'
           }

       # 填充每個球員的對手信息
       for player in roster_data.get('players', []):
           team = player['team']
           if team in team_opponent_map:
               opponent_info = team_opponent_map[team]
               player['has_game_today'] = True
               player['opponent'] = opponent_info['opponent']
               player['home_away'] = opponent_info['home_away']
           else:
               player['has_game_today'] = False
               player['opponent'] = None
               player['home_away'] = None

       return roster_data['players']  # 前端期望直接是 players 陣列
   ```

3. **`app.py`（新增 2 個端點）**
   ```python
   from datetime import datetime

   @app.route("/api/schedule/daily")
   def schedule_daily():
       """Get daily NBA schedule"""
       date = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
       from data.nba_live import get_daily_schedule
       return jsonify(get_daily_schedule(date))

   @app.route("/api/roster/daily")
   def roster_daily():
       """Get roster with daily matchup context"""
       date = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
       period = request.args.get('period', 'season')
       from data_loader import get_roster_with_daily_context
       return jsonify(get_roster_with_daily_context(date, period))
   ```

**測試**：
```bash
curl "http://localhost:5000/api/schedule/daily?date=2026-03-28" | python3 -m json.tool
curl "http://localhost:5000/api/roster/daily?date=2026-03-28&period=season" | python3 -m json.tool | head -50
```

**風險緩解**：
- ScoreboardV2 可能因 API 限流超時：所有 nba_api 呼叫包含 try/except，失敗時返回 `{"games": []}`
- 球員 team 縮寫不對齊（如 LAL vs Los Angeles Lakers）：建立 TEAM_ABBR_MAP 統一轉換

---

### 子任務 8-D：前端日期切換器 + 球員對手顯示（2-3 小時）
**複雜度：中** | **依賴：8-C** | **先決條件：8-C 完成**

**目標**：
1. 陣容頁面右上方新增日期導航（左/右箭頭 + 日期顯示）
2. 球員卡片新增「vs 對手」badge
3. 支援無比賽日期的優雅處理

**修改文件：**

1. **`templates/index.html`（修改 section-header，新增 HTML + CSS + JS）**

   a. **HTML（替換陣容 section-header）**
   ```html
   <div class="section-header">
     <span class="section-title">我的陣容</span>
     <div class="section-line"></div>
     <!-- period tabs（來自 8-B） -->
     <div class="period-tabs" id="period-tabs">
       <!-- ... -->
     </div>
     <!-- 新增：日期導航 -->
     <div class="date-nav" id="date-nav">
       <button class="date-btn" id="date-prev">&#8249;</button>
       <span class="date-display" id="date-display">今日</span>
       <button class="date-btn" id="date-next" disabled>&#8250;</button>
     </div>
   </div>
   ```

   b. **CSS（新增）**
   ```css
   .date-nav {
     display: flex;
     align-items: center;
     gap: 6px;
   }
   .date-btn {
     width: 26px;
     height: 26px;
     background: var(--surface);
     border: 1px solid var(--border);
     border-radius: 6px;
     color: var(--text);
     cursor: pointer;
     font-size: 16px;
     display: flex;
     align-items: center;
     justify-content: center;
   }
   .date-btn:disabled {
     opacity: 0.3;
     cursor: default;
   }
   .date-display {
     font-size: 12px;
     color: var(--text-muted);
     min-width: 80px;
     text-align: center;
   }

   .game-badge {
     font-size: 10px;
     color: var(--blue);
     margin-top: 2px;
     font-weight: 600;
   }
   .game-badge.no-game {
     color: var(--text-muted);
     font-weight: 400;
   }
   ```

   c. **JS（新增日期切換邏輯）**
   ```javascript
   let currentDate = new Date();
   const today = new Date();

   function formatDateDisplay(d) {
     if (d.toDateString() === today.toDateString()) return '今日';
     const months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
     const days = ['日','一','二','三','四','五','六'];
     return `${months[d.getMonth()+1]} ${d.getDate()}（${days[d.getDay()]}）`;
   }

   document.getElementById('date-prev').onclick = () => {
     currentDate = new Date(currentDate);
     currentDate.setDate(currentDate.getDate() - 1);
     updateDateNav();
     loadRoster();  // 重新載入，使用新 date + currentPeriod
   };

   document.getElementById('date-next').onclick = () => {
     if (currentDate >= today) return;
     currentDate = new Date(currentDate);
     currentDate.setDate(currentDate.getDate() + 1);
     updateDateNav();
     loadRoster();
   };

   function updateDateNav() {
     document.getElementById('date-display').textContent = formatDateDisplay(currentDate);
     document.getElementById('date-next').disabled = (currentDate >= today);
   }

   updateDateNav();  // 初始化
   ```

   d. **修改 `loadRoster()` 函數**
   ```javascript
   async function loadRoster() {
     const dateStr = currentDate.toISOString().split('T')[0];  // 'YYYY-MM-DD'
     const res = await fetch(
       `${API}/api/roster/daily?date=${dateStr}&period=${currentPeriod}`
     );
     const players = await res.json();
     // ... 原有的 loadRoster 邏輯，但使用新的 players 結構
   }
   ```

   e. **更新球員卡片渲染（增加對手 badge）**

   在 `loadRoster()` 的球員卡片生成邏輯中（原 ~第 754-803 行），在 `.player-meta` 下方新增：
   ```javascript
   const gameInfo = p.has_game_today
     ? `<div class="game-badge">vs ${p.opponent} ${p.home_away === 'home' ? '（主）' : '（客）'}</div>`
     : `<div class="game-badge no-game">今日休息</div>`;

   // 修改球員卡片 HTML，在 .player-meta 之後插入 gameInfo
   // 原結構大致是：
   // <div class="player-meta">${p.team} · ${p.position} · ${a.min}分鐘</div>
   // 改為：
   // <div class="player-meta">${p.team} · ${p.position} · ${a.min}分鐘</div>
   // ${gameInfo}
   ```

   f. **擴展出賽狀態 pill**

   原 loadRoster 函數（~第 741-748 行）只支援 Out/Questionable，改為：
   ```javascript
   const statusPill = {
     'Out': `<span class="status-pill status-out">OUT</span>`,
     'Questionable': `<span class="status-pill status-questionable">GTD</span>`,
     'Injured': `<span class="status-pill status-out">INJ</span>`,
     'NA': `<span class="status-pill status-na">N/A</span>`,
   }[p.status] || '';

   // 新增 CSS for status-na
   .status-na {
     background: rgba(139,148,158,.2);
     color: var(--text-muted);
   }
   ```

**測試**：
- 點擊左箭頭，日期應往前推 1 天
- 選擇有比賽的日期（如今天），每個球員應顯示「vs 對手」
- 選擇無比賽的日期（週末或休賽期），應顯示「今日休息」
- 切換 period，對手信息應保持，但統計數據更新

---

### 子任務 8-E：修復 my_roster.json 的 position 欄位（0.5 小時）
**複雜度：低** | **依賴：無** | **先決條件：無**

**目標**：補充 `my_roster.json` 中所有球員的真實 position（目前全是 `"—"`）

**修改文件：**

1. **`my_roster.json`（手動修正 position）**
   ```json
   {
     "id": 1,
     "name": "Kennedy Chandler",
     "api_name": "Kennedy Chandler",
     "team": "UTA",
     "position": "PG",        // 改為真實位置
     "status": "Active",
     "notes": "..."
   },
   // ... 其他 15 名球員，每位補充 position
   ```

   **位置參考（根據 NBA 官方）：**
   - Kennedy Chandler: PG
   - Tre Jones: PG/SG
   - Deni Avdija: SF/PF
   - Gui Santos: SF
   - LeBron James: SF/PF
   - P.J. Washington: PF
   - Deandre Ayton: C
   - Amen Thompson: SG/SF
   - Ace Bailey: SF
   - Paul George: SF/SG
   - Bobby Portis: PF/C
   - Josh Hart: SF
   - DeMar DeRozan: SG/SF
   - Shaedon Sharpe: SG/SF
   - Isaiah Collier: PG
   - Russell Westbrook: PG

2. **`app.py` 修改（讀取真實 position）**

   原 `/api/roster` 端點（行 74）：
   ```python
   'position': '—',  # 硬編碼
   ```

   改為從來源讀取（需修改 `data_loader.py` 返回 position）：

   在 `data_loader.py` 的 `get_roster_with_stats()` 函數中（~第 67 行），添加：
   ```python
   'position': roster_player['position'],  # 從 my_roster.json 讀取
   ```

   然後 `app.py` 中改為：
   ```python
   'position': p['position'],  # 從 data_loader 取得
   ```

**測試**：
```bash
curl http://localhost:5000/api/roster | python3 -m json.tool | grep -A1 position
```

---

## 📊 子任務執行順序

建議按以下順序進行（考慮依賴關係）：

```
🟢 8-A（後端 period 擴展）— 2-3 小時
   ↓ 依賴
🟡 8-B（前端 period tabs）— 1-2 小時
   ↓ 獨立並行
🟠 8-C（後端每日賽程） + 8-E（position 修復）— 3-4 + 0.5 小時
   ↓ 依賴
🔴 8-D（前端日期切換） — 2-3 小時

總估時：9-13 小時（可以平行執行 8-C + 8-E）
```

---

## ✅ 驗證清單

完成後，逐項驗證：

- [ ] Task 7（Railway Token）已完成，應用在線
- [ ] `GET /api/roster?period=7d` 返回 7 天平均值
- [ ] `GET /api/roster?period=14d` 返回 14 天平均值
- [ ] `GET /api/roster?period=30d` 返回 30 天平均值
- [ ] 前端「7天/14天/30天」按鈕可切換數據
- [ ] `GET /api/schedule/daily?date=2026-03-28` 返回當日賽程
- [ ] `GET /api/roster/daily?date=2026-03-28` 返回陣容 + 對手信息
- [ ] 前端日期導航箭頭可切換日期
- [ ] 球員卡片顯示「vs 對手」或「今日休息」
- [ ] 多個 period + date 組合切換正常
- [ ] 無比賽日期（週末或休賽期）顯示「今日休息」，不崩潰
- [ ] 手機 RWD 佈局正常（section-header 兩組 UI 不溢出）

---

## 🔧 Critical Files

- `G:\Vibe coding\fantasy-nba-demo\data\nba_live.py` — 新增函數
- `G:\Vibe coding\fantasy-nba-demo\data_loader.py` — 擴展函數
- `G:\Vibe coding\fantasy-nba-demo\app.py` — 新增端點
- `G:\Vibe coding\fantasy-nba-demo\templates\index.html` — UI + JS
- `G:\Vibe coding\fantasy-nba-demo\my_roster.json` — 補充 position

---

## ⚠️ 風險與緩解

| 風險 | 可能性 | 症狀 | 緩解方案 |
|------|--------|------|---------|
| `ScoreboardV2` 超時 | 高 | `/api/schedule/daily` 10-45 秒無回應 | 所有 nba_api 呼叫 20 秒 timeout + try/except，失敗返回空 games 列表 |
| 球隊縮寫不對齊 | 中 | 球員卡片無法比對對手 | 建立 TEAM_ABBR_MAP（30 支球隊全名 ↔ 縮寫），統一轉換 |
| 7/14/30 天數據首次取得慢 | 中 | 首次請求 10-30 秒 | 快取命中後恢復正常；可選擇預熱但增加啟動時間 |
| RWD 佈局破裂 | 中 | 行動裝置上 UI 溢出或換行 | 將 section-header 改為兩行（手機），period + date 分行 |
| 球員 status 更新遲滯 | 低 | 傷病信息不即時 | 暫時接受手動維護；未來可接入 Yahoo 傷病 API |
