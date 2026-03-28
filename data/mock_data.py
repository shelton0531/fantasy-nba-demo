"""
mock_data.py
Bridge layer:
  - Roster & player stats        → nba_live.py (real NBA API)
  - Free agent suggestions       → nba_live.py (real stats, mock ownership)
  - Opponent / News / AI recs    → mock (until Yahoo API)
"""

from .nba_live import build_roster, _fetch_season_stats, _fetch_recent_stats, _find_player, _row_to_avg

# ── Opponent weekly totals (mock until Yahoo API) ──────────────────────────
OPPONENT_ROSTER_WEEKLY = {
    "name": "Thunder Hawks",
    "pts": 682, "reb": 287, "ast": 198,
    "stl": 42,  "blk": 29,  "threes": 76,
    "fg_pct": 47.8, "ft_pct": 79.3, "to": 89,
}

# ── Injury & trade news (mock; future: Yahoo + Twitter) ────────────────────
INJURY_NEWS = [
    {"type": "injury", "player": "Paolo Banchero",    "team": "ORL", "message": "左膝輕微腫脹，明日出賽列 Questionable",         "time": "2小時前",  "severity": "warning"},
    {"type": "out",    "player": "Jordan Clarkson",   "team": "UTA", "message": "右腳踝扭傷確認缺席，預計1週後復出",               "time": "4小時前",  "severity": "danger"},
    {"type": "return", "player": "Tyrese Haliburton", "team": "IND", "message": "從傷病名單移除，今晚確認出賽",                    "time": "6小時前",  "severity": "success"},
    {"type": "trade",  "player": "Cam Thomas",        "team": "BKN", "message": "交易傳聞：可能被交易至 Lakers，關注後續消息",      "time": "8小時前",  "severity": "info"},
    {"type": "injury", "player": "Karl-Anthony Towns","team": "NYK", "message": "膝蓋不適，本週練習受限",                          "time": "10小時前", "severity": "warning"},
]

# ── Free agent recommendations (mock; future: Yahoo FA + nba_api) ──────────
FREE_AGENTS = [
    {
        "id": "fa1", "name": "Cam Thomas", "team": "BKN", "position": "SG",
        "ownership": 45.2, "add_trend": "+12%",
        "avg_7d": {"pts": 28.4, "reb": 3.2, "ast": 3.8, "stl": 1.2, "blk": 0.4, "threes": 2.8, "fg_pct": 48.3, "ft_pct": 91.2, "to": 2.6},
        "recommendation": "強烈推薦",
        "reason": "近7日場均28.4分爆發，FT%達91.2%補強你隊FT短板，本週仍有4場出賽",
        "match_score": 94,
    },
    {
        "id": "fa2", "name": "Zach LaVine", "team": "SAC", "position": "SG/SF",
        "ownership": 38.7, "add_trend": "+8%",
        "avg_7d": {"pts": 22.1, "reb": 4.8, "ast": 4.2, "stl": 1.0, "blk": 0.3, "threes": 3.1, "fg_pct": 46.5, "ft_pct": 85.3, "to": 2.2},
        "recommendation": "推薦",
        "reason": "3PM近7日場均3.1顆，可填補你隊三分火力，且本週4場出賽機會多",
        "match_score": 81,
    },
    {
        "id": "fa3", "name": "Dereck Lively II", "team": "DAL", "position": "C",
        "ownership": 52.1, "add_trend": "+5%",
        "avg_7d": {"pts": 14.6, "reb": 11.2, "ast": 1.4, "stl": 0.8, "blk": 2.4, "threes": 0.0, "fg_pct": 68.2, "ft_pct": 62.3, "to": 1.2},
        "recommendation": "考慮",
        "reason": "BLK場均2.4 + FG%高達68.2%，適合替換受傷的 Clarkson 補充內線",
        "match_score": 71,
    },
    {
        "id": "fa4", "name": "Immanuel Quickley", "team": "TOR", "position": "PG",
        "ownership": 29.3, "add_trend": "+18%",
        "avg_7d": {"pts": 19.3, "reb": 4.1, "ast": 7.8, "stl": 1.4, "blk": 0.2, "threes": 2.6, "fg_pct": 44.1, "ft_pct": 87.6, "to": 2.8},
        "recommendation": "推薦",
        "reason": "AST場均7.8近期大爆發，add率本週上升18%，CP值極高的隱藏寶石",
        "match_score": 78,
    },
]


# ── Public API ──────────────────────────────────────────────────────────────

