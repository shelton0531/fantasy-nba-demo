"""
Yahoo Fantasy API 客戶端（OAuth 2.0 PKCE）
用於取得真實的對手陣容和對戰數據
"""

import requests
import xml.etree.ElementTree as ET
from yahoo_config import (
    LEAGUE_KEY,
    YAHOO_FANTASY_API_BASE,
    USER_TEAM_ID,
    get_access_token,
    is_configured,
    is_token_expired,
    refresh_access_token
)

NS = 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'


def _get_headers():
    """取得帶有 OAuth 2.0 Token 的 Headers，自動處理 Token 續期"""
    if is_token_expired():
        print("[Yahoo API] Token 即將過期，嘗試自動續期...")
        if refresh_access_token():
            print("[Yahoo API] Token 續期成功")
        else:
            print("[Yahoo API] Token 續期失敗，請重新執行 oauth_https_server.py")
    token = get_access_token()
    return {'Authorization': f'Bearer {token}'}


def _get(endpoint):
    """執行 GET 請求，回傳 XML root 元素，失敗回傳 None"""
    url = f"{YAHOO_FANTASY_API_BASE}/{endpoint}"
    try:
        r = requests.get(url, headers=_get_headers(), timeout=10)
        if r.status_code == 200:
            return ET.fromstring(r.text)
        print(f"[Yahoo API] HTTP {r.status_code}: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[Yahoo API] 請求失敗: {e}")
        return None


def get_opponent_info(week):
    """
    從 scoreboard 找出本週對手的 team_key 和隊伍名稱

    回傳: {'team_key': '466.l.46147.t.10', 'name': '葉來葉好玩葉董好好玩', 'team_id': '10'}
    失敗回傳: None
    """
    root = _get(f"league/{LEAGUE_KEY}/scoreboard;week={week}")
    if root is None:
        return None

    try:
        for matchup in root.iter(f'{{{NS}}}matchup'):
            # 收集此 matchup 的所有 team_key
            team_keys = [
                el.text for el in matchup.iter(f'{{{NS}}}team_key')
                if el.text and '.t.' in el.text
            ]
            # 去重（XML 中 team_key 可能重複出現）
            seen = set()
            unique_keys = [k for k in team_keys if not (k in seen or seen.add(k))]

            my_key = f"{LEAGUE_KEY}.t.{USER_TEAM_ID}"
            if my_key in unique_keys:
                opp_key = next((k for k in unique_keys if k != my_key), None)
                if opp_key:
                    opp_id = opp_key.split('.t.')[-1]
                    # 取得對手隊伍名稱
                    name_root = _get(f"team/{opp_key}")
                    opp_name = "對手"
                    if name_root is not None:
                        name_el = name_root.find(f'.//{{{NS}}}name')
                        if name_el is not None:
                            opp_name = name_el.text
                    return {
                        'team_key': opp_key,
                        'name': opp_name,
                        'team_id': opp_id
                    }
    except Exception as e:
        print(f"[Yahoo API] 解析對手失敗: {e}")

    return None


def get_team_stats_for_week(team_key, week):
    """
    取得指定隊伍在指定週的累積統計

    回傳格式：
    {
        'pts': 110.5, 'reb': 48.0, 'ast': 32.0, 'stl': 10.0,
        'blk': 8.0, 'tov': 14.0, 'threepm': 18.0,
        'fg_pct': 47.3, 'ft_pct': 81.2
    }
    失敗回傳: None
    """
    root = _get(f"team/{team_key}/stats;type=week;week={week}")
    if root is None:
        return None

    # Yahoo stat_id 對照表（從聯盟 settings 確認）
    STAT_MAP = {
        '5':  'fg_pct',   # FG%（值為小數，如 0.485 = 48.5%）
        '8':  'ft_pct',   # FT%（值為小數，如 0.817 = 81.7%）
        '10': 'threepm',  # 3-Pointers Made
        '12': 'pts',      # Points
        '15': 'reb',      # Rebounds
        '16': 'ast',      # Assists
        '17': 'stl',      # Steals
        '18': 'blk',      # Blocks
        '19': 'tov',      # Turnovers
    }

    try:
        stats = {}
        for stat_el in root.iter(f'{{{NS}}}stat'):
            sid = stat_el.findtext(f'{{{NS}}}stat_id')
            val = stat_el.findtext(f'{{{NS}}}value')
            if sid in STAT_MAP and val not in (None, '-', ''):
                try:
                    stats[STAT_MAP[sid]] = float(val)
                except ValueError:
                    pass

        if not stats:
            return None

        # FG% 和 FT% 是小數（0.485），轉成百分比（48.5）
        if 'fg_pct' in stats and stats['fg_pct'] < 1:
            stats['fg_pct'] = round(stats['fg_pct'] * 100, 1)
        if 'ft_pct' in stats and stats['ft_pct'] < 1:
            stats['ft_pct'] = round(stats['ft_pct'] * 100, 1)

        return stats

    except Exception as e:
        print(f"[Yahoo API] 解析統計失敗: {e}")
        return None


