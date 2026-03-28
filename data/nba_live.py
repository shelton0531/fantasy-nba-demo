"""
nba_live.py
Real NBA stats via nba_api, with local JSON cache (TTL = 3 hours).
Provides per-game season averages + last-15-game recent form.
"""

import json
import os
import time
from datetime import datetime

from nba_api.stats.endpoints import leaguedashplayerstats, playergamelog
from nba_api.stats.static import players as nba_players

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
CACHE_SEASON = os.path.join(CACHE_DIR, "season_stats.json")
CACHE_RECENT = os.path.join(CACHE_DIR, "recent_stats.json")
CACHE_N7    = os.path.join(CACHE_DIR, "n7_stats.json")
CACHE_N14   = os.path.join(CACHE_DIR, "n14_stats.json")
CACHE_N30   = os.path.join(CACHE_DIR, "n30_stats.json")
CACHE_TODAY = os.path.join(CACHE_DIR, "today_games.json")
CACHE_TTL = 3 * 60 * 60  # 3 hours in seconds
SEASON = "2025-26"

# ── Roster config: your Yahoo Fantasy picks (name + meta only, stats come from API)
MY_ROSTER_CONFIG = [
    # Teams & status updated for 2025-26 season
    # week_games = mock until Yahoo schedule API is connected
    {"id": "p1",  "name": "Nikola Jokic",       "team": "DEN", "position": "C",      "week_games": 3, "week_remaining": 1},
    {"id": "p2",  "name": "Tyrese Haliburton",   "team": "IND", "position": "PG",     "week_games": 0, "week_remaining": 0},  # 整季傷缺
    {"id": "p3",  "name": "Jaylen Brown",         "team": "BOS", "position": "SG/SF",  "week_games": 3, "week_remaining": 1},
    {"id": "p4",  "name": "Evan Mobley",          "team": "CLE", "position": "PF/C",   "week_games": 3, "week_remaining": 2},
    {"id": "p5",  "name": "Devin Booker",         "team": "PHX", "position": "SG",     "week_games": 3, "week_remaining": 1},
    {"id": "p6",  "name": "Paolo Banchero",       "team": "ORL", "position": "PF",     "week_games": 3, "week_remaining": 2},
    {"id": "p7",  "name": "Scottie Barnes",       "team": "TOR", "position": "PF/SF",  "week_games": 3, "week_remaining": 2},
    {"id": "p8",  "name": "Desmond Bane",         "team": "ORL", "position": "SG/SF",  "week_games": 3, "week_remaining": 2},  # MEM → ORL
    {"id": "p9",  "name": "Bam Adebayo",          "team": "MIA", "position": "C/PF",   "week_games": 3, "week_remaining": 1},
    {"id": "p10", "name": "Alperen Sengun",       "team": "HOU", "position": "C",      "week_games": 3, "week_remaining": 2},
    {"id": "p11", "name": "Luguentz Dort",        "team": "OKC", "position": "SG/SF",  "week_games": 3, "week_remaining": 2},
    {"id": "p12", "name": "Miles McBride",        "team": "NYK", "position": "PG/SG",  "week_games": 3, "week_remaining": 2},
    {"id": "p13", "name": "Jordan Clarkson",      "team": "NYK", "position": "PG/SG",  "week_games": 3, "week_remaining": 1},  # UTA → NYK
]

# Mock injury/status — updated for 2025-26
ROSTER_STATUS = {
    "Nikola Jokic":     {"status": "Active",   "injury": None},
    "Tyrese Haliburton":{"status": "Out",       "injury": "整季傷缺（膝蓋手術，預計賽季報銷）"},
    "Jaylen Brown":     {"status": "Active",   "injury": None},
    "Evan Mobley":      {"status": "Active",   "injury": None},
    "Devin Booker":     {"status": "Active",   "injury": None},
    "Paolo Banchero":   {"status": "Active",   "injury": None},
    "Scottie Barnes":   {"status": "Active",   "injury": None},
    "Desmond Bane":     {"status": "Active",   "injury": None},
    "Bam Adebayo":      {"status": "Active",   "injury": None},
    "Alperen Sengun":   {"status": "Active",   "injury": None},
    "Luguentz Dort":    {"status": "Active",   "injury": None},
    "Miles McBride":    {"status": "Active",   "injury": None},
    "Jordan Clarkson":  {"status": "Active",   "injury": None},
}