def get_my_roster():
    return build_roster()


def get_opponent_roster():
    return OPPONENT_ROSTER_WEEKLY


def get_weekly_matchup():
    roster = build_roster()

    # Weekly totals = avg × games_played_this_week
    def week_total(roster, key):
        return round(sum(p["avg"].get(key, 0) * p["games_played"] for p in roster), 1)

    def week_pct(roster, key):
        # Weighted average by games played
        vals = [(p["avg"].get(key, 0), p["games_played"]) for p in roster if p["games_played"] > 0]
        total_w = sum(w for _, w in vals)
        return round(sum(v * w for v, w in vals) / total_w, 1) if total_w else 0

    my = {
        "pts":    week_total(roster, "pts"),
        "reb":    week_total(roster, "reb"),
        "ast":    week_total(roster, "ast"),
        "stl":    week_total(roster, "stl"),
        "blk":    week_total(roster, "blk"),
        "threes": week_total(roster, "threes"),
        "fg_pct": week_pct(roster, "fg_pct"),
        "ft_pct": week_pct(roster, "ft_pct"),
        "to":     week_total(roster, "to"),
    }

    opp = OPPONENT_ROSTER_WEEKLY
    categories = [
        {"key": "pts",    "label": "得分",  "my": my["pts"],    "opp": opp["pts"],    "higher_wins": True},
        {"key": "reb",    "label": "籃板",  "my": my["reb"],    "opp": opp["reb"],    "higher_wins": True},
        {"key": "ast",    "label": "助攻",  "my": my["ast"],    "opp": opp["ast"],    "higher_wins": True},
        {"key": "stl",    "label": "抄截",  "my": my["stl"],    "opp": opp["stl"],    "higher_wins": True},
        {"key": "blk",    "label": "阻攻",  "my": my["blk"],    "opp": opp["blk"],    "higher_wins": True},
        {"key": "threes", "label": "三分",  "my": my["threes"], "opp": opp["threes"], "higher_wins": True},
        {"key": "fg_pct", "label": "FG%",   "my": my["fg_pct"], "opp": opp["fg_pct"], "higher_wins": True},
        {"key": "ft_pct", "label": "FT%",   "my": my["ft_pct"], "opp": opp["ft_pct"], "higher_wins": True},
        {"key": "to",     "label": "失誤",  "my": my["to"],     "opp": opp["to"],     "higher_wins": False},
    ]

    for cat in categories:
        my_val  = float(cat["my"])
        opp_val = float(cat["opp"])
        diff    = round(my_val - opp_val, 1)
        if cat["higher_wins"]:
            cat["status"] = "winning" if diff > 0 else ("losing" if diff < 0 else "tied")
            cat["diff"]   = f"+{diff}" if diff > 0 else str(diff)
        else:
            cat["status"] = "winning" if diff < 0 else ("losing" if diff > 0 else "tied")
            cat["diff"]   = f"+{abs(diff)}" if diff < 0 else f"-{abs(diff)}"

    wins   = sum(1 for c in categories if c["status"] == "winning")
    losses = sum(1 for c in categories if c["status"] == "losing")
    ties   = sum(1 for c in categories if c["status"] == "tied")

    return {
        "my_team":  "你的球隊",
        "opponent": opp["name"],
        "record":   f"{wins}-{losses}-{ties}",
        "wins": wins, "losses": losses, "ties": ties,
        "categories": categories,
        "my_totals":  my,
    }