def get_my_stats_for_week(week):
    """取得您自己隊伍的本週統計"""
    my_team_key = f"{LEAGUE_KEY}.t.{USER_TEAM_ID}"
    return get_team_stats_for_week(my_team_key, week)


def get_all_teams_with_rosters():
    """
    取得聯盟所有隊伍及其陣容（一次 API 呼叫）

    回傳格式:
    [
        {
            'team_key': '466.l.46147.t.1',
            'team_id': '1',
            'name': 'Team Name',
            'is_my_team': False,
            'players': [{'name': 'Player Name', 'position': 'PG'}, ...]
        },
        ...
    ]
    失敗回傳: []
    """
    root = _get(f"league/{LEAGUE_KEY}/teams;out=roster")
    if root is None:
        return []

    teams = []
    try:
        for team_el in root.iter(f'{{{NS}}}team'):
            # 只處理直屬 teams 底下的 team（避免 roster 內的巢狀元素）
            team_key_el = team_el.find(f'{{{NS}}}team_key')
            name_el = team_el.find(f'{{{NS}}}name')
            if team_key_el is None or name_el is None:
                continue

            team_key = team_key_el.text
            if not team_key or '.t.' not in team_key:
                continue

            team_id = team_key.split('.t.')[-1]
            team_name = name_el.text

            # 取得該隊陣容
            players = []
            for player_el in team_el.iter(f'{{{NS}}}player'):
                full_el = player_el.find(f'.//{{{NS}}}full')
                pos_el = player_el.find(f'.//{{{NS}}}display_position')
                if full_el is not None and full_el.text:
                    players.append({
                        'name': full_el.text,
                        'position': pos_el.text if pos_el is not None else '—'
                    })

            teams.append({
                'team_key': team_key,
                'team_id': team_id,
                'name': team_name,
                'is_my_team': team_id == str(USER_TEAM_ID),
                'players': players
            })
    except Exception as e:
        print(f"[Yahoo API] 解析全聯盟陣容失敗: {e}")

    return teams


def get_league_standings():
    """
    取得聯盟目前排名與每隊 W-L 紀錄

    回傳格式:
    {'466.l.46147.t.1': {'wins': 12, 'losses': 8, 'ties': 2}, ...}
    失敗回傳: {}
    """
    root = _get(f"league/{LEAGUE_KEY}/standings")
    if root is None:
        return {}

    standings = {}
    try:
        for team_el in root.iter(f'{{{NS}}}team'):
            team_key_el = team_el.find(f'{{{NS}}}team_key')
            if team_key_el is None:
                continue
            team_key = team_key_el.text
            if not team_key or '.t.' not in team_key:
                continue

            wins_el = team_el.find(f'.//{{{NS}}}wins')
            losses_el = team_el.find(f'.//{{{NS}}}losses')
            ties_el = team_el.find(f'.//{{{NS}}}ties')

            standings[team_key] = {
                'wins': int(wins_el.text) if wins_el is not None else 0,
                'losses': int(losses_el.text) if losses_el is not None else 0,
                'ties': int(ties_el.text) if ties_el is not None else 0,
            }
    except Exception as e:
        print(f"[Yahoo API] 解析排名失敗: {e}")

    return standings