def _cache_valid(path):
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < CACHE_TTL


def _fetch_season_stats():
    """Full season per-game averages — all 67 columns."""
    if _cache_valid(CACHE_SEASON):
        with open(CACHE_SEASON, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[nba_live] Fetching season stats from NBA API...")
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        timeout=45,
    )
    df = endpoint.get_data_frames()[0]
    # Store all columns; round floats to 3 dp to reduce file size
    data = []
    for rec in df.to_dict(orient="records"):
        cleaned = {}
        for k, v in rec.items():
            if isinstance(v, float):
                cleaned[k] = round(v, 3)
            else:
                cleaned[k] = v
        data.append(cleaned)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_SEASON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"[nba_live] Season stats cached ({len(data)} players, {len(df.columns)} cols)")
    return data


def _fetch_recent_stats():
    """Last-15-game per-game averages — all 67 columns."""
    if _cache_valid(CACHE_RECENT):
        with open(CACHE_RECENT, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[nba_live] Fetching recent (L15) stats from NBA API...")
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        last_n_games=15,
        timeout=45,
    )
    df = endpoint.get_data_frames()[0]
    data = []
    for rec in df.to_dict(orient="records"):
        cleaned = {}
        for k, v in rec.items():
            if isinstance(v, float):
                cleaned[k] = round(v, 3)
            else:
                cleaned[k] = v
        data.append(cleaned)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_RECENT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"[nba_live] Recent stats cached ({len(data)} players, {len(df.columns)} cols)")
    return data


def _fetch_n_game_stats(n):
    """Last-N-game per-game averages (n=7, 14, or 30)."""
    cache_path = {7: CACHE_N7, 14: CACHE_N14, 30: CACHE_N30}.get(n)
    if cache_path and _cache_valid(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[nba_live] Fetching L{n} stats from NBA API...")
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        last_n_games=n,
        timeout=45,
    )
    df = endpoint.get_data_frames()[0]
    data = []
    for rec in df.to_dict(orient="records"):
        cleaned = {k: round(v, 3) if isinstance(v, float) else v for k, v in rec.items()}
        data.append(cleaned)

    if cache_path:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    print(f"[nba_live] L{n} stats cached ({len(data)} players)")
    return data


def _normalize(s):
    """Remove accents/diacritics for fuzzy matching."""
    import unicodedata
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


def _find_player(records, name):
    """
    Match priority:
    1. Normalized full name exact match  (Jokić → Jokic)
    2. Both first AND last name present  (avoids Bruce/Jaylen Brown collision)
    3. Single candidate with matching last name
    4. Partial containment fallback
    """
    name_norm = _normalize(name)
    parts = name_norm.split()
    first_norm = parts[0] if len(parts) >= 2 else ""
    last_norm  = parts[-1]

    # 1. exact normalized full name
    for r in records:
        if _normalize(r["PLAYER_NAME"]) == name_norm:
            return r

    # 2. first AND last name both present (handles same-last-name collisions)
    if first_norm:
        candidates = [
            r for r in records
            if first_norm in _normalize(r["PLAYER_NAME"])
            and last_norm  in _normalize(r["PLAYER_NAME"])
        ]
        if candidates:
            return candidates[0]

    # 3. unique last-name match
    last_candidates = [r for r in records if _normalize(r["PLAYER_NAME"]).split()[-1] == last_norm]
    if len(last_candidates) == 1:
        return last_candidates[0]

    return None