def get_free_agents():
    """
    Real free agent recommendations: top fantasy performers
    not in my roster, ranked by recent fantasy_pts.
    Ownership % is mock until Yahoo API is connected.
    """
    from .nba_live import MY_ROSTER_CONFIG
    roster_names = {cfg["name"].lower() for cfg in MY_ROSTER_CONFIG}

    recent = _fetch_recent_stats()
    season = _fetch_season_stats()

    # Build candidate list: players not on my roster, with meaningful GP
    candidates = []
    for r_row in recent:
        name = r_row["PLAYER_NAME"]
        if name.lower() in roster_names:
            continue
        if int(r_row.get("GP", 0)) < 5:
            continue

        r_avg = _row_to_avg(r_row)
        s_row = _find_player(season, name)
        s_avg = _row_to_avg(s_row)

        if not r_avg or r_avg["fantasy_pts"] < 20:
            continue

        # Mock ownership (in future: from Yahoo FA endpoint)
        import random
        random.seed(hash(name))
        ownership = round(random.uniform(5, 65), 1)
        add_trend_val = round(random.uniform(-5, 20), 1)
        add_trend = f"+{add_trend_val}%" if add_trend_val >= 0 else f"{add_trend_val}%"

        # Match score: weighted by fantasy_pts rank + FT% gap (common weakness)
        rank = r_avg["ranks"]["fantasy_pts"]
        match_score = max(0, min(99, round(100 - (rank / 6))))

        # Build reason from real data
        reasons = []
        if r_avg["fantasy_pts"] >= 50:
            reasons.append(f"近15場 Fantasy 積分高達 {r_avg['fantasy_pts']} (聯盟 #{rank})")
        if r_avg["pts"] >= 25:
            reasons.append(f"場均 {r_avg['pts']} 分爆發")
        if r_avg["ast"] >= 7:
            reasons.append(f"助攻場均 {r_avg['ast']} 高產")
        if r_avg["threes"] >= 3:
            reasons.append(f"三分球場均 {r_avg['threes']} 顆")
        if r_avg["blk"] >= 2:
            reasons.append(f"阻攻場均 {r_avg['blk']}")
        if not reasons:
            reasons.append(f"近期全面表現穩定，Fantasy 積分 {r_avg['fantasy_pts']}")

        rec_label = "強烈推薦" if match_score >= 85 else ("推薦" if match_score >= 70 else "考慮")

        candidates.append({
            "id": f"fa_{name.replace(' ','_').lower()}",
            "name": name,
            "team": r_row.get("TEAM_ABBREVIATION", ""),
            "position": "—",  # position data needs separate endpoint
            "ownership": ownership,
            "add_trend": add_trend,
            "avg_7d": {
                "pts":    r_avg["pts"],
                "reb":    r_avg["reb"],
                "ast":    r_avg["ast"],
                "stl":    r_avg["stl"],
                "threes": r_avg["threes"],
                "fg_pct": r_avg["fg_pct"],
                "ft_pct": r_avg["ft_pct"],
                "fantasy_pts": r_avg["fantasy_pts"],
                "plus_minus":  r_avg["plus_minus"],
            },
            "season_avg_pts": s_avg["pts"] if s_avg else 0,
            "recommendation": rec_label,
            "reason": "，".join(reasons),
            "match_score": match_score,
            "rank_fantasy": rank,
        })

    # Sort by fantasy_pts rank (ascending = better)
    candidates.sort(key=lambda x: x["rank_fantasy"])
    return candidates[:8]


def get_injury_news():
    return INJURY_NEWS


def get_player_recent_form(player_id):
    """Return last-5 game log simulated from recent vs season trend."""
    import random
    roster = build_roster()
    player = next((p for p in roster if p["id"] == player_id), None)
    if not player:
        return []
    random.seed(hash(player_id))
    base = player["avg"]["pts"]
    games = []
    for i in range(5, 0, -1):
        v = random.uniform(-0.2, 0.2)
        games.append({
            "game": f"G-{i}",
            "pts":  round(base * (1 + v), 1),
            "reb":  round(player["avg"]["reb"] * (1 + v * 0.5), 1),
            "ast":  round(player["avg"]["ast"] * (1 + v * 0.5), 1),
        })
    return games


def get_ai_recommendations():
    return [
        {
            "type": "add", "priority": "high",
            "player": "Cam Thomas",
            "action": "建議加入",
            "reason": "你的 FT% 本週落後對手，Cam Thomas 近期 FT% 91.2% 是自由市場最佳補強選擇。搭配近7日場均28.4分的爆發，投報率極高。",
            "drop_suggestion": "考慮放棄 Jordan Clarkson（預計缺席1週）",
        },
        {
            "type": "warning", "priority": "medium",
            "player": "Paolo Banchero",
            "action": "密切觀察",
            "reason": "Banchero 今日列 Questionable，若明日確定出賽則不需調整；若 Out，本週 PTS/REB/AST 三項同時受影響，建議預備 Immanuel Quickley 作為備案。",
            "drop_suggestion": None,
        },
        {
            "type": "schedule", "priority": "low",
            "player": "Scottie Barnes + Miles McBride",
            "action": "本週主力輪替",
            "reason": "Barnes 和 McBride 本週出賽機會多，是你隊本週產能最高的球員。Barnes 的 STL+AST 雙向貢獻可鎖定兩項，確保他們在 lineup 中。",
            "drop_suggestion": None,
        },
    ]
