# 🚀 Railway 環境變數設定指南

## 概況
將 Yahoo OAuth Token 設定為 Railway 環境變數（**推薦方式**），避免 Token 過期問題。

---

## 步驟 1️⃣ 打開 Railway Dashboard

訪問：**https://railway.app/dashboard**

---

## 步驟 2️⃣ 進入專案

點擊 **fantasy-nba-demo** 專案

---

## 步驟 3️⃣ 進入 Web Service

點擊左側 **web** Service

---

## 步驟 4️⃣ 打開環境變數設定

點擊 **Variables** Tab

---

## 步驟 5️⃣ 新增環境變數

### 5.1 新增 `YAHOO_ACCESS_TOKEN`
- **Key**: `YAHOO_ACCESS_TOKEN`
- **Value**:
```
lPkOcuKduA2geD9mgW4Z63As8Q1qGz1f88joGJEqj5H1zyacJxOqdVscrFyHMGsNZpTG.5S7Vvd0S4Q2ij16fXmm3SBbEaezCwgrOX.NW0NkFxgg3KfcGh.H4g7ijSNmgnZ9MV4aeVn43Pohv3kTD0psf6xYisVvn0HTuY02lvO31T1SZeIfa1X1U0RPVjdtLBGd4cHjHRQ2xnqgSj5.St2badfOJlkN50vhpTyLieUa1QjLMygnz3863uLYoJUWqtxXAaYGwomgL63uEEzHBuC3Cf5Ocz00EBZQX3YnK7HL5J5WKvTz0QxuoRriav945ugOt4TFZFYBeDnuez7OonQJNb3Rqb36ovVL7fqcR6fUPLLQo7nZ9Zg5xitMKZz33EpS2UX1MaeOrPAVwUan6IgAuHMvZW7G2LLtjIiEWU_BfrMYbvaiADzou0DyGkXhSput7jgZwYub.nUmFyy4ioNVnYZAH_WKB3MImRevalo566Dcj4p8uQAd9m5E7ff7j.OBgLJKzOzwaPRp5go9dWOstL7rCivwkhpCfVqN8eJa85hLLZ4MS5.gicv.XsSLk54gUhvVKVjSUHMGHUkyWotrIOXkl6AOlyMp4iT.QW3Mtgikspfb.g6y2DFMkUrQB0fo_Ls0sQS.qNQi95dvTUTG96HPQL7jHlKJM9NW3Ohv1Vki6B5g2YGahergWwIw7VwKGkkn0Z39c_YD68u8Pkqh4FrXyWV8WGwPTpl6HX42hzNul3M1WfMmC3lnE7996yT1XV68bGBWf2UR8lCNK9bSUhODbXLCTU2wZuNpCSbyvAwceaqW2uCYwFuPqqvFvg.xebzxMApvkGgUl9WvAiB_tvwYnwf.GM5oiLsbNB55WmnO2jAC_v353iQqPOuHW_BsbNzj5rQUarV8.CbPujt.zooKTz2J2BqRc2hd31c9.XIGz5OtRWpqDzj1f6zfJm9CrnzqQo0tEX0.qYb0ZA--
```

### 5.2 新增 `YAHOO_REFRESH_TOKEN`
- **Key**: `YAHOO_REFRESH_TOKEN`
- **Value**:
```
ACrExGl9kKScnLYTydlbO0mvZypb~001~eiHrfW_5NOp21s47C5hzCo_5mJsL648DUQ--
```

### 5.3 新增 `CURRENT_WEEK`
- **Key**: `CURRENT_WEEK`
- **Value**: `22`

---

## 步驟 6️⃣ 手動觸發部署

完成環境變數設定後，Railway 不會自動部署。你需要：

1. 點擊 **Deployments** Tab
2. 點擊右上角 **Redeploy** 按鈕
3. 等待 1-2 分鐘部署完成

---

## ✅ 驗證部署成功

部署完成後，執行此命令驗證：

```bash
curl https://web-production-d742.up.railway.app/api/token-status
```

**預期結果**（JSON 格式）：
```json
{
  "status": "ok",
  "source": "env_var",
  "created_at": 1774576971,
  "elapsed_minutes": X,
  "expires_in_hours": Y
}
```

---

## 🔄 測試 Yahoo API 連線

驗證應用連接到 Yahoo Fantasy API：

```bash
curl https://web-production-d742.up.railway.app/api/matchup
```

**預期結果**：
- 本週對手: **葉來葉好玩葉董好好玩**
- 對手統計資料正確顯示

---

## 💡 常見問題

### ❓ 為什麼環境變數設定後需要 Redeploy？
Railway 讀取環境變數時需要重啟應用程式。

### ❓ Token 會過期嗎？
不會！應用會自動 refresh token，並存儲在記憶體中。下次部署時會重新使用本地副本。

### ❓ 如果 Token 過期怎麼辦？
重複步驟 1-6，將新的 `YAHOO_ACCESS_TOKEN` 和 `YAHOO_REFRESH_TOKEN` 更新到 Railway。

---

## 📞 需要幫助？

如果部署失敗，請檢查：
- ✅ Railway CLI 已登入
- ✅ 環境變數值完全複製（無空格、無換行）
- ✅ 已點擊 Redeploy 按鈕
- ✅ 等待 1-2 分鐘部署完成

---

**最後更新**: 2026-03-27
**部署狀態**: ⚠️ 待 Railway Dashboard 環境變數設定