def _f(row, key, scale=1, default=0.0):
    """Safe float extract with optional scale (e.g. PCT fields stored as 0.xxx)."""
    v = row.get(key, default)
    if v is None:
        return default
    return round(float(v) * scale, 1)


def _i(row, key, default=0):
    v = row.get(key, default)
    return int(v) if v is not None else default


def _row_to_avg(row):
    if not row:
        return None
    return {
        # ── Core fantasy 9-cat ──
        "pts":       _f(row, "PTS"),
        "reb":       _f(row, "REB"),
        "ast":       _f(row, "AST"),
        "stl":       _f(row, "STL"),
        "blk":       _f(row, "BLK"),
        "threes":    _f(row, "FG3M"),
        "fg_pct":    _f(row, "FG_PCT", scale=100),
        "ft_pct":    _f(row, "FT_PCT", scale=100),
        "to":        _f(row, "TOV"),
        # ── Shooting breakdown ──
        "fg3a":      _f(row, "FG3A"),
        "fg3_pct":   _f(row, "FG3_PCT", scale=100),
        "ftm":       _f(row, "FTM"),
        "fta":       _f(row, "FTA"),
        "fgm":       _f(row, "FGM"),
        "fga":       _f(row, "FGA"),
        # ── Rebounds split ──
        "oreb":      _f(row, "OREB"),
        "dreb":      _f(row, "DREB"),
        # ── Usage / impact ──
        "min":       _f(row, "MIN"),
        "plus_minus":_f(row, "PLUS_MINUS"),
        # ── Fantasy / milestones ──
        "fantasy_pts": _f(row, "NBA_FANTASY_PTS"),
        "dd2":       _i(row, "DD2"),
        "td3":       _i(row, "TD3"),
        # ── Win/loss ──
        "w":         _i(row, "W"),
        "l":         _i(row, "L"),
        "w_pct":     _f(row, "W_PCT", scale=100),
        # ── Meta ──
        "gp":        _i(row, "GP"),
        "age":       _f(row, "AGE"),
        # ── League ranks (lower = better, except TO where lower rank = fewer TOs) ──
        "ranks": {
            "pts":       _i(row, "PTS_RANK"),
            "reb":       _i(row, "REB_RANK"),
            "ast":       _i(row, "AST_RANK"),
            "stl":       _i(row, "STL_RANK"),
            "blk":       _i(row, "BLK_RANK"),
            "threes":    _i(row, "FG3M_RANK"),
            "fg_pct":    _i(row, "FG_PCT_RANK"),
            "ft_pct":    _i(row, "FT_PCT_RANK"),
            "to":        _i(row, "TOV_RANK"),
            "min":       _i(row, "MIN_RANK"),
            "plus_minus":_i(row, "PLUS_MINUS_RANK"),
            "fantasy_pts":_i(row, "NBA_FANTASY_PTS_RANK"),
        },
    }


def _trend(season_avg, recent_avg):
    """Multi-stat trend: compare recent vs season across PTS/REB/AST/fantasy_pts."""
    if not season_avg or not recent_avg:
        return "neutral"
    checks = [
        (recent_avg["pts"]         - season_avg["pts"],          3.0),
        (recent_avg["fantasy_pts"] - season_avg["fantasy_pts"],  5.0),
        (recent_avg["reb"]         - season_avg["reb"],          2.0),
        (recent_avg["ast"]         - season_avg["ast"],          2.0),
    ]
    hot_count  = sum(1 for diff, thr in checks if diff >= thr)
    cold_count = sum(1 for diff, thr in checks if diff <= -thr)
    if hot_count >= 2:
        return "hot"
    if cold_count >= 2:
        return "cold"
    return "neutral"


