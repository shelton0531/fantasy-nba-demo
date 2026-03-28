# 🤖 自動更新 Yahoo Token — 完整方案

## 問題
目前 Railway 上 token 過期需要手動更新環境變數，不夠自動化。

## 解決方案

### 推薦方案 1️⃣：Railway Persistent Volume（⭐ 最簡單）

使用 Railway Volume 存儲 token 檔案，應用自動 refresh 寫入 Volume，下次部署無需手動更新。

#### 優點
- ✅ 只需 1 次手動設定
- ✅ 應用自動刷新 token 到 `/data/yahoo_token.json`
- ✅ 部署不覆蓋 token（數據持久化）
- ✅ 完全自動，無需任何定時任務

#### 實施步驟

##### Step 1: 在 Railway Dashboard 建立 Volume

1. 打開 https://railway.app/dashboard
2. 進入 **fantasy-nba-demo** 專案
3. 點擊 **web** service
4. 點擊 **Volumes** Tab
5. 點擊 **Create Volume** 按鈕
6. 設定 **Mount Path**: `/data`
7. 點擊 **Create** 確認

##### Step 2: 更新環境變數

在 **Variables** Tab 中：

**保留並更新：**
```
TOKEN_DIR = /data
CURRENT_WEEK = 22
```

**刪除（不再需要環境變數）：**
```
YAHOO_ACCESS_TOKEN    ❌ 刪除
YAHOO_REFRESH_TOKEN   ❌ 刪除
```

##### Step 3: 上傳初始 Token 檔案到 Volume

執行以下指令：

```bash
cd "D:\Vibe coding\fantasy-nba-demo"

# 方法 A：直接上傳（推薦）
cat yahoo_token.json | base64 | railway run bash -c "base64 -d > /data/yahoo_token.json"

# 或方法 B：使用 SSH
railway ssh
# 在遠端執行：
# mkdir -p /data
# cat > /data/yahoo_token.json << 'EOF'
# (貼上 yahoo_token.json 內容)
# EOF
```

##### Step 4: Redeploy 應用

1. 點擊 **Deployments** Tab
2. 點擊 **Redeploy** 按鈕
3. 等待 1-2 分鐘部署完成

##### Step 5: 驗證成功

```bash
# 檢查 token 狀態
curl https://web-production-d742.up.railway.app/api/token-status

# 預期結果：status = "ok"，source = "file"
```

預期輸出：
```json
{
  "status": "ok",
  "source": "file",
  "created_at": 1774599572,
  "elapsed_minutes": X,
  "expires_in_minutes": 59
}
```

##### Step 6: 完成！從此自動

- 應用會每次調用 Yahoo API 時自動檢查 token 過期
- 過期時自動刷新，並寫入 `/data/yahoo_token.json`
- 下次部署應用，token 仍然存在（不覆蓋）
- **無需手動更新**

---

### 備選方案 2️⃣：使用 PostgreSQL（進階）

如果想要更安全的存儲方式，使用 Railway 免費 PostgreSQL：

**優點：**
- 更安全（加密存儲）
- 支持版本控制（歷史記錄）
- 支持多個應用共享

**實施：**
1. Railway Dashboard → **Create** → 搜索 **PostgreSQL**
2. 添加到專案
3. 修改 `yahoo_config.py` 讀寫數據庫而非檔案
4. 設定 `DATABASE_URL` 環境變數

---

### 備選方案 3️⃣：定時刷新 API（簡單 webhook）

如果 Volume 方案不行，可以外部定時呼叫刷新端點。

**做法：**
1. 在 `app.py` 新增 `/api/refresh-token` 端點
2. 使用 IFTTT / Zapier 每小時呼叫一次
3. 或使用 GitHub Actions 定時刷新

---

## 建議流程

### 立即（5 分鐘）
✅ 實施方案 1 —— Railway Volume

### 完成後（永久）
- ✨ Token 自動刷新，無需操作
- 📊 驗證應用連線狀態正常

---

## 常見問題

### Q: Volume 建立後，token 會立即自動刷新嗎？
A: 不會。首次部署後，應用會在第一次呼叫 Yahoo API 時檢查 token 過期狀態，然後自動刷新。

### Q: 如何確認 token 已自動刷新？
A:
```bash
curl https://web-production-d742.up.railway.app/api/token-status | grep source
# 應該看到 "source": "file"
```

### Q: 多久會自動刷新一次？
A: 不是定時刷新，而是按需刷新。每次調用 Yahoo API 時，如果 token 過期會自動刷新。

### Q: 能否查看 Volume 中的檔案？
A:
```bash
railway run ls -lh /data/
railway run cat /data/yahoo_token.json
```

---

## 總結

| 方案 | 自動程度 | 複雜度 | 建議 |
|------|--------|------|------|
| Volume（方案 1） | ⭐⭐⭐⭐⭐ 完全自動 | 簡單 | ✅ 推薦 |
| PostgreSQL（方案 2） | ⭐⭐⭐⭐⭐ 完全自動 | 中等 | 進階用戶 |
| Webhook（方案 3） | ⭐⭐⭐ 半自動 | 中等 | 備選 |

---

**最後更新：** 2026-03-27
**建議：** 立即實施方案 1，5 分鐘完成，永久解決問題
