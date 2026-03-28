# 你的 Fantasy NBA 陣容

## 快速查看

```bash
# 查看近 15 場平均
python3 roster_report.py recent

# 查看整季平均
python3 roster_report.py season
```

---

## 陣容概況 (2025-26 季度)

| 指標 | 數值 |
|------|------|
| **陣容規模** | 13 人 |
| **活躍球員** | 12 人（Haliburton 整季傷缺） |
| **Fantasy 總積分** | 442.6 pts (整季平均) / 419.6 pts (近15場) |
| **人均 Fantasy** | 36.9 pts (整季) / 38.1 pts (近15場) |
| **聯盟排名前 5** | Jokic #1, Jaylen #10, Sengun #14, Paolo #21, Barnes #19 |

---

## 陣容強項

- **得分火力** — Jokic (27.9), Booker (25.5), Jaylen (28.5), Bam (20.3)
- **籃板能力** — Jokic (12.7), Mobley (8.9), Bam (9.8), Sengun (9.0)
- **助攻中樞** — Jokic (10.7), Sengun (6.2), Booker (5.9), Barnes (5.4)
- **投籃命中率** — Sengun (51.6% FG), Mobley (53.9% FG)
- **罰球命中率** — Bane (92.4%), Jokic (82.9%)

---

## 陣容弱項

| 球員 | 問題 | 建議 |
|------|------|------|
| **Dort** | 場均 8.4 pts (聯盟 #265) | 考慮替換高得分球員 |
| **Clarkson** | 場均 9.0 pts (聯盟 #344) | 考慮替換高助攻球員 |
| **McBride** | 出賽少 (35 games) | 監測出賽情況 |
| **Haliburton** | 整季傷缺報銷 | 已列為 Out，建議替換 |

---

## 檔案說明

| 檔案 | 內容 |
|------|------|
| `players_data.json` | 2025-26 全 570 位球員 (整季 + 近15場) |
| `my_roster.json` | 你的 13 人陣容配置 |
| `roster_report.py` | 報告生成工具 |
| `README_ROSTER.md` | 本檔 |

---

## 下一步

### 1. 更新陣容
編輯 `my_roster.json`，修改 `roster` 陣列，替換球員名字即可。

### 2. 替換低產球員
建議替換清單：
- Dort → 尋找高得分自由球員
- Clarkson → 尋找高助攻自由球員
- Haliburton → 緊急替換（整季報銷）

### 3. 查詢自由市場
```bash
# 查看自由市場推薦 (在 web app 上)
http://localhost:5000 → 自由市場分頁
```

---

## 數據更新頻率

- 整季數據：每 3 小時更新一次
- 近期數據 (L15)：每 3 小時更新一次
- 陣容數據：手動更新 (編輯 `my_roster.json`)

上次數據更新：2026-03-26 01:35:13