def build_roster():
    season = _fetch_season_stats()
    recent = _fetch_recent_stats()

    roster = []
    for cfg in MY_ROSTER_CONFIG:
        s_row = _find_player(season, cfg["name"])
        r_row = _find_player(recent, cfg["name"])

        s_avg = _row_to_avg(s_row)
        r_avg = _row_to_avg(r_row)
        # Use recent if available, else fall back to season, else zeros
        _zero = {
            "pts": 0, "reb": 0, "ast": 0, "stl": 0, "blk": 0,
            "threes": 0, "fg_pct": 0, "ft_pct": 0, "to": 0, "gp": 0,
            "fg3a": 0, "fg3_pct": 0, "ftm": 0, "fta": 0, "fgm": 0, "fga": 0,
            "oreb": 0, "dreb": 0, "min": 0, "plus_minus": 0,
            "fantasy_pts": 0, "dd2": 0, "td3": 0,
            "w": 0, "l": 0, "w_pct": 0, "age": 0,
            "ranks": {k: 999 for k in ["pts","reb","ast","stl","blk","threes",
                                        "fg_pct","ft_pct","to","min","plus_minus","fantasy_pts"]},
        }
        display_avg = r_avg or s_avg or _zero

        trend = _trend(s_avg, r_avg)
        status_info = ROSTER_STATUS.get(cfg["name"], {"status": "Active", "injury": None})

        roster.append({
            "id":    cfg["id"],
            "name":  cfg["name"],
            "team":  cfg["team"],
            "position": cfg["position"],
            "status":   status_info["status"],
            "injury":   status_info["injury"],
            "avg":      display_avg,
            "season_avg": s_avg,
            "recent_avg": r_avg,
            "games_played":    cfg["week_games"],
            "games_remaining": cfg["week_remaining"] if status_info["status"] != "Out" else 0,
            "trend":    trend,
            "ownership": 99.0,  # placeholder until Yahoo API
            "data_source": "recent_L15" if r_avg else "season_avg",
        })

    return roster


def get_today_games():
    """
    取得今日 NBA 賽程（使用 ScoreboardV2）
    回傳: [{'home_abbr': 'LAL', 'away_abbr': 'GSW', 'status': '7:30 PM ET'}, ...]
    日期變更就重取，不受 TTL 限制
    """
    from datetime import date
    today_str = date.today().isoformat()

    if os.path.exists(CACHE_TODAY):
        try:
            with open(CACHE_TODAY, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("date") == today_str:
                return cached["games"]
        except Exception:
            pass

    from nba_api.stats.endpoints import scoreboardv2
    from nba_api.stats.static import teams as nba_teams_static

    team_map = {t["id"]: t["abbreviation"] for t in nba_teams_static.get_teams()}

    sb = scoreboardv2.ScoreboardV2(game_date=today_str, timeout=20)
    df = sb.get_data_frames()[0]  # GameHeader frame

    games = []
    for _, row in df.iterrows():
        home_id = int(row["HOME_TEAM_ID"])
        away_id = int(row["VISITOR_TEAM_ID"])
        games.append({
            "home_abbr":  team_map.get(home_id, str(home_id)),
            "away_abbr":  team_map.get(away_id, str(away_id)),
            "home_id":    home_id,
            "away_id":    away_id,
            "status":     str(row.get("GAME_STATUS_TEXT", "")).strip(),
            "game_id":    str(row["GAME_ID"]),
        })

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_TODAY, "w", encoding="utf-8") as f:
        json.dump({"date": today_str, "games": games}, f, ensure_ascii=False)

    print(f"[nba_live] Today's schedule: {len(games)} games on {today_str}")
    return games


def get_cache_status():
    def info(path):
        if not os.path.exists(path):
            return "未快取"
        age = int(time.time() - os.path.getmtime(path))
        ts = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%H:%M:%S")
        remaining = max(0, CACHE_TTL - age)
        return f"快取中（更新於 {ts}，剩餘 {remaining//60} 分鐘）"
    return {
        "season_stats": info(CACHE_SEASON),
        "recent_stats": info(CACHE_RECENT),
    }