def get_my_roster_with_keys():
    """
    取得我的陣容球員清單，包含 player_key 與即時傷兵狀態
    回傳: [{'name': str, 'player_key': str, 'position': str, 'status': str, 'injury_note': str}, ...]
    失敗回傳: []
    """
    my_team_key = f"{LEAGUE_KEY}.t.{USER_TEAM_ID}"
    root = _get(f"team/{my_team_key}/roster/players")
    if root is None:
        return []

    players = []
    try:
        for player_el in root.iter(f'{{{NS}}}player'):
            key_el    = player_el.find(f'{{{NS}}}player_key')
            full_el   = player_el.find(f'.//{{{NS}}}full')
            pos_el    = player_el.find(f'.//{{{NS}}}display_position')
            status_el = player_el.find(f'.//{{{NS}}}status')
            injury_el = player_el.find(f'.//{{{NS}}}injury_note')

            if key_el is None or full_el is None:
                continue

            players.append({
                'name':         full_el.text,
                'player_key':   key_el.text,
                'position':     pos_el.text if pos_el is not None else '—',
                'status':       (status_el.text or 'Active') if status_el is not None else 'Active',
                'injury_note':  (injury_el.text or '') if injury_el is not None else '',
            })
    except Exception as e:
        print(f"[Yahoo API] 解析陣容球員失敗: {e}")

    return players


def get_player_news(player_key, max_items=3):
    """
    取得單一球員的 Yahoo Fantasy 最新消息
    player_key: e.g. '466.p.5893'
    回傳: [{'headline': str, 'body': str, 'published': str}, ...]
    失敗回傳: []
    """
    root = _get(f"player/{player_key}/news")
    if root is None:
        return []

    news_items = []
    try:
        for item in root.iter(f'{{{NS}}}news_item'):
            headline_el  = item.find(f'{{{NS}}}headline')
            body_el      = item.find(f'{{{NS}}}body')
            published_el = item.find(f'{{{NS}}}published')
            news_items.append({
                'headline':  headline_el.text  if headline_el is not None  else '',
                'body':      body_el.text      if body_el is not None      else '',
                'published': published_el.text if published_el is not None else '',
            })
            if len(news_items) >= max_items:
                break
    except Exception as e:
        print(f"[Yahoo API] 解析球員新聞失敗: {e}")

    return news_items


def get_fa_players_positions(count: int = 150) -> dict:
    """
    取得 FA 球員的 Fantasy 位置 map，每日快取。
    回傳: {player_name_lower: position_str}，失敗回傳 {}
    """
    from pathlib import Path
    from datetime import date
    import json

    cache_path = Path("cache") / f"fa_positions_{date.today().isoformat()}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    root = _get(f"league/{LEAGUE_KEY}/players;status=FA;count={count}")
    if root is None:
        return {}

    pos_map = {}
    try:
        for player_el in root.iter(f'{{{NS}}}player'):
            full_el = player_el.find(f'.//{{{NS}}}full')
            pos_el  = player_el.find(f'.//{{{NS}}}display_position')
            if full_el is not None and full_el.text:
                pos_map[full_el.text.lower()] = pos_el.text if pos_el is not None else '—'
    except Exception as e:
        print(f"[Yahoo API] 解析 FA 位置失敗: {e}")
        return {}

    try:
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(pos_map, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return pos_map


def get_fa_players_status(count: int = 150) -> dict:
    """
    取得 FA 球員的即時狀態 map，每日快取。
    回傳: {player_name_lower: status_str}，失敗回傳 {}
    """
    from pathlib import Path
    from datetime import date
    import json

    cache_path = Path("cache") / f"fa_status_{date.today().isoformat()}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    root = _get(f"league/{LEAGUE_KEY}/players;status=FA;count={count}")
    if root is None:
        return {}

    status_map = {}
    try:
        for player_el in root.iter(f'{{{NS}}}player'):
            full_el   = player_el.find(f'.//{{{NS}}}full')
            status_el = player_el.find(f'.//{{{NS}}}status')
            if full_el is not None and full_el.text:
                status_map[full_el.text.lower()] = (status_el.text or 'Active') if status_el is not None else 'Active'
    except Exception as e:
        print(f"[Yahoo API] 解析 FA 狀態失敗: {e}")
        return {}

    try:
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(status_map, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return status_map


if __name__ == "__main__":
    from yahoo_config import CURRENT_WEEK
    print("[Yahoo API 測試]")
    print(f"League Key: {LEAGUE_KEY}")
    print(f"Current Week: {CURRENT_WEEK}")
    print()

    opp = get_opponent_info(CURRENT_WEEK)
    if opp:
        print(f"✓ 本週對手: {opp['name']} (team_key: {opp['team_key']})")
        stats = get_team_stats_for_week(opp['team_key'], CURRENT_WEEK)
        if stats:
            print(f"✓ 對手統計: {stats}")
        else:
            print("✗ 無法取得對手統計")
    else:
        print("✗ 無法取得對手資訊")
